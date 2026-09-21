"""Command-line interface: ``python -m medsim --case CASE [--query Q] [--json] [--verbose]``."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TextIO

from medsim.config import load_settings
from medsim.environment import MedicalEnvironment
from medsim.errors import ConfigError, MedSimError, redact
from medsim.ledger import FactLedger
from medsim.models import EnvironmentResponse

EnvFactory = Callable[[argparse.Namespace], MedicalEnvironment]

SYNTHESIZED_NOTE = "SYNTHESIZED — simulation artifact, not a clinical claim"


class RedactingFilter(logging.Filter):
    def __init__(self, secrets: Sequence[str]) -> None:
        super().__init__()
        self._secrets = [s for s in secrets if s]

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage(), self._secrets)
        record.args = None
        return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="medsim",
        description="Query a simulated patient. Without --query, reads one question per line "
        "from stdin; all questions share one fact ledger.",
    )
    parser.add_argument("--case", required=True, type=Path, help="Path to a case-study JSON file.")
    parser.add_argument("--query", help="A single question. Omit to read questions from stdin.")
    parser.add_argument("--json", action="store_true", help="Print full EnvironmentResponse JSON.")
    parser.add_argument("--verbose", action="store_true", help="Debug logging and more detail.")
    parser.add_argument("--load-ledger", type=Path, help="Resume from a saved ledger JSON file.")
    parser.add_argument("--save-ledger", type=Path, help="Write the ledger JSON here on exit.")
    parser.add_argument(
        "--no-verify-models", action="store_true", help="Skip the OpenRouter model-slug check."
    )
    return parser


def _default_factory(args: argparse.Namespace) -> MedicalEnvironment:
    settings = load_settings()
    level = logging.DEBUG if args.verbose else getattr(logging, settings.log_level.upper(), 30)
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")
    secret = settings.openrouter_api_key.get_secret_value()
    for handler in logging.getLogger().handlers:
        handler.addFilter(RedactingFilter([secret]))
    return MedicalEnvironment.from_case_file(
        args.case, settings=settings, verify_models=False if args.no_verify_models else None
    )


def format_summary(response: EnvironmentResponse, *, verbose: bool = False) -> str:
    source: str = response.answer_source
    if source == "literature":
        source = f"literature ({SYNTHESIZED_NOTE})"
    lines = [
        f"Q: {response.input_query}",
        f"A: {response.output_answer}",
        f"   source: {source} | confidence: {response.confidence}",
    ]
    if response.evidence:
        lines.append(f"   evidence: {'; '.join(response.evidence)}")
    result = response.literature_search_result
    if result is not None:
        counts = ", ".join(f"{k}={v}" for k, v in result.per_source_counts.items())
        lines.append(
            f'   literature query: "{result.query}" -> {len(result.documents)} docs ({counts})'
        )
        if result.errors:
            lines.append(f"   source errors: {'; '.join(result.errors)}")
        if verbose:
            for doc in result.documents:
                lines.append(f"     [{doc.doc_id}] {doc.title or doc.text[:80]} {doc.url or ''}")
    if response.llm_calls:
        calls = "; ".join(
            f"{c.stage}/{c.purpose} {c.model} {c.prompt_tokens}->{c.completion_tokens} tok "
            f"{c.latency_ms / 1000:.1f}s{'' if c.success else ' FAILED'}"
            for c in response.llm_calls
        )
        lines.append(f"   llm calls: {calls}")
    else:
        lines.append("   llm calls: none")
    if verbose:
        lines.append(f"   retriever parameters: {json.dumps(response.retriever_parameters)}")
    return "\n".join(lines)


def main(
    argv: Sequence[str] | None = None,
    *,
    env_factory: EnvFactory | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    args = build_parser().parse_args(argv)

    try:
        env = (env_factory or _default_factory)(args)
        if args.load_ledger:
            env.ledger = FactLedger.load(args.load_ledger)
    except (ConfigError, OSError, ValueError) as exc:
        print(f"medsim: configuration error: {exc}", file=stderr)
        return 2

    if args.query is not None:
        questions = [args.query]
    else:
        questions = [line.strip() for line in stdin if line.strip()]
    single = args.query is not None

    exit_code = 0
    try:
        for question in questions:
            try:
                response = env.query(question)
            except MedSimError as exc:
                print(f"medsim: error answering {question!r}: {exc}", file=stderr)
                exit_code = 1
                continue
            if args.json:
                print(response.model_dump_json(indent=2 if single else None), file=stdout)
            else:
                print(format_summary(response, verbose=args.verbose), file=stdout)
                if not single:
                    print(file=stdout)
    finally:
        if args.save_ledger:
            env.ledger.save(args.save_ledger)
        env.close()
    return exit_code
