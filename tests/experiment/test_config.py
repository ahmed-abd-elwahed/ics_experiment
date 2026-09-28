from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from experiment.config import (
    environment_settings,
    load_config,
    output_path,
    parse_config,
    partial_path,
    select_cases,
)
from medsim.errors import ConfigError
from tests.experiment.helpers import make_config, write_cases

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 9, 22, 10, 30, 0, tzinfo=UTC)


def test_basic_config_is_valid_and_names_the_basic_strategy() -> None:
    config = load_config(ROOT / "configs" / "basic.json")
    assert [s.name for s in config.strategies] == ["basic"]
    assert (ROOT / config.cases_file).is_file()
    assert config.stopping.max_iterations is not None


def test_strategies_can_be_given_by_name(tmp_path: Path) -> None:
    config = make_config(write_cases(tmp_path), strategies=["basic"])
    assert config.strategies[0].name == "basic"
    assert config.strategies[0].params == {}
    assert config.strategy_keys == ["basic"]


@pytest.mark.parametrize(
    ("update", "message"),
    [
        ({"stopping": {"max_iterations": None, "max_seconds": None}}, "max_seconds, or both"),
        ({"strategies": ["basic", "basic"]}, "distinct label"),
        ({"strategies": []}, "strategies"),
        ({"environment": {"openrouter_api_key": "sk-x"}}, ".env"),
        ({"workers": 0}, "workers"),
        ({"unknown": 1}, "unknown"),
    ],
)
def test_invalid_configs_are_rejected(tmp_path: Path, update: dict[str, Any], message: str) -> None:
    data = make_config(write_cases(tmp_path)).model_dump(mode="json") | update
    with pytest.raises(ConfigError, match=message):
        parse_config(data)


def test_same_strategy_twice_with_labels(tmp_path: Path) -> None:
    config = make_config(
        write_cases(tmp_path),
        strategies=[
            {"name": "basic", "label": "cold", "params": {"temperature": 0}},
            {"name": "basic", "label": "warm", "params": {"temperature": 1}},
        ],
    )
    assert config.strategy_keys == ["cold", "warm"]


def test_case_selection(tmp_path: Path) -> None:
    cases_file = write_cases(tmp_path)
    assert len(select_cases(make_config(cases_file))) == 6
    assert [c.case_id for c in select_cases(make_config(cases_file, max_cases=2))] == [
        "CASE1", "CASE2"
    ]  # fmt: skip
    picked = select_cases(make_config(cases_file, case_ids=["CASE4", "CASE2"], max_cases=1))
    assert [c.case_id for c in picked] == ["CASE4"]
    assert picked[0].narrative == "Patient 4 presented with fever. Case 4, second part."
    assert picked[0].diagnosis == "Diagnosis 4"
    with pytest.raises(ConfigError, match="CASE9"):
        select_cases(make_config(cases_file, case_ids=["CASE9"]))
    with pytest.raises(ConfigError, match="does not exist"):
        select_cases(make_config(tmp_path / "missing.json"))


def test_duplicate_case_ids_are_rejected(tmp_path: Path) -> None:
    record = {"case_id": "CASE1", "case_information": "Fever.", "diagnosis": "Flu"}
    cases_file = write_cases(tmp_path, [record, record | {"case_information": "Cough."}])
    with pytest.raises(ConfigError, match="Duplicate case id 'CASE1'"):
        select_cases(make_config(cases_file))


def test_bundled_dataset_loads() -> None:
    path = Path(__file__).resolve().parents[2] / "cases" / "combined_272_whole_chunking.json"
    records = json.loads(path.read_text(encoding="utf-8"))
    assert all(set(r) == {"case_id", "case_information", "diagnosis"} for r in records)
    assert len(select_cases(make_config(path))) == len(records) == 272


def test_the_real_dataset_loads() -> None:
    config = load_config(ROOT / "configs" / "basic.json")
    cases = select_cases(config.model_copy(update={"cases_file": str(ROOT / config.cases_file)}))
    assert len(cases) == config.max_cases
    assert all(case.narrative and case.diagnosis for case in cases)


def test_output_path_fills_the_template_and_never_overwrites(tmp_path: Path) -> None:
    config = make_config(
        write_cases(tmp_path), name="my run!", output=str(tmp_path / "out" / "{name}_{timestamp}")
    )
    first = output_path(config, now=NOW)
    assert first == tmp_path / "out" / "my_run_20260922T103000Z.json"
    first.parent.mkdir()
    first.write_text("{}")
    assert output_path(config, now=NOW).name == "my_run_20260922T103000Z_2.json"
    assert partial_path(first).name == "my_run_20260922T103000Z.partial.jsonl"
    bad = config.model_copy(update={"output": "records/{user}.json"})
    with pytest.raises(ConfigError, match="name"):
        output_path(bad, now=NOW)


def test_environment_settings_from_inline_overrides_or_a_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.chdir(tmp_path)  # no .env here
    cases_file = write_cases(tmp_path)
    inline = make_config(cases_file, environment={"max_documents": 3, "cache_enabled": True})
    settings = environment_settings(inline)
    assert (settings.max_documents, settings.cache_enabled) == (3, True)

    env_file = tmp_path / "env.json"
    env_file.write_text(json.dumps({"europe_pmc": {"page_size": 25}}))
    from_file = environment_settings(make_config(cases_file, environment=str(env_file)))
    assert from_file.europe_pmc.page_size == 25

    env_file.write_text(json.dumps({"OPENROUTER_API_KEY": "sk-leak"}))
    with pytest.raises(ConfigError, match=r"\.env"):
        environment_settings(make_config(cases_file, environment=str(env_file)))
    with pytest.raises(ConfigError, match="max_documents"):
        environment_settings(make_config(cases_file, environment={"max_documents": 0}))
