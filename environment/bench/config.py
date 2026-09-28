"""Benchmark settings, read from the environment and ``.env`` with medsim's ``MEDSIM_`` prefix.

Field names match the hint in ``medsim.llm.structured.call_structured`` ("Raise
MEDSIM_<STAGE>_MAX_TOKENS"), because the bench stages are named extractor, redactor and judge.
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The judge panel: three models from three families other than the pipeline's (DeepSeek by
# default), so no judge grades its own family's answers. Every answer is judged by each model and
# the final label is the majority vote; with no majority, the first (main) judge decides. The
# first two were chosen on 2026-09-21 by probing one judgment (gemini-3.5-flash-lite $0.0007 and
# 2 s; qwen3.8-flash $0.0006 but 22 s of reasoning); gpt-6-luna was added on 2026-09-29.
DEFAULT_JUDGE_MODELS = ("google/gemini-3.5-flash-lite", "qwen/qwen3.8-flash", "openai/gpt-6-luna")


class BenchSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MEDSIM_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # MEDSIM_JUDGE_MODELS as a JSON list; the first is the main judge (breaks ties).
    judge_models: list[str] = Field(default_factory=lambda: list(DEFAULT_JUDGE_MODELS))
    extractor_model: str | None = None  # None = the main judge
    redactor_model: str | None = None  # None = the main judge
    question_writer_model: str | None = None  # set C questions; None = the main judge
    judge_max_tokens: int = Field(default=4000, ge=1)
    # Whole-judgment retries when a judge call fails or its reply is unusable (see bench.judge).
    judge_max_attempts: int = Field(default=3, ge=1)
    judge_retry_backoff_s: float = Field(default=2.0, ge=0.0)
    extractor_max_tokens: int = Field(default=8000, ge=1)
    redactor_max_tokens: int = Field(default=8000, ge=1)
    question_writer_max_tokens: int = Field(default=4000, ge=1)

    @field_validator("judge_models")
    @classmethod
    def _distinct_models(cls, models: list[str]) -> list[str]:
        if not models or len(set(models)) != len(models):
            raise ValueError("judge_models must list at least one model, each once")
        return models

    @property
    def judge_model(self) -> str:
        """The main judge: breaks ties, and extracts and redacts by default."""
        return self.judge_models[0]

    def extractor(self) -> str:
        return self.extractor_model or self.judge_model

    def redactor(self) -> str:
        return self.redactor_model or self.judge_model

    def question_writer(self) -> str:
        return self.question_writer_model or self.judge_model
