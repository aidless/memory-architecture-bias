"""scoring — offline metrics for PAPER5 reproduction.

This package wraps the protocol §5 metrics into importable functions so
that downstream analysis (Jupyter notebooks, ablation tooling, R3 rebuttal
analysis) can reuse them without copy-pasting the formulas.

Public surface
--------------
- ``gamma_monitor`` — Γ_temporal, Γ_content, Γ_retrieval, ΔECE, bootstrap CI.
- ``(no other modules yet)``

See ``scoring/gamma_monitor.py`` for the full implementation.
"""
from .gamma_monitor import (
    gamma_temporal, gamma_content, gamma_retrieval, gamma_decomposition,
    ece, delta_ece, bootstrap_ci, output_lengths,
)

__all__ = [
    "gamma_temporal", "gamma_content", "gamma_retrieval", "gamma_decomposition",
    "ece", "delta_ece", "bootstrap_ci", "output_lengths",
]
__version__ = "1.0.0"