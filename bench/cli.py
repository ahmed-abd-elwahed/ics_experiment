"""``python -m bench [--out DIR] <step> [options]``; steps run in the order listed in the help."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from bench.config import BenchSettings
from bench.extract import run_extract, select_cases
from bench.items import ItemBuilder, run_redact
from bench.judge import Judge, run_judge
from bench.report import build_report, write_report
from bench.run import CONFIGS, LiveRetrievers, run_configs
from bench.schemas import Item
from bench.text import load_cases
from bench.validate import run_validate
from bench.workspace import Workspace, load_manifest, read_models, update_manifest
from medsim.cli import RedactingFilter
from medsim.config import Settings, load_settings
from medsim.errors import ConfigError, MedSimError
from medsim.llm.openrouter import OpenRouterClient

logger = logging.getLogger("bench")

DEFAULT_CASES = Path("cases/combined_272_whole_chunking.json")


def key_usage(settings: Settings) -> float | None:
    """The OpenRouter key's cumulative spend (USD), or None if it cannot be read."""
    try:
        response = httpx.get(
            f"{settings.openrouter_base_url.rstrip('/')}/key",
            headers={"Authorization": f"Bearer {settings.openrouter_api_key.get_secret_value()}"},
            timeout=20,
        )
        response.raise_for_status()
        return float(response.json()["data"]["usage"])
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m bench",
        description="Retrieval benchmark for medsim. Steps: extract -> redact -> run -> judge -> "
        "validate -> report. Each step resumes where it stopped.",
    )
    parser.add_argument("--out", type=Path, default=Path("bench_runs/default"),
                        help="Workspace directory (default: bench_runs/default).")  # fmt: skip
    parser.add_argument("--workers", type=int, default=12,
                        help="Parallel questions or judge calls (default 12).")  # fmt: skip
    parser.add_argument("--verbose", action="store_true", help="Debug logging.")
    parser.add_argument("--no-verify-models", action="store_true",
                        help="Skip the OpenRouter model-slug check.")  # fmt: skip
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("extract", help="List measured values in each case (LLM).")
    p.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    p.add_argument("--limit", type=int, help="Number of cases (seeded random subset).")
    p.add_argument("--seed", type=int, default=20260921)

    p = sub.add_parser("redact", help="Build set A (hidden value) and set B questions.")
    p.add_argument("--cases", type=Path, help="Defaults to the case file used by extract.")
    p.add_argument("--set-a", type=int, default=35)
    p.add_argument("--set-b", type=int, default=15)
    p.add_argument("--per-case", type=int, default=1, help="Max set A questions per case.")
    p.add_argument("--seed", type=int, default=20260921)

    p = sub.add_parser("run", help="Ask medsim every question under each configuration.")
    p.add_argument("--configs", default="current,openrouter_search",
                   help=f"Comma-separated, from: {', '.join(CONFIGS)}.")  # fmt: skip
    p.add_argument("--limit", type=int, help="Only the first N questions.")
    p.add_argument("--no-cache", action="store_true", help="Do not reuse cached search results.")

    p = sub.add_parser("judge", help="LLM judge: relevance, usefulness, correctness.")
    p.add_argument("--configs", help="Default: every configuration that has run results.")

    p = sub.add_parser("validate", help="Controls, flipped truth, second judge, human sample.")
    p.add_argument("--configs")
    p.add_argument(
        "--controls", type=int, default=10, help="Set A questions to build controls for."
    )
    p.add_argument("--flips", type=int, default=10)
    p.add_argument("--second-fraction", type=float, default=0.1)
    p.add_argument("--export-human", type=int, default=0, help="Rows to export for human labels.")
    p.add_argument("--seed", type=int, default=7)

    p = sub.add_parser("report", help="Write report.md and report.json.")
    p.add_argument("--configs")
    p.add_argument("--baseline", default="current")
    p.add_argument("--bootstrap", type=int, default=2000)
    p.add_argument("--seed", type=int, default=11)
    p.add_argument("--snapshot", help="Also save the report as reports/<SNAPSHOT>.md.")

    sub.add_parser("spend", help="Print the OpenRouter key's usage and remaining limit.")
    return parser


def _configs(ws: Workspace, value: str | None) -> list[str]:
    return [c.strip() for c in value.split(",") if c.strip()] if value else ws.run_configs()


def _items(ws: Workspace) -> list[Item]:
    items = read_models(ws.items, Item)
    if not items:
        raise ConfigError(f"No questions in {ws.items}; run the redact step first.")
    return items


def _client(settings: Settings, models: Sequence[str], verify: bool) -> OpenRouterClient:
    client = OpenRouterClient(settings)
    if verify:
        client.verify_models(list(dict.fromkeys(models)))
    return client


