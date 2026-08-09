"""Generate the complete per-cell Gamma_temporal summary table (P5 Appendix) from the archived JSONs.

Reads (package-relative):
  ../r1_v4chat_dose_response_per_seed.json          (R1 V4-Chat dose-response, 90 records)
  ../recomputed_cell_means_FIXED.json                (Round-3 deepseek-v4-pro + qwen3.7-plus, p=0.8)
  ../p5_grid_v4flash_20260807.json                   (rebuilt deepseek-v4-flash grid, 18 cells)

Writes ../analyses/full_percell_table_20260808.json and prints LaTeX rows for the appendix table.
Deterministic: every value is a direct aggregate of the archived per-seed numbers.
"""

import json
import os
import re
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
OUT = os.path.join(BASE, "analyses", "full_percell_table_20260808.json")

ARCH = {"append_only": "Append-Only", "rag": "RAG+Filter", "summarization": "Summarization"}


def load(name):
    return json.load(open(os.path.join(BASE, name), encoding="utf-8"))


def rows_from_r1(r1):
    cells = {}
    for rec in r1:
        key = ("DeepSeek V4-Chat (R1)", "length", ARCH[rec["architecture"]], float(rec["contamination_rate"]))
        cells.setdefault(key, []).append(float(rec["gamma_temporal"]))
    out = []
    for (model, bias, arch, rate), vals in sorted(cells.items()):
        out.append({
            "model": model, "bias": bias, "architecture": arch, "rate": rate,
            "mean": round(st.mean(vals), 4), "sd": round(st.stdev(vals), 4) if len(vals) > 1 else 0.0,
            "n": len(vals),
        })
    return out


def rows_from_fixed(fixed):
    out = []
    for key, cell in fixed.items():
        m = re.match(r"^(deepseek-v4-pro|qwen3.7-plus)-(Append-Only|RAG\+Filter|Summarization)-(authority|length)-p([0-9.]+)$", key)
        if not m:
            raise ValueError(f"unparsable fixed key: {key}")
        model, arch, bias, rate = m.groups()
        model_label = "deepseek-v4-pro (Round-3)" if model == "deepseek-v4-pro" else "qwen3.7-plus (Round-3)"
        out.append({
            "model": model_label, "bias": bias, "architecture": arch, "rate": float(rate),
            "mean": round(cell["mean"], 4),
            "sd": round(st.stdev(cell["gammas"]), 4) if len(cell["gammas"]) > 1 else 0.0,
            "n": cell["n"],
        })
    return out


def rows_from_grid(grid):
    out = []
    for key, cell in grid["cells"].items():
        bias, arch, rate_tag = key.split("|")
        rate = float(rate_tag[1:])
        out.append({
            "model": "deepseek-v4-flash (rebuilt grid)",
            "bias": bias, "architecture": arch, "rate": rate,
            "mean": round(cell["mean"], 4), "sd": round(cell["sd"], 4), "n": cell["n"],
        })
    return out


def main():
    r1 = load("r1_v4chat_dose_response_per_seed.json")
    fixed = load("recomputed_cell_means_FIXED.json")
    grid = load("p5_grid_v4flash_20260807.json")
    all_rows = rows_from_r1(r1) + rows_from_fixed(fixed) + rows_from_grid(grid)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"n_cells": len(all_rows), "rows": all_rows}, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    header = "Model & Bias & Architecture & $p$ & Mean & SD & $n$ \\\\"
    print(header)
    for r in sorted(all_rows, key=lambda x: (x["model"], x["bias"], x["architecture"], x["rate"])):
        print(f"{r['model']} & {r['bias']} & {r['architecture']} & {r['rate']:.1f} & "
              f"{r['mean']:.4f} & {r['sd']:.4f} & {r['n']} \\\\")
    print("saved:", OUT)


if __name__ == "__main__":
    main()
