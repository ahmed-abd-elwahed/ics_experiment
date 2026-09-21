"""Benchmark settings, read from the environment and ``.env`` with medsim's ``MEDSIM_`` prefix.

Field names match the hint in ``medsim.llm.structured.call_structured`` ("Raise
MEDSIM_<STAGE>_MAX_TOKENS"), because the bench stages are named extractor, redactor and judge.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Judges come from model families other than the pipeline's (DeepSeek by default), so no judge
# grades its own family's search terms. Chosen on 2026-09-21 by probing one pass-1 judgment:
# gemini-3.5-flash-lite $0.0007 and 2 s; qwen3.8-flash $0.0006 but 22 s of reasoning (used as
# the second judge on a sample); gpt-5.6-luna could not be routed with medsim's parameters.
DEFAULT_JUDGE_MODEL = "google/gemini-3.5-flash-lite"
DEFAULT_SECOND_JUDGE_MODEL = "qwen/qwen3.8-flash"


class BenchSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MEDSIM_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    judge_model: str = DEFAULT_JUDGE_MODEL
    second_judge_model: str = DEFAULT_SECOND_JUDGE_MODEL
    extractor_model: str | None = None  # None = judge_model
    redactor_model: str | None = None  # None = judge_model
    judge_max_tokens: int = Field(default=4000, ge=1)
    extractor_max_tokens: int = Field(default=8000, ge=1)
    redactor_max_tokens: int = Field(default=8000, ge=1)

    def extractor(self) -> str:
        return self.extractor_model or self.judge_model

    def redactor(self) -> str:
        return self.redactor_model or self.judge_model