def execute(args: argparse.Namespace, settings: Settings, bench: BenchSettings) -> dict[str, Any]:
    ws = Workspace(args.out)
    verify = not args.no_verify_models
    summary: dict[str, Any]
    if args.command == "extract":
        cases = load_cases(args.cases)
        case_ids = select_cases(cases, limit=args.limit, seed=args.seed)
        with _client(settings, [bench.extractor()], verify) as llm:
            summary = run_extract(
                ws, cases, case_ids, llm=llm, model=bench.extractor(),
                max_tokens=bench.extractor_max_tokens, workers=args.workers,
            )  # fmt: skip
        return {"cases_file": str(args.cases), "limit": args.limit, "seed": args.seed, **summary}

    if args.command == "redact":
        cases_file = args.cases or Path(load_manifest(ws).get("latest", {}).get("extract", {})
                                        .get("cases_file", DEFAULT_CASES))  # fmt: skip
        cases = load_cases(cases_file)
        live = LiveRetrievers(settings)
        models = [bench.redactor(), settings.model_for("resolver")]
        try:
            with _client(settings, models, verify) as llm:
                builder = ItemBuilder(
                    cases, llm=llm, pipeline_llm=llm, settings=settings,
                    redactor_model=bench.redactor(), redactor_max_tokens=bench.redactor_max_tokens,
                    lookup_pmid=lambda pmcid: live.lookup_pmid(settings, pmcid),
                )  # fmt: skip
                summary = run_redact(
                    ws, cases, builder, set_a=args.set_a, set_b=args.set_b,
                    per_case=args.per_case, seed=args.seed, workers=args.workers,
                )  # fmt: skip
        finally:
            live.close()
        return {"set_a": args.set_a, "set_b": args.set_b, "seed": args.seed, **summary}

    if args.command == "run":
        names = _configs(ws, args.configs)
        unknown = [n for n in names if n not in CONFIGS]
        if unknown:
            raise ConfigError(f"Unknown configuration(s): {', '.join(unknown)}")
        items = _items(ws)[: args.limit] if args.limit else _items(ws)
        run_settings = settings.model_copy(update={"cache_enabled": not args.no_cache})
        models = [
            *settings.stage_models(),
            settings.openrouter_search.model or settings.default_model,
            settings.model_for("reranker"),
        ]
        live = LiveRetrievers(run_settings, cache=not args.no_cache)
        try:
            with _client(settings, models, verify) as llm:
                summary = run_configs(
                    ws, items, [CONFIGS[n] for n in names], llm=llm, base_settings=run_settings,
                    retrievers=live, fulltext=live.fulltext, workers=args.workers,
                )  # fmt: skip
        finally:
            live.close()
        return {"configs": names, "items": len(items), "pipeline_models": settings.stage_models(),
                **summary}  # fmt: skip

    if args.command == "judge":
        with _client(settings, [bench.judge_model], verify) as llm:
            judge = Judge(llm, bench.judge_model, bench.judge_max_tokens)
            summary = run_judge(
                ws, _items(ws), _configs(ws, args.configs), judge, workers=args.workers
            )
        return {"judge_model": bench.judge_model, **summary}

    if args.command == "validate":
        models = [bench.judge_model, bench.second_judge_model]
        with _client(settings, models, verify) as llm:
            judge = Judge(llm, bench.judge_model, bench.judge_max_tokens)
            second = Judge(llm, bench.second_judge_model, bench.judge_max_tokens)
            summary = run_validate(
                ws, _items(ws), _configs(ws, args.configs), judge, second_judge=second,
                controls=args.controls, flips=args.flips, second_fraction=args.second_fraction,
                export_human=args.export_human, seed=args.seed, workers=args.workers,
            )  # fmt: skip
        return {"judge_model": bench.judge_model, "second_judge_model": bench.second_judge_model,
                **summary}  # fmt: skip

    if args.command == "report":
        markdown, data = build_report(
            ws, _items(ws), _configs(ws, args.configs), judge_model=bench.judge_model,
            second_judge_model=bench.second_judge_model, baseline=args.baseline,
            n_boot=args.bootstrap, seed=args.seed,
        )  # fmt: skip
        write_report(ws, markdown, data)
        summary = {"report": str(ws.report_md), "configs": data["configs"]}
        if args.snapshot:
            snapshot = ws.root / "reports" / f"{args.snapshot}.md"
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_text(markdown + "\n", encoding="utf-8")
            summary["snapshot"] = str(snapshot)
        return summary

    raise ConfigError(f"Unknown command {args.command}")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings()
        bench = BenchSettings()
    except ConfigError as exc:
        print(f"bench: configuration error: {exc}", file=sys.stderr)
        return 2
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("bench").setLevel(logging.DEBUG if args.verbose else logging.INFO)
    if args.verbose:
        logging.getLogger("medsim").setLevel(logging.DEBUG)
    if args.command != "spend":  # every command's log is kept in the workspace
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        log_path = args.out / "logs" / f"{stamp}_{args.command}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        logging.getLogger().addHandler(file_handler)
        command_line = " ".join(sys.argv[1:] if argv is None else argv)
        logging.getLogger("bench").info("bench %s", command_line)
    for handler in logging.getLogger().handlers:
        handler.addFilter(RedactingFilter([settings.openrouter_api_key.get_secret_value()]))

    if args.command == "spend":
        usage = key_usage(settings)
        print(json.dumps({"key_usage_usd": usage}))
        return 0

    before = key_usage(settings)
    try:
        summary = execute(args, settings, bench)
    except (ConfigError, MedSimError, OSError) as exc:
        print(f"bench: {args.command} failed: {exc}", file=sys.stderr)
        return 1
    after = key_usage(settings)
    record: dict[str, Any] = {**summary, "key_usage_before": before, "key_usage_after": after}
    if before is None or after is None:
        record.pop("key_usage_before")
        record.pop("key_usage_after")
    update_manifest(Workspace(args.out), args.command, record)
    spent = (
        f"; key spend +${after - before:.4f}" if before is not None and after is not None else ""
    )
    print(json.dumps(summary, default=str), file=sys.stderr)
    print(f"bench {args.command}: done{spent}", file=sys.stderr)
    return 0
