"""medsim: a simulated text-only medical environment for evaluating diagnostic agents.

Answers not stated in the case study are synthesized from literature. They are simulation
artifacts, not clinical claims.
"""

from __future__ import annotations

__version__ = "0.1.0"

from medsim.environment import MedicalEnvironment
from medsim.models import CaseStudy, EnvironmentResponse, LiteratureSearchResult, RetrievedDocument

__all__ = [
    "CaseStudy",
    "EnvironmentResponse",
    "LiteratureSearchResult",
    "MedicalEnvironment",
    "RetrievedDocument",
    "__version__",
]
