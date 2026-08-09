# -*- coding: utf-8 -*-
"""P5 external-task replication summary (2026-08-09; deviation: qwen3.7-plus -> gpt-5.4-mini).
Reads analyses/p5_external_task_20260809.json; per model computes the paired
Summarization-minus-Append gamma contrast across seeds (direction + raw p).
Writes analyses/p5_external_task_summary_20260809.json."""
import os, json, math, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
IN = os.path.join(BASE, "analyses", "p5_external_task_20260809.json")
OUT = os.path.join(BASE, "analyses", "p5_external_task_summary_20260809.json")

def paired_stats(a, b):
    n = min(len(a), len(b))
    d = [x - y for x, y in zip(a[:n], b[:n])]
    m = st.mean(d)
    if n <= 1:
        return m, None, n
    s = st.stdev(d)
    if s == 0:
        return m, 1.0, n
    t = m / (s / math.sqrt(n))
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))
    return m, p, n

rows = json.load(open(IN, encoding="utf-8"))
out = {"case": "external-task replication (open-ended generation; biased arm = expand with more detail)",
       "deviation": "qwen3.7-plus unavailable (DashScope Arrearage); substituted gpt-5.4-mini via Youle relay; see evidence/deviation_external_task_20260809.md",
       "models": {}}
for model in sorted({r["model"] for r in rows}):
    by = {r["arch"]: r for r in rows if r["model"] == model}
    summ = by.get("Summarization"); app = by.get("Append-Only")
    entry = {}
    for arch in ["Append-Only", "Summarization", "RAG+Filter"]:
        r = by.get(arch)
        entry[arch] = {"gamma": r["gamma"], "n_seeds": r["n"]}
    if summ and app:
        m, p, n = paired_stats(summ["seeds"], app["seeds"])
        entry["Summ_minus_Append"] = {"diff": round(m, 4), "p_raw": (round(p, 4) if p is not None else None),
                                      "n": n, "direction": "Summ-lower" if m < 0 else ("Summ-higher" if m > 0 else "tie")}
    out["models"][model] = entry
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for model, e in out["models"].items():
    sc = e.get("Summ_minus_Append", {})
    print(f"{model:20s} Summ={e['Summarization']['gamma']:.4f} Append={e['Append-Only']['gamma']:.4f} "
          f"diff={sc.get('diff'):+.4f} p={sc.get('p_raw')} n={sc.get('n')} dir={sc.get('direction')}")
print("saved", OUT)