"""Experiment configuration: which cases, which environment settings, which strategies, when to
stop, and where to save the record.

Relative paths (the case file, an environment config file, the output) are relative to the
project root; the CLI script and the web app run from there.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from medsim.case_study import load_cases
from medsim.config import Settings, load_settings
from medsim.errors import ConfigError
from medsim.models import CaseStudy

DEFAULT_OUTPUT = "records/{name}_{timestamp}.json"
InitialInformation = Literal["none", "background"]
# Settings that must come from .env, never from a config file that gets copied into the record.
SECRET_SETTINGS = frozenset({"openrouter_api_key", "OPENROUTER_API_KEY"})


class StrategySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str  # a key of strategies.STRATEGIES
    label: str | None = None  # tells two entries of the same strategy apart; defaults to name
    params: dict[str, Any] = Field(default_factory=dict)

    @property
    def key(self) -> str:
        return self.label or self.name


class StoppingCriteria(BaseModel):
    """A case run stops at whichever limit it reaches first.

    ``max_seconds`` is checked before each iteration starts, so the iteration in progress when
    the time runs out is allowed to finish.
    """

    model_config = ConfigDict(extra="forbid")

    max_iterations: int | None = Field(default=10, ge=1)
    max_seconds: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _has_a_limit(self) -> StoppingCriteria:
        if self.max_iterations is None and self.max_seconds is None:
            raise ValueError("set max_iterations, max_seconds, or both")
        return self


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="experiment", min_length=1)
    cases_file: str
    case_ids: list[str] | None = None  # None = every case in the file, in file order
    max_cases: int | None = Field(default=None, ge=1)  # after case_ids; None = no limit
    # "background": the strategy starts with the case's background_and_presentation text.
    initial_information: InitialInformation = "none"
    # medsim settings overrides (see environment/README.md), or the path of a JSON file of them.
    environment: dict[str, Any] | str = Field(default_factory=dict)
    strategies: list[StrategySpec] = Field(min_length=1)
    stopping: StoppingCriteria = Field(default_factory=StoppingCriteria)
    workers: int = Field(default=4, ge=1, le=64)  # case runs in parallel; 1 = strictly in turn
    output: str = DEFAULT_OUTPUT  # {name} and {timestamp} are filled in

    @field_validator("strategies", mode="before")
    @classmethod
    def _names_as_specs(cls, value: Any) -> Any:
        if isinstance(value, list):
            return [{"name": v} if isinstance(v, str) else v for v in value]
        return value

    @field_validator("environment")
    @classmethod
    def _no_secrets(cls, value: dict[str, Any] | str) -> dict[str, Any] | str:
        if isinstance(value, dict) and SECRET_SETTINGS & set(value):
            raise ValueError("put OPENROUTER_API_KEY in .env, not in the experiment config")
        return value

    @model_validator(mode="after")
    def _unique_labels(self) -> ExperimentConfig:
        keys = [s.key for s in self.strategies]
        repeated = sorted({k for k in keys if keys.count(k) > 1})
        if repeated:
            raise ValueError(
                f"strategy {', '.join(repeated)} is listed more than once; give each entry a "
                "distinct label"
            )
        return self

    @property
    def strategy_keys(self) -> list[str]:
        return [s.key for s in self.strategies]


def _describe(exc: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(p) for p in err['loc']) or 'config'}: {err['msg']}" for err in exc.errors()
    )


def parse_config(data: Any) -> ExperimentConfig:
    try:
        return ExperimentConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"Invalid experiment config: {_describe(exc)}") from None


def load_config(path: str | Path) -> ExperimentConfig:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"Cannot read experiment config {path}: {exc}") from None
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Experiment config {path} is not valid JSON: {exc}") from None
    return parse_config(data)


# --- environment ------------------------------------------------------------------------------


def environment_overrides(config: ExperimentConfig) -> dict[str, Any]:
    """The medsim settings overrides, read from the file when ``environment`` is a path."""
    if isinstance(config.environment, dict):
        return dict(config.environment)
    path = Path(config.environment)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"Cannot read environment config {path}: {exc}") from None
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Environment config {path} is not valid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ConfigError(f"Environment config {path} must be a JSON object of medsim settings.")
    if SECRET_SETTINGS & set(data):
        raise ConfigError(f"Put OPENROUTER_API_KEY in .env, not in {path}.")
    return data


def environment_settings(config: ExperimentConfig) -> Settings:
    """medsim ``Settings``: defaults, then .env and ``MEDSIM_*`` variables, then the overrides."""
    return load_settings(**environment_overrides(config))


def public_settings(settings: Settings) -> dict[str, Any]:
    """The settings as recorded in the experiment record: everything except the API key."""
    return settings.model_dump(mode="json", exclude={"openrouter_api_key"})


# --- cases ------------------------------------------------------------------------------------


def select_cases(config: ExperimentConfig) -> list[CaseStudy]:
    path = Path(config.cases_file)
    if not path.is_file():
        raise ConfigError(f"Case file {path} does not exist.")
    try:
        cases = load_cases(path)
    except (OSError, ValueError, KeyError, TypeError) as exc:  # bad JSON or a malformed record
        raise ConfigError(f"Cannot load cases from {path}: {type(exc).__name__}: {exc}") from None
    if config.case_ids is not None:
        missing = [case_id for case_id in config.case_ids if case_id not in cases]
        if missing:
            raise ConfigError(f"Case ids not found in {path}: {', '.join(missing)}.")
        selected = [cases[case_id] for case_id in dict.fromkeys(config.case_ids)]
    else:
        selected = list(cases.values())
    if config.max_cases is not None:
        selected = selected[: config.max_cases]
    if not selected:
        raise ConfigError(f"No cases selected from {path}.")
    return selected


def initial_information(case: CaseStudy, mode: InitialInformation) -> str | None:
    if mode == "background":
        text = str(case.metadata.get("background_and_presentation") or "").strip()
        return text or None
    return None


# --- output -----------------------------------------------------------------------------------


def output_path(config: ExperimentConfig, *, now: datetime) -> Path:
    """The record's path: the template filled in, with a numeric suffix if the file exists."""
    safe_name = re.sub(r"[^\w.-]+", "_", config.name).strip("_") or "experiment"
    try:
        filled = config.output.format(name=safe_name, timestamp=now.strftime("%Y%m%dT%H%M%SZ"))
    except (KeyError, IndexError, ValueError) as exc:
        raise ConfigError(
            f"Invalid output path {config.output!r}: only {{name}} and {{timestamp}} can be "
            f"filled in ({exc})."
        ) from None
    path = Path(filled)
    if path.suffix != ".json":
        path = path.with_name(path.name + ".json")
    candidate, n = path, 1
    while candidate.exists() or partial_path(candidate).exists():
        n += 1
        candidate = path.with_name(f"{path.stem}_{n}{path.suffix}")
    return candidate


def partial_path(record_path: Path) -> Path:
    """Where finished case runs are appended while the experiment runs."""
    return record_path.with_suffix(".partial.jsonl")
