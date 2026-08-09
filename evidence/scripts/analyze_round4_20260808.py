# -*- coding: utf-8 -*-
"""Round-4 offline validation + mixed-model analysis (P5-A/B for Strong Accept).
Input : paper5_round4_live_20260723 (1080 jsonl: 2 models x 3 arch x 2 bias x 3 rates x 30 seeds)
Checks: file completeness, per-record schema, gamma computation (clean-normalized word-length W1).
Output: analyses/round4_validation_20260808.json + printed mixed-model summary."""
import os, json, re, statistics as st, collections, math, io

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
ZIP = os.path.join(BASE, "round4_live.zip")
OUT = os.path.join(BASE, "analyses", "round4_validation_20260808.json")
PAT = re.compile(r"^(deepseek-v4-pro|deepseek-v4-flash)__(Append-Only|RAG\+Filter|Summarization)__(length|authority)__p(0\.\d+)__s(\d+)\.jsonl$")

def gamma_from_rows(rows):
    clean = [r for r in rows if r.get("arm") == "clean"]
    biased = [r for r in rows if r.get("arm") == "biased"]
    if not clean or not biased:
        return None
    def lens(rs):
        out = []
        for r in rs:
            t = r.get("response_text") or ""
            if isinstance(t, str):
                out.append(len(t.split()))
        return out
    cl, bl = lens(clean), lens(biased)
    if len(cl) < 2 or len(bl) < 1:
        return None
    mu = st.mean(cl)
    sd = st.stdev(cl) if len(cl) > 1 else 0.0
    if sd == 0:
        return 0.0
    return sum(abs(x - y) for x, y in zip(sorted((v - mu) / sd for v in cl), sorted((v - mu) / sd for v in bl))) / len(bl)

import zipfile
from itertools import combinations
ARCHS = ["Append-Only", "RAG+Filter", "Summarization"]
z = zipfile.ZipFile(ZIP)
files = [n for n in z.namelist() if n.endswith(".jsonl") and n != "cost_ledger.jsonl"]
assert len(files) == 1080, len(files)
cells = collections.defaultdict(dict)
schema_ok = True
for f in files:
    m = PAT.match(f)
    if not m:
        schema_ok = False
        continue
    rows = [json.loads(l) for l in z.read(f).decode("utf-8").splitlines()]
    if not rows or not all(k in rows[0] for k in ("arm", "response_text", "model_alias", "round")):
        schema_ok = False
    cells[(m.group(1), m.group(2), m.group(3), m.group(4))][int(m.group(5))] = gamma_from_rows(rows)

print("schema_ok:", schema_ok, "| cells:", len(cells), "| seeds/cell:", {k: len(v) for k, v in list(cells.items())[:3]})
# per-cell means
per_cell = {}
for (model, arch, bias, rate), seeds in cells.items():
    vals = [v for v in seeds.values() if v is not None]
    per_cell[(model, arch, bias, rate)] = {"n": len(vals), "mean": round(st.mean(vals), 4) if vals else None,
                                           "sd": round(st.stdev(vals), 4) if len(vals) > 1 else None}
# R1 contrast replication on v4-flash @ p=0.8 length: Summarization vs Append-Only
def paired_t(a, b):
    n = min(len(a), len(b))
    d = [x - y for x, y in zip(a[:n], b[:n])]
    m = st.mean(d); s = st.stdev(d) if n > 1 else 0
    if s == 0: return m, 1.0, n
    t = m / (s / math.sqrt(n))
    from math import erf
    p = 2 * (1 - 0.5 * (1 + erf(abs(t) / math.sqrt(2))))
    return m, p, n

rep = {}
for model in ["deepseek-v4-flash", "deepseek-v4-pro"]:
    key = (model, "Summarization", "length", "0.8")
    key2 = (model, "Append-Only", "length", "0.8")
    if key in cells and key2 in cells:
        a = [cells[key][s] for s in sorted(cells[key]) if cells[key][s] is not None]
        b = [cells[key2][s] for s in sorted(cells[key2]) if cells[key2][s] is not None]
        m, p, n = paired_t(a, b)
        rep[model] = {"n": n, "diff_sum_app": round(m, 4), "p_raw": round(p, 4)}
        print(f"R1 replication {model} Summ-vs-Append @p0.8: diff={m:+.4f} p={p:.4f} n={n}")

summary = {
  "files": 1080, "cells": len(cells), "schema_ok": schema_ok,
  "per_cell_mean": {f"{k[0]}|{k[1]}|{k[2]}|p{k[3]}": v for k, v in per_cell.items()},
  "r1_contrast_replication": rep,
  "note": "gamma = clean-normalized word-length W1 (same as R1 and v4-flash grid).",
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)


# ---- k=9 family-level BH + Holm per model x bias (OSF Analysis Plan) ----
def bh(ps):
    k = len(ps); idx = sorted(range(k), key=lambda i: ps[i])
    out = [None]*k
    for r, i in enumerate(idx):
        out[i] = min(1.0, ps[i]*k/(r+1))
    m2 = [out[i] for i in idx]
    for j in range(k-2, -1, -1):
        m2[j] = min(m2[j], m2[j+1])
    for r, i in enumerate(idx):
        out[i] = m2[r]
    return out

def holm(ps):
    k = len(ps); idx = sorted(range(k), key=lambda i: ps[i])
    out = [None]*k
    for r, i in enumerate(idx):
        out[i] = min(1.0, ps[i] * (k - r))
    return out

family9 = {}
for model in ["deepseek-v4-flash", "deepseek-v4-pro"]:
    for bias in ["length", "authority"]:
        tests = []
        for rate in ["0.2", "0.5", "0.8"]:
            for a1, a2 in combinations(ARCHS, 2):
                c1 = cells.get((model, a1, bias, rate), {}); c2 = cells.get((model, a2, bias, rate), {})
                s1 = [c1[k] for k in sorted(c1) if c1[k] is not None]
                s2 = [c2[k] for k in sorted(c2) if c2[k] is not None]
                if len(s1) >= 5 and len(s2) >= 5:
                    m, pp, n = paired_t(s1, s2)
                    tests.append({"contrast": f"{a1} vs {a2}", "rate": rate, "diff": round(m, 4), "p_raw": round(pp, 4), "n": n})
        ps = [t["p_raw"] for t in tests]
        b = bh(ps); h = holm(ps)
        for t, bp, hp in zip(tests, b, h):
            t["p_bh_k9"] = round(bp, 4); t["p_holm_k9"] = round(hp, 4)
        family9[f"{model}|{bias}"] = {"k": len(tests),
            "survive_bh_k9": [t["contrast"] + "@p" + t["rate"] for t in tests if t["p_bh_k9"] < 0.05],
            "survive_holm_k9": [t["contrast"] + "@p" + t["rate"] for t in tests if t["p_holm_k9"] < 0.05],
            "min_raw_p": min(ps) if ps else None, "tests": tests}
summary["family_audit_k9_holm"] = family9
print()
print("=== k=9 family-level BH + Holm (OSF Analysis Plan) ===")
for k, v in family9.items():
    print(f"{k}: BH={v['survive_bh_k9']} Holm={v['survive_holm_k9']}")

json.dump(summary, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved", OUT)
