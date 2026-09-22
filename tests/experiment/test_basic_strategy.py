from __future__ import annotations

import pytest

from medsim.errors import ConfigError, LLMError
from strategies import BasicStrategy, CaseContext, build_strategy, describe_strategies
from tests.conftest import MODEL, ScriptedLLM, make_settings


def basic(llm: ScriptedLLM, **params: object) -> BasicStrategy:
    strategy = build_strategy("basic", dict(params), llm=llm, settings=make_settings())
    assert isinstance(strategy, BasicStrategy)
    return strategy


def test_first_question_with_no_information(llm: ScriptedLLM) -> None:
    llm.push({"question": " What brings the patient in today? ", "rationale": "Start broad."})
    session = basic(llm).new_session(CaseContext(max_iterations=5))
    question = session.next_question()

    assert question is not None
    assert question.text == "What brings the patient in today?"
    assert question.rationale == "Start broad."
    assert [c.stage for c in question.llm_calls] == ["strategy"]
    prompt = llm.calls[0]["messages"][1].content
    assert "You have no information about the patient yet." in prompt
    assert "(none yet)" in prompt
    assert "This is question 1 of at most 5." in prompt
    assert llm.calls[0]["model"] == MODEL
    assert llm.calls[0]["temperature"] == 0.2
    assert llm.calls[0]["response_format"]["json_schema"]["name"] == "strategy_output"


def test_prompt_carries_initial_information_and_memory(llm: ScriptedLLM) -> None:
    llm.push({"question": "Any cough?", "rationale": "Narrow down."})
    session = basic(llm, model="other/model", temperature=0.7).new_session(
        CaseContext(initial_information="A 40-year-old man with fever.")
    )
    session.remember("What is the chief complaint?", "Fever for two days.")
    session.remember("What is his temperature?", "38.9 °C.")
    session.next_question()

    prompt = llm.calls[0]["messages"][1].content
    assert "Initial information about the patient:\nA 40-year-old man with fever." in prompt
    assert (
        "1. Q: What is the chief complaint?\n   A: Fever for two days.\n"
        "2. Q: What is his temperature?\n   A: 38.9 °C."
    ) in prompt
    assert "This is question 3. Ask the next question." in prompt
    assert (llm.calls[0]["model"], llm.calls[0]["temperature"]) == ("other/model", 0.7)


def test_empty_question_means_nothing_left_to_ask(llm: ScriptedLLM) -> None:
    llm.push({"question": "  ", "rationale": "Done."})
    assert basic(llm).new_session(CaseContext()).next_question() is None


def test_cut_off_reply_names_the_strategy_param() -> None:
    class Truncating(ScriptedLLM):
        """Every reply is cut off by max_tokens before any content."""

        def complete(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            response = super().complete(*args, **kwargs)
            return response.model_copy(update={"content": "", "finish_reason": "length"})

    truncating = Truncating(["x", "x"])
    with pytest.raises(LLMError, match="strategy's max_tokens param"):
        basic(truncating, max_tokens=10).new_session(CaseContext()).next_question()


def test_unknown_strategy_and_bad_params_are_config_errors() -> None:
    with pytest.raises(ConfigError, match="Available: basic"):
        build_strategy("clever", {}, llm=ScriptedLLM(), settings=make_settings())
    with pytest.raises(ConfigError, match="temperature"):
        build_strategy("basic", {"temperature": 5}, llm=ScriptedLLM(), settings=make_settings())
    with pytest.raises(ConfigError, match="Extra inputs"):
        build_strategy("basic", {"colour": "red"}, llm=ScriptedLLM(), settings=make_settings())


def test_describe_strategies_lists_basic_with_default_params() -> None:
    (entry,) = describe_strategies()
    assert entry["name"] == "basic"
    assert entry["params"] == {"model": None, "temperature": 0.2, "max_tokens": 4000}
