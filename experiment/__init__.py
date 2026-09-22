"""Experiments comparing information gathering strategies against the simulated environment.

An experiment runs every selected case with every configured strategy. In each case run the
strategy asks questions, the environment answers them, and the answers accumulate in the
strategy's memory until a stopping criterion (iterations or time) is reached. Everything is
saved to one experiment record.
"""

from __future__ import annotations

from experiment.config import ExperimentConfig, StoppingCriteria, StrategySpec, load_config
from experiment.progress import ProgressTracker
from experiment.record import CaseRun, ExperimentRecord, Iteration, load_record
from experiment.runner import ExperimentListener, ExperimentPlan, ExperimentRunner

__all__ = [
    "CaseRun",
    "ExperimentConfig",
    "ExperimentListener",
    "ExperimentPlan",
    "ExperimentRecord",
    "ExperimentRunner",
    "Iteration",
    "ProgressTracker",
    "StoppingCriteria",
    "StrategySpec",
    "load_config",
    "load_record",
]
