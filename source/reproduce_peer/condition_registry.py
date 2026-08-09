"""reproduce_peer.condition_registry — canonical condition table from protocol §1.

Frozen registry of all 15 conditions + 1 sensitivity probe. Every condition
in this table MUST appear once and only once in ``outputs/protocol_run.jsonl``.

Canonical registry (protocol §1):
    D-{A,S,R}-{02,05,08}   : DeepSeek length  (9 cells, n=10, T=30)
    Q-{A,S,R}-08            : Qwen length      (3 cells, n=10, T=10)
    Q-{A,S,R}-AU            : Qwen authority   (3 cells, n=10, T=10)

Sensitivity probe (NOT canonical, protocol §3.5):
    D-R-DENSE-05            : RAG dense SVD-64 (n=5, T=30, p=0.5, theta=0.3)

Total canonical: 15 conditions × n seeds × T rounds × 2 agents = 6,360 calls
(per protocol §6, accounting for paired biased+clean runs).
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Condition:
    condition_id: str
    model: str          # "deepseek" | "qwen"
    bias_type: str      # "length" | "authority"
    architecture: str   # "Append-Only" | "Summarization" | "RAG+Filter"
    p: float            # contamination rate in {0.2, 0.5, 0.8}
    n_seeds: int        # 10 for DeepSeek Face 1, 10 for Qwen n=10
    n_rounds: int       # 30 for DeepSeek, 10 for Qwen
    theta: float = 0.1  # RAG threshold (0.3 for SVD-64 sensitivity probe)
    is_canonical: bool = True
    role: str = "main"  # "main" | "sensitivity"

    @property
    def calls_per_run(self) -> int:
        """Solver+summarizer calls per single arm (one seed, one architecture, one agent)."""
        # Per round: 1 solver call + (1 summarizer call if architecture == Summarization).
        # For RAG+SVD-64 we do not summarize.
        per_round = 1 + (1 if self.architecture == "Summarization" else 0)
        return self.n_rounds * per_round


CONDITIONS: list[Condition] = [
    # DeepSeek Face 1 — length bias, dose-response (9 cells, n=10 seeds, T=30)
    Condition("D-A-02", "deepseek", "length", "Append-Only",     0.2, 10, 30),
    Condition("D-A-05", "deepseek", "length", "Append-Only",     0.5, 10, 30),
    Condition("D-A-08", "deepseek", "length", "Append-Only",     0.8, 10, 30),
    Condition("D-S-02", "deepseek", "length", "Summarization",   0.2, 10, 30),
    Condition("D-S-05", "deepseek", "length", "Summarization",   0.5, 10, 30),
    Condition("D-S-08", "deepseek", "length", "Summarization",   0.8, 10, 30),
    Condition("D-R-02", "deepseek", "length", "RAG+Filter",      0.2, 10, 30),
    Condition("D-R-05", "deepseek", "length", "RAG+Filter",      0.5, 10, 30),
    Condition("D-R-08", "deepseek", "length", "RAG+Filter",      0.8, 10, 30),
    # Qwen Face 2 — length bias at p=0.8 (3 cells, n=10 seeds, T=10)
    Condition("Q-A-08", "qwen",     "length", "Append-Only",     0.8, 10, 10),
    Condition("Q-S-08", "qwen",     "length", "Summarization",   0.8, 10, 10),
    Condition("Q-R-08", "qwen",     "length", "RAG+Filter",      0.8, 10, 10),
    # Qwen Face 2 — authority bias at p=0.8 (3 cells, n=10 seeds, T=10)
    Condition("Q-A-AU", "qwen",     "authority", "Append-Only",   0.8, 10, 10),
    Condition("Q-S-AU", "qwen",     "authority", "Summarization", 0.8, 10, 10),
    Condition("Q-R-AU", "qwen",     "authority", "RAG+Filter",    0.8, 10, 10),
    # DeepSeek authority at p=0.8 (3 cells, n=10 seeds, T=10; logs: cow legacy + round3 flat)
    Condition("D-A-AU", "deepseek", "authority", "Append-Only",     0.8, 10, 10),
    Condition("D-S-AU", "deepseek", "authority", "Summarization",   0.8, 10, 10),
    Condition("D-R-AU", "deepseek", "authority", "RAG+Filter",      0.8, 10, 10),
    # Sensitivity probe — RAG dense SVD-64 (n=5, T=30, p=0.5, theta=0.3)
    Condition("D-R-DENSE-05", "deepseek", "length", "RAG+Dense", 0.5, 5, 30,
              theta=0.3, is_canonical=False, role="sensitivity"),
]

CONDITION_GROUPS: dict[str, list[str]] = {
    "deepseek_length": [c.condition_id for c in CONDITIONS
                        if c.model == "deepseek" and c.bias_type == "length" and c.is_canonical],
    "qwen_length":     [c.condition_id for c in CONDITIONS
                        if c.model == "qwen" and c.bias_type == "length"],
    "qwen_authority":  [c.condition_id for c in CONDITIONS
                        if c.model == "qwen" and c.bias_type == "authority"],
    "deepseek_authority": [c.condition_id for c in CONDITIONS
                        if c.model == "deepseek" and c.bias_type == "authority"],
    "sensitivity":     [c.condition_id for c in CONDITIONS if not c.is_canonical],
}


def get(condition_id: str) -> Condition:
    """Look up a condition by ID. Raises KeyError if not found."""
    for c in CONDITIONS:
        if c.condition_id == condition_id:
            return c
    raise KeyError(f"Unknown condition_id: {condition_id!r}. "
                   f"Valid IDs: {[c.condition_id for c in CONDITIONS]}")


__all__ = ["Condition", "CONDITIONS", "CONDITION_GROUPS", "get"]