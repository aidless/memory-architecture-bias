# -*- coding: utf-8 -*-
"""P5 third-model direction check (N->4): R1 V4-Chat vs Qwen3.7-Plus vs v4 checkpoints.
Summ-vs-Append @ p=0.8 length: direction and paired t on per-seed Gamma.
Inputs: r1_v4chat_dose_response_per_seed.json (R1), recomputed_cell_means_FIXED.json (Qwen),
       round4_live.zip (v4-pro/v4-flash)."""
import os, json, math, statistics as st, zipfile, io

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
def paired_t(a, b):
    n = min(len(a), len(b))
    d = [x - y for x, y in zip(a[:n], b[:n])]
    m = st.mean(d); s = st.stdev(d) if n > 1 else 0
    if s == 0: return m, 1.0, n
    t = m / (s / math.sqrt(n))
    from math import erf
    p = 2 * (1 - 0.5 * (1 + erf(abs(t) / math.sqrt(2))))
    return m, p, n

out = {}
# R1
r1 = json.load(open(os.path.join(BASE, "r1_v4chat_dose_response_per_seed.json"), encoding="utf-8"))
r1s = [r["gamma_temporal"] for r in r1 if r["architecture"] == "summarization" and r["contamination_rate"] == 0.8]
r1a = [r["gamma_temporal"] for r in r1 if r["architecture"] == "append_only" and r["contamination_rate"] == 0.8]
m, p, n = paired_t(r1s, r1a)
out["R1_V4Chat"] = {"diff": round(m, 4), "p_raw": round(p, 4), "n": n, "direction": "Summ-lower" if m < 0 else "Summ-higher"}
# Qwen
fixed = json.load(open(os.path.join(BASE, "recomputed_cell_means_FIXED.json"), encoding="utf-8"))
qw = [fixed["qwen3.7-plus-Summarization-length-p0.8"]["gammas"], fixed["qwen3.7-plus-Append-Only-length-p0.8"]["gammas"]]
m, p, n = paired_t(qw[0], qw[1])
out["Qwen3.7Plus"] = {"diff": round(m, 4), "p_raw": round(p, 4), "n": n, "direction": "Summ-lower" if m < 0 else "Summ-higher"}
# v4 (round4 zip)
import re
ZIP = os.path.join(BASE, "round4_live.zip")
PAT = re.compile(r"^(deepseek-v4-pro|deepseek-v4-flash)__(Append-Only|RAG\+Filter|Summarization)__(length|authority)__p0\.8__s(\d+)\.jsonl$")
def gamma(rows):
    clean = [r for r in rows if r.get("arm") == "clean"]; biased = [r for r in rows if r.get("arm") == "biased"]
    if not clean or not biased: return None
    def lens(rs): return [len((r.get("response_text") or "").split()) for r in rs]
    cl, bl = lens(clean), lens(biased)
    mu = st.mean(cl); sd = st.stdev(cl) if len(cl) > 1 else 0.0
    if sd == 0: return 0.0
    a = sorted((v - mu) / sd for v in cl); b = sorted((v - mu) / sd for v in bl)
    return sum(abs(x - y) for x, y in zip(a, b)) / len(bl)
with zipfile.ZipFile(ZIP) as z:
    cells = {}
    for name in z.namelist():
        mm = PAT.match(name)
        if not mm: continue
        rows = [json.loads(l) for l in z.read(name).decode("utf-8").splitlines()]
        cells.setdefault((mm.group(1), mm.group(2)), {})[int(mm.group(4))] = gamma(rows)
for model in ["deepseek-v4-pro", "deepseek-v4-flash"]:
    s_ = [cells[(model, "Summarization")][k] for k in sorted(cells[(model, "Summarization")]) if cells[(model, "Summarization")][k] is not None]
    a_ = [cells[(model, "Append-Only")][k] for k in sorted(cells[(model, "Append-Only")]) if cells[(model, "Append-Only")][k] is not None]
    m, p, n = paired_t(s_, a_)
    out[model] = {"diff": round(m, 4), "p_raw": round(p, 4), "n": n, "direction": "Summ-lower" if m < 0 else "Summ-higher"}
os.makedirs(os.path.join(BASE, "analyses"), exist_ok=True)
json.dump({"case": "R1 family-significant contrast (Summ vs Append @ p=0.8) across models",
           "rows": out}, open(os.path.join(BASE, "analyses", "p5_third_model_direction_20260809.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k, v in out.items():
    print(f"{k:18s} diff={v['diff']:+.4f} p={v['p_raw']:.4f} n={v['n']} {v['direction']}")
print("saved analyses/p5_third_model_direction_20260809.json")
