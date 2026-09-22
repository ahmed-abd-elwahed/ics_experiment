"""Information gathering strategies, by the name used in experiment configs.

To add one, subclass ``InformationGatheringStrategy`` (and ``StrategySession``) in a module of
this package and register the class in ``STRATEGIES``.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from medsim.config import Settings
from medsim.errors import ConfigError
from medsim.llm.base import LLMClient
from strategies.base import (
    CaseContext,
    InformationGatheringStrategy,
    Memory,
    MemoryEntry,
    Question,
    StrategyParams,
    StrategySession,
)
from strategies.basic import BasicStrategy

STRATEGIES: dict[str, type[InformationGatheringStrategy[Any]]] = {
    BasicStrategy.name: BasicStrategy,
}


def strategy_class(name: str) -> type[InformationGatheringStrategy[Any]]:
    try:
        return STRATEGIES[name]
    except KeyError:
        available = ", ".join(sorted(STRATEGIES))
        raise ConfigError(f"Unknown strategy {name!r}. Available: {available}.") from None


def parse_params(name: str, params: dict[str, Any]) -> StrategyParams:
    """Validate a strategy's ``params`` from the experiment config."""
    try:
        return strategy_class(name).params_model.model_validate(params)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(p) for p in err['loc']) or 'params'}: {err['msg']}"
            for err in exc.errors()
        )
        raise ConfigError(f"Invalid params for strategy {name!r}: {details}") from None


def build_strategy(
    name: str, params: dict[str, Any], *, llm: LLMClient, settings: Settings
) -> InformationGatheringStrategy[Any]:
    return strategy_class(name)(parse_params(name, params), llm=llm, settings=settings)


def describe_strategies() -> list[dict[str, Any]]:
    """Name, description, and default params of every registered strategy."""
    return [
        {
            "name": name,
            "description": cls.description,
            "params": cls.params_model().model_dump(mode="json"),
        }
        for name, cls in STRATEGIES.items()
    ]


__all__ = [
    "STRATEGIES",
    "BasicStrategy",
    "CaseContext",
    "InformationGatheringStrategy",
    "Memory",
    "MemoryEntry",
    "Question",
    "StrategyParams",
    "StrategySession",
    "build_strategy",
    "describe_strategies",
    "parse_params",
    "strategy_class",
]
