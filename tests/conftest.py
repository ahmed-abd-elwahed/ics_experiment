from __future__ import annotations

import json
import os
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import pytest

from medsim.case_study import load_case_study
from medsim.config import EuropePMCSettings, LitSenseSettings, Settings, load_settings
from medsim.models import CaseStudy, ChatMessage, LLMResponse, TokenUsage

FIXTURES = Path(__file__).parent / "fixtures"
TEST_KEY = "sk-or-v1-TESTSECRET-0123456789abcdef"
MODEL = "deepseek/deepseek-v4-flash-0731"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--live", action="store_true", default=False, help="run live API tests")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    live_ok = config.getoption("--live") and bool(os.environ.get("OPENROUTER_API_KEY"))
    skip = pytest.mark.skip(reason="needs --live and OPENROUTER_API_KEY")
    for item in items:
        if "live" in item.keywords and not live_ok:
            item.add_marker(skip)


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    if "live" in request.keywords:
        return
    for name in list(os.environ):
        if name.startswith("MEDSIM_") or name == "OPENROUTER_API_KEY":
            monkeypatch.delenv(name, raising=False)


def make_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "openrouter_api_key": TEST_KEY,
        "verify_models_on_startup": False,
        "llm_backoff_base_s": 0.0,
        "llm_max_retries": 1,
        "europe_pmc": EuropePMCSettings(backoff_base_s=0.0, max_retries=1, page_size=5),
        "litsense": LitSenseSettings(backoff_base_s=0.0, max_retries=1, min_interval_s=0.0),
        "max_documents": 6,
        "max_doc_chars": 600,
    }
    values.update(overrides)
    return load_settings(_env_file=None, **values)


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def case() -> CaseStudy:
    return load_case_study(FIXTURES / "test_case.json")


def completion_body(
    content: str, *, model: str = MODEL, prompt_tokens: int = 100, completion_tokens: int = 20
) -> dict[str, Any]:
    """An OpenRouter chat-completions response body (documented OpenAI-compatible shape)."""
    return {
        "id": "gen-test",
        "object": "chat.completion",
        "created": 1757900000,
        "model": model,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": content},
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


class ScriptedLLM:
    """LLMClient test double that returns queued outputs in order and records each call."""

    def __init__(self, outputs: Sequence[str | dict[str, Any] | Exception] = ()) -> None:
        self.default_model = MODEL
        self.outputs: list[str | dict[str, Any] | Exception] = list(outputs)
        self.calls: list[dict[str, Any]] = []

    def push(self, *outputs: str | dict[str, Any] | Exception) -> None:
        self.outputs.extend(outputs)

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        response_format: dict[str, Any] | None,
        temperature: float,
        max_tokens: int,
        model: str | None = None,
    ) -> LLMResponse:
        self.calls.append(
            {
                "messages": list(messages),
                "response_format": response_format,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "model": model,
            }
        )
        if not self.outputs:
            raise AssertionError("ScriptedLLM ran out of scripted outputs")
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        content = output if isinstance(output, str) else json.dumps(output)
        return LLMResponse(
            content=content,
            model=model or self.default_model,
            usage=TokenUsage(prompt_tokens=50, completion_tokens=10, total_tokens=60),
            latency_ms=5.0,
        )

    def stages_called(self) -> list[str]:
        """Infer which stage each call was from the response_format schema name."""
        names = []
        for call in self.calls:
            rf = call["response_format"] or {}
            names.append(str(rf.get("json_schema", {}).get("name", "?")).removesuffix("_output"))
        return names


@pytest.fixture
def llm() -> Iterator[ScriptedLLM]:
    scripted = ScriptedLLM()
    yield scripted
    assert not scripted.outputs, f"unused scripted LLM outputs: {scripted.outputs}"
