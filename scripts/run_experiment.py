#!/usr/bin/env python3
"""Run an experiment from a config file.

    .venv/bin/python scripts/run_experiment.py --config configs/basic.json

Every selected case is run with every strategy in the config, and the experiment record is
saved where the config's ``output`` says. Options such as ``--max-cases 2`` or
``--max-iterations 3`` override the config for a quick trial; ``--help`` lists them all.
Paths inside the config are relative to the project root, wherever this is run from.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Importable without an editable install: the experiment packages live at the project root and
# the environment's packages (medsim, bench) under environment/.
sys.path[:0] = [str(ROOT), str(ROOT / "environment")]

from experiment.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(project_root=ROOT))
