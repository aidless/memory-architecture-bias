"""Recompute PAPER5 Table 2 (R1 V4-Chat dose-response contrasts) from the archived per-seed JSON.

Usage:
    python analyze_r1_dose_response_20260807.py [path/to/r1_v4chat_dose_response_per_seed.json]

Default input: ../r1_v4chat_dose_response_per_seed.json (relative to this script).
Output: ../analyses/r1_dose_response_contrasts.json plus a printed 9-contrast table.
All values are deterministic functions of the archived per-seed gamma_temporal records.
"""

import json
import math
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
DEFAULT_IN = os.path.join(BASE, "r1_v4chat_dose_response_per_seed.json")
OUT = os.path.join(BASE, "analyses", "r1_dose_response_contrasts.json")

ARCHS = ["append_only", "rag", "summarization"]
ARCH_LABEL = {
    "append_only": "Append-Only",
    "rag": "RAG+Filter",
    "summarization": "Summarization",
}
RATES = [0.2, 0.5, 0.8]
# Orientation matches Table 2 ("Comparison" column): first label minus second label.
PAIRS = [
    ("append_only", "rag"),
    ("append_only", "summarization"),
    ("summarization", "rag"),
]


def betacf(a, b, x, itmax=200, eps=3e-12):
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def betai(a, b, x):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lnbt = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log1p(-x)
    )
    bt = math.exp(lnbt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * betacf(a, b, x) / a
    return 1.0 - bt * betacf(b, a, 1.0 - x) / b


def t_twotailed_p(t, df):
    """Two-tailed p-value of Student's t with df degrees of freedom."""
    x = df / (df + t * t)
    return betai(df / 2.0, 0.5, x)


def paired_t(diffs, df=9):
    """Paired t-test on per-seed differences (t-distribution, df=9).

    Returns (mean_diff, t, p, d_z, n).
    """
    n = len(diffs)
    m = st.mean(diffs)
    s = st.stdev(diffs) if n > 1 else 0.0
    if s == 0.0:
        return m, 0.0, 1.0, 0.0, n
    t = m / (s / math.sqrt(n))
    p = t_twotailed_p(t, df)
    d_z = m / s
    return m, t, p, d_z, n


def holm(ps):
    """Holm-Bonferroni adjusted p-values (FWER)."""
    k = len(ps)
    idx = sorted(range(k), key=lambda i: ps[i])
    adj = [0.0] * k
    prev = 0.0
    for r, i in enumerate(idx):
        adj[i] = max(min(1.0, ps[i] * (k - r)), prev)
        prev = adj[i]
    return adj


def bh(ps):
    """Benjamini-Hochberg adjusted p-values (FDR)."""
    k = len(ps)
    idx = sorted(range(k), key=lambda i: ps[i])
    adj = [0.0] * k
    for r, i in enumerate(idx):
        adj[i] = min(1.0, ps[i] * k / (r + 1))
    monotone = [adj[i] for i in idx]
    for j in range(k - 2, -1, -1):
        monotone[j] = min(monotone[j], monotone[j + 1])
    for r, i in enumerate(idx):
        adj[i] = monotone[r]
    return adj


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IN
    rows = json.load(open(src, encoding="utf-8"))

    cells = {}
    for r in rows:
        key = (r["architecture"], float(r["contamination_rate"]))
        cells.setdefault(key, []).append(float(r["gamma_temporal"]))
    for key, vals in cells.items():
        if len(vals) != 10:
            raise ValueError(f"expected 10 seeds per cell, got {len(vals)} at {key}")

    contrasts = []
    for rate in RATES:
        for a1, a2 in PAIRS:
            diffs = [x - y for x, y in zip(cells[(a1, rate)], cells[(a2, rate)])]
            m, t, p, d_z, n = paired_t(diffs)
            contrasts.append(
                {
                    "rate": rate,
                    "architecture_a": ARCH_LABEL[a1],
                    "architecture_b": ARCH_LABEL[a2],
                    "mean_diff_a_minus_b": round(m, 4),
                    "t": round(t, 4),
                    "p_raw": round(p, 4),
                    "d_z": round(d_z, 4),
                    "n_seeds": n,
                    "df": 9,
                }
            )

    raw = [c["p_raw"] for c in contrasts]
    holm9 = holm(raw)
    bh9 = bh(raw)
    for c, h, b in zip(contrasts, holm9, bh9):
        c["p_holm_k9"] = round(h, 4)
        c["p_bh_k9"] = round(b, 4)

    # within-rate family (k=3), per Table 2's within-table Bonferroni column
    for rate in RATES:
        sub = [c for c in contrasts if c["rate"] == rate]
        for c, p in zip(sub, [min(1.0, c["p_raw"] * 3) for c in sub]):
            c["p_bonf_k3"] = round(p, 4)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(
        {
            "input": os.path.relpath(src, BASE),
            "n_records": len(rows),
            "method": "paired t-test on per-seed gamma_temporal differences (n=10); d_z = mean/sd of differences; Holm and BH over the k=9 family; Bonferroni k=3 within rate",
            "contrasts": contrasts,
        },
        open(OUT, "w", encoding="utf-8"),
        ensure_ascii=False,
        indent=1,
    )

    header = f"{'rate':>5} {'architecture_a':>14} {'architecture_b':>14} {'t':>8} {'p_raw':>8} {'d_z':>7} {'holm_k9':>8} {'bh_k9':>8} {'bonf_k3':>8}"
    print(header)
    for c in contrasts:
        print(
            f"{c['rate']:>5} {c['architecture_a']:>14} {c['architecture_b']:>14} "
            f"{c['t']:>8} {c['p_raw']:>8} {c['d_z']:>7} "
            f"{c['p_holm_k9']:>8} {c['p_bh_k9']:>8} {c['p_bonf_k3']:>8}"
        )
    print("saved:", OUT)


if __name__ == "__main__":
    main()
