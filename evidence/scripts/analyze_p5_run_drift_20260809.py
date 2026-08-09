# -*- coding: utf-8 -*-
"""P5 cross-run drift: deepseek-v4-pro architecture ordering, Round-3 (10 seeds) vs Round-4 (30 seeds) @ p=0.8.
Inputs: recomputed_cell_means_FIXED.json (Round-3), round4_validation_20260808.json (Round-4)."""
import os, json, io
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
fixed = json.load(open(os.path.join(BASE, "recomputed_cell_means_FIXED.json"), encoding="utf-8"))
r4 = json.load(open(os.path.join(BASE, "analyses", "round4_validation_20260808.json"), encoding="utf-8"))
pc = r4["per_cell_mean"]
ARCHS = ["Append-Only", "Summarization", "RAG+Filter"]
out = {}
for bias in ["length", "authority"]:
    r3 = {a: round(fixed[f"deepseek-v4-pro-{a}-{bias}-p0.8"]["mean"], 4) for a in ARCHS}
    r4v = {a: pc[f"deepseek-v4-pro|{a}|{bias}|p0.8"]["mean"] for a in ARCHS}
    o3 = sorted(r3, key=lambda a: r3[a]); o4 = sorted(r4v, key=lambda a: r4v[a])
    out[bias] = {"round3_10seed": {a: r3[a] for a in ARCHS}, "round3_order": o3,
                 "round4_30seed": {a: round(r4v[a], 4) for a in ARCHS}, "round4_order": o4,
                 "order_changed": o3 != o4}
    print(f"{bias}: Round-3 order {o3} | Round-4 order {o4} | changed={o3 != o4}")
os.makedirs(os.path.join(BASE, "analyses"), exist_ok=True)
json.dump({"case": "deepseek-v4-pro cross-run architecture ordering drift @ p=0.8 (Round-3 10-seed vs Round-4 30-seed)",
           "rows": out}, open(os.path.join(BASE, "analyses", "p5_run_drift_20260809.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved analyses/p5_run_drift_20260809.json")
