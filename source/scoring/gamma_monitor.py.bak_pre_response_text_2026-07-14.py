"""scoring.gamma_monitor — Γ_temporal and Γ decomposition from JSONL logs.

Implements the metric definitions from
``PAPER5_CONSOLIDATED/protocol.md`` §5:

    Γ_temporal = W1(P_biased_hat, P_clean_hat)
                 where output length is z-scored within each arm of each
                 paired condition using the clean arm's mean and std.

    Γ_content  = W1 of stored content (Summarization case only — for
                 Append-Only and RAG it equals Γ_temporal because outputs
                 are stored verbatim).

    Γ_retrieval = Γ_temporal - Γ_content.

    ΔECE(condition) = ECE_final(condition) - ECE_final(clean baseline
                     at matched architecture).

The functions in this module are pure-Python + NumPy + SciPy and operate
on JSONL files written by the live harnesses under
``tmp/windows/w1-paper5/data/logs/``.

Citation in paper
-----------------
If you use this module in derivative work, please cite the paper and
link the reproduction repository (see main.tex §Reproducibility).
"""
from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy.stats import wasserstein_distance


def _safe_load(path: Path) -> list[dict]:
    """Load JSONL, returning list of dicts (skipping empty lines)."""
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def output_lengths(rows: list[dict]) -> np.ndarray:
    """Extract output-token counts from a list of JSONL rows.

    Each row should have a key containing the LLM-generated text. The
    accepted keys, in priority order, are: ``response_text`` (Round-3
    schema, 2026-07-13+), ``output_text`` and ``summary`` (R2 schema),
    ``text`` (legacy pilot harness). Token count is whitespace-delimited
    per protocol §4.5.

    The ``response_text`` field is the canonical Round-3 schema field
    and is checked first because the Round-3 live logs (under
    ``C:/Users/Administrator/AppData/Roaming/haolo_desktop/...``) emit
    provider-attributed rows with this key; the older pilot/R2 harnesses
    emitted ``output_text`` / ``summary`` / ``text`` depending on the
    summarizer integration.
    """
    lengths: list[int] = []
    for r in rows:
        text = (
            r.get("response_text")
            or r.get("output_text")
            or r.get("summary")
            or r.get("text")
            or ""
        )
        if isinstance(text, str):
            lengths.append(len(text.split()))
    return np.asarray(lengths, dtype=float)


def gamma_temporal(clean_rows: list[dict], biased_rows: list[dict]) -> float:
    """W_1 of z-scored output lengths, biased vs clean arm.

    Z-scoring uses the clean arm's mean and std (per protocol §5.1).
    """
    clean = output_lengths(clean_rows)
    biased = output_lengths(biased_rows)
    if len(clean) < 2 or len(biased) < 1:
        return float("nan")
    mu, sd = float(clean.mean()), float(clean.std(ddof=0))
    if sd == 0.0:
        return 0.0
    z_clean = (clean - mu) / sd
    z_biased = (biased - mu) / sd
    return float(wasserstein_distance(z_clean, z_biased))


def gamma_content(rows_biased_summary: list[dict],
                  rows_clean_summary: list[dict]) -> float:
    """Γ_content for Summarization: W_1 of summarized-length distributions.

    For Summarization the "content" stored in memory is the compressed
    one-sentence summary, not the full agent output. So Γ_content is
    the W_1 between biased-summary lengths and clean-summary lengths,
    z-scored using the clean-summary mean/std (mirroring protocol §5.1).

    For Append-Only and RAG (which store outputs verbatim), call sites
    should set Γ_content equal to Γ_temporal directly — this function
    is for Summarization only.
    """
    clean = output_lengths(rows_clean_summary)
    biased = output_lengths(rows_biased_summary)
    if len(clean) < 2 or len(biased) < 1:
        return float("nan")
    mu, sd = float(clean.mean()), float(clean.std(ddof=0))
    if sd == 0.0:
        return 0.0
    return float(wasserstein_distance((clean - mu) / sd, (biased - mu) / sd))


def gamma_retrieval(gamma_t: float, gamma_c: float) -> float:
    """Γ_retrieval = Γ_temporal - Γ_content (residual after compression)."""
    return gamma_t - gamma_c


def gamma_decomposition(gamma_t: float, architecture: str) -> tuple[float, float]:
    """Convenience wrapper: return (gamma_content, gamma_retrieval).

    For Append-Only and RAG, gamma_content == gamma_t (verbatim storage)
    and gamma_retrieval == 0. For Summarization, call sites must supply
    the explicit gamma_content from gamma_content(...).
    """
    if architecture == "Summarization":
        # Caller must supply gamma_content separately; this branch is a guard.
        raise ValueError("Summarization requires explicit gamma_content; "
                         "call gamma_content(...) and gamma_retrieval(...) directly.")
    return gamma_t, 0.0


def ece(rows: list[dict], n_bins: int = 10) -> float:
    """Expected Calibration Error over ``n_bins`` equal-width bins on [0, 1].

    Per protocol §5.3: confidence parsed from the line
    ``Confidence: <float>`` in the model output; correctness judged by
    Rouge-L F1 ≥ 0.30 against the reference summary (a stricter external
    judge is acceptable per protocol).

    Rows missing a confidence value are dropped.
    """
    pts: list[tuple[float, float]] = []  # (confidence, correct_or_not)
    for r in rows:
        c = r.get("confidence")
        y = r.get("correct")
        if c is None or y is None:
            continue
        pts.append((float(c), float(y)))
    if not pts:
        return float("nan")
    n = len(pts)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    e = 0.0
    for b in range(n_bins):
        in_bin = [(c, y) for (c, y) in pts if edges[b] <= c < edges[b + 1]]
        if not in_bin:
            continue
        conf = sum(c for c, _ in in_bin) / len(in_bin)
        acc = sum(y for _, y in in_bin) / len(in_bin)
        e += (len(in_bin) / n) * abs(conf - acc)
    return float(e)


def delta_ece(clean_rows: list[dict], biased_rows: list[dict], n_bins: int = 10) -> float:
    """ΔECE = ECE(biased) - ECE(clean) at matched architecture / seed."""
    return ece(biased_rows, n_bins) - ece(clean_rows, n_bins)


def bootstrap_ci(values: Iterable[float], n_boot: int = 1000, alpha: float = 0.05,
                 seed: int = 20260708) -> tuple[float, float, float]:
    """Return (mean, low, high) of the bootstrap 95% CI for a 1D metric."""
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot)
    for i in range(n_boot):
        sample = rng.choice(arr, size=arr.size, replace=True)
        means[i] = sample.mean()
    low = float(np.quantile(means, alpha / 2))
    high = float(np.quantile(means, 1 - alpha / 2))
    return float(arr.mean()), low, high


__all__ = [
    "output_lengths",
    "gamma_temporal", "gamma_content", "gamma_retrieval", "gamma_decomposition",
    "ece", "delta_ece",
    "bootstrap_ci",
    "_safe_load",
]