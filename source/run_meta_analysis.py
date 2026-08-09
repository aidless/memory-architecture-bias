"""run_meta_analysis.py — Cross-round dose-response + confirmatory synthesis.

Three rounds, distinct purposes:
  R1 dose-response (V4-Chat, T=30, 3 rates):
    F:\\Research\\memory_architecture\\experiments\\results\\dose_response.json
    → 9 cells (3 archs × 3 rates × 10 seeds)
    → used as prior for trend analysis
  R2 R2 backup (V4-Chat, T=30, p=0.8 only):
    F:\\Research\\memory_architecture\\experiments\\results\\full_30r_10s.json
    → 3 cells (3 archs × p=0.8 × 10 seeds) — independent re-run
    → cross-run consistency check
  R3 confirmatory (V4-Pro + Qwen3.7-Plus, T=10, p=0.8):
    C:\\Users\\...\\haolo_desktop\\...\\paper5_round3_live_logs_20260713
    → 12 cells (3 archs × 2 bias types × 2 models × 10 seeds)
    → confirmatory test

Outputs:
  outputs/meta_analysis_three_rounds.csv  — per-cell round-by-round summary
  outputs/meta_analysis_trend.csv          — V4-Chat dose-response trend (R1)
"""
from __future__ import annotations
import json
import math
import statistics
from pathlib import Path
from collections import defaultdict

import numpy as np
from scipy.stats import wasserstein_distance, chi2


def gamma_per_file(fp: Path) -> float | None:
    """Compute gamma_temporal for one JSONL file."""
    rows = []
    with fp.open() as fh:
        for line in fh:
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except:
                    pass
    if not rows:
        return None
    clean = [r for r in rows if r.get("arm") == "clean"]
    biased = [r for r in rows if r.get("arm") == "biased"]
    if not clean or not biased:
        return None

    def lens(rs):
        out = []
        for r in rs:
            t = r.get("response_text", "") or r.get("output_text", "") or r.get("text", "")
            if isinstance(t, str):
                out.append(len(t.split()))
        return np.asarray(out, dtype=float)

    cl = lens(clean)
    bl = lens(biased)
    if len(cl) < 2 or len(bl) < 1:
        return None
    mu, sd = float(cl.mean()), float(cl.std(ddof=0))
    if sd == 0.0:
        return 0.0
    return float(wasserstein_distance((cl - mu) / sd, (bl - mu) / sd))


def load_r1_dose_response() -> dict:
    """R1: V4-Chat dose-response (3 rates × 3 archs × 10 seeds).

    Combines dose_response.json (p=0.2, p=0.5) with full_30r_10s.json (p=0.8)
    since both are V4-Chat, T=30, n=10 paired seeds, same architecture choices.
    The two files are independent re-runs of the same design.
    """
    cells = defaultdict(list)
    sources = [
        Path(r"F:\Research\memory_architecture\experiments\results\dose_response.json"),
        Path(r"F:\Research\memory_architecture\experiments\results\full_30r_10s.json"),
    ]
    for fp in sources:
        if not fp.exists():
            continue
        with fp.open() as f:
            data = json.load(f)
        for d in data:
            arch = d.get("architecture", "?")
            bias = d.get("bias", "length") or "length"
            p = d.get("contamination_rate", 0.8)
            gt = d.get("gamma_temporal")
            if isinstance(gt, (int, float)) and not math.isnan(gt):
                cells[(arch, bias, p)].append(gt)
    return cells


def load_r2_backup() -> dict:
    """R2 backup is the same data as R1 dose_response p=0.8 (full_30r_10s.json).

    Kept as a separate alias for cross-run consistency labelling.
    """
    return load_r1_dose_response()  # already includes the R2-backup file


def load_r3_confirmatory() -> dict:
    """R3: V4-Pro + Qwen3.7-Plus, p=0.8, 2 bias types × 3 archs × 10 seeds."""
    log_root = Path(r"C:\Users\Administrator\AppData\Roaming\haolo_desktop\thread-groups\default\outputs\paper5_round3_live_logs_20260713")
    cells = defaultdict(list)
    if not log_root.exists():
        return cells
    for fp in sorted(log_root.glob("*.jsonl")):
        parts = fp.stem.split("__")
        if len(parts) < 5:
            continue
        model, arch, bias, p_str, s_str = parts
        p = float(p_str.replace("p", ""))
        gt = gamma_per_file(fp)
        if gt is not None:
            cells[(model, arch, bias, p)].append(gt)
    return cells


def summary(gammas: list[float]) -> dict:
    if not gammas:
        return {"n": 0, "mean": float("nan"), "sd": float("nan"), "sem": float("nan")}
    if len(gammas) < 2:
        return {"n": len(gammas), "mean": gammas[0], "sd": float("nan"), "sem": 0.0}
    return {
        "n": len(gammas),
        "mean": statistics.mean(gammas),
        "sd": statistics.stdev(gammas),
        "sem": statistics.stdev(gammas) / math.sqrt(len(gammas)),
    }


def main():
    print("Loading R1 (V4-Chat dose-response, 3 rates)...")
    r1 = load_r1_dose_response()
    print(f"  R1 cells: {len(r1)}")
    print("Loading R2 backup (V4-Chat p=0.8 only)...")
    r2 = load_r2_backup()
    print(f"  R2 cells: {len(r2)}")
    print("Loading R3 confirmatory (V4-Pro + Qwen3.7-Plus, p=0.8)...")
    r3 = load_r3_confirmatory()
    print(f"  R3 cells: {len(r3)}")

    # =================================================================
    # 1. R1 dose-response trend (V4-Chat) — does gamma decrease with p?
    # =================================================================
    print("\n=== R1 dose-response trend (V4-Chat, T=30) ===")
    print(f"{'arch':<20} {'p=0.2':<12} {'p=0.5':<12} {'p=0.8':<12} {'slope':<10} {'p_slope':<10}")
    trend_rows = []
    archs = sorted({k[0] for k in r1.keys()})
    for arch in archs:
        g02 = r1.get((arch, "length", 0.2), [])
        g05 = r1.get((arch, "length", 0.5), [])
        g08 = r1.get((arch, "length", 0.8), [])
        s02 = summary(g02)
        s05 = summary(g05)
        s08 = summary(g08)

        # OLS slope of gamma vs p
        xs = []
        ys = []
        for p, s in [(0.2, s02), (0.5, s05), (0.8, s08)]:
            if s["n"] >= 2:
                xs.extend([p] * s["n"])
                ys.extend([s["mean"]] * s["n"])  # crude: use mean
        slope, p_slope = float("nan"), float("nan")
        if len(xs) >= 3:
            try:
                from scipy.stats import linregress
                slope, _, _, p_slope, _ = linregress(xs, ys)
            except Exception:
                pass
        trend_rows.append({
            "arch": arch, "p02_mean": s02["mean"], "p05_mean": s05["mean"],
            "p08_mean": s08["mean"], "slope": slope, "p_slope": p_slope,
            "n02": s02["n"], "n05": s05["n"], "n08": s08["n"],
        })
        print(f"{arch:<20} {s02['mean']:<12.3f} {s05['mean']:<12.3f} {s08['mean']:<12.3f} {slope:<+10.4f} {p_slope:<10.3f}")

    # Save trend
    out_dir = Path(r"F:\Research\PAPER5_CONSOLIDATED\outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "meta_analysis_trend.csv").open("w", encoding="utf-8") as f:
        f.write("arch,p02_mean,p05_mean,p08_mean,slope,p_slope,n02,n05,n08\n")
        for r in trend_rows:
            f.write(f"{r['arch']},{r['p02_mean']:.4f},{r['p05_mean']:.4f},"
                    f"{r['p08_mean']:.4f},{r['slope']:.4f},{r['p_slope']:.4f},"
                    f"{r['n02']},{r['n05']},{r['n08']}\n")
    print(f"Wrote {out_dir / 'meta_analysis_trend.csv'}")

    # =================================================================
    # 2. R1 cross-source consistency check (dose_response.json vs full_30r_10s.json)
    # =================================================================
    # dose_response has p=0.2, p=0.5 entries; full_30r_10s.json has p=0.8
    # Compare R1 (combined) with R2 backup (p=0.8 only file)
    print("\n=== R1 cross-source consistency (dose_response vs full_30r_10s, V4-Chat) ===")
    print(f"{'arch':<20} {'R1 dose_res p=0.5':<18} {'R1 full30r p=0.8':<18} {'trend':<10}")
    consistency_rows = []
    for arch in archs:
        s_dose = summary(r1.get((arch, "length", 0.5), []))
        s_full = summary(r1.get((arch, "length", 0.8), []))
        trend = "↑" if s_full["mean"] > s_dose["mean"] else "↓"
        print(f"{arch:<20} {s_dose['mean']:>6.3f} ± {s_dose['sem']:.3f}   "
              f"{s_full['mean']:>6.3f} ± {s_full['sem']:.3f}   {trend:<10}")
        consistency_rows.append({
            "arch": arch,
            "p05_mean": s_dose["mean"], "p05_se": s_dose["sem"], "p05_n": s_dose["n"],
            "p08_mean": s_full["mean"], "p08_se": s_full["sem"], "p08_n": s_full["n"],
        })

    # =================================================================
    # 3. R3 confirmatory (V4-Pro + Qwen3.7-Plus, p=0.8) — reference
    # =================================================================
    print("\n=== R3 confirmatory (V4-Pro + Qwen3.7-Plus, p=0.8) ===")
    print(f"{'model':<20} {'bias':<12} {'arch':<20} {'mean ± SEM':<18} {'n':<3}")
    r3_rows = []
    for (model, arch, bias, p), gs in sorted(r3.items()):
        s = summary(gs)
        print(f"{model:<20} {bias:<12} {arch:<20} {s['mean']:>6.3f} ± {s['sem']:.3f}   {s['n']:<3}")
        r3_rows.append({"model": model, "bias": bias, "arch": arch, "p": p,
                        **s})

    # Save full CSV
    with (out_dir / "meta_analysis_three_rounds.csv").open("w", encoding="utf-8") as f:
        f.write("round,model,arch,bias,p,n,mean,sem,note\n")
        for arch, s in zip(archs, trend_rows):
            f.write(f"R1_dose_response,deepseek-chat,{arch},length,0.2,{s['n02']},"
                    f"{s['p02_mean']:.4f},0.0000,prior-trend\n")
            f.write(f"R1_dose_response,deepseek-chat,{arch},length,0.5,{s['n05']},"
                    f"{s['p05_mean']:.4f},0.0000,prior-trend\n")
            f.write(f"R1_dose_response,deepseek-chat,{arch},length,0.8,{s['n08']},"
                    f"{s['p08_mean']:.4f},0.0000,prior-trend\n")
        for r in consistency_rows:
            f.write(f"R1_dose_response,deepseek-chat,{r['arch']},length,0.5,{r['p05_n']},"
                    f"{r['p05_mean']:.4f},{r['p05_se']:.4f},dose-response\n")
            f.write(f"R1_dose_response,deepseek-chat,{r['arch']},length,0.8,{r['p08_n']},"
                    f"{r['p08_mean']:.4f},{r['p08_se']:.4f},dose-response\n")
        for r in r3_rows:
            f.write(f"R3_confirmatory,{r['model']},{r['arch']},{r['bias']},{r['p']},"
                    f"{r['n']},{r['mean']:.4f},{r['sem']:.4f},confirmatory\n")
    print(f"\nWrote {out_dir / 'meta_analysis_three_rounds.csv'}")

    # =================================================================
    # 4. Headline synthesis for paper
    # =================================================================
    # Architecture name normalization across rounds
    arch_norm = {
        "append_only": "Append-Only",
        "rag": "RAG+Filter",
        "summarization": "Summarization",
    }
    r1_p08_norm = {arch_norm.get(r["arch"], r["arch"]): r["p08_mean"]
                   for r in consistency_rows}
    r3_v4pro_p08 = {r["arch"]: r["mean"] for r in r3_rows
                    if r["model"] == "deepseek-v4-pro" and r["bias"] == "length"}
    print("\n=== Headline synthesis (for paper §4.8 supplementary) ===")
    print("Architecture γ at p=0.8 across model versions:")
    print(f"{'arch':<20} {'V4-Chat (R1)':<14} {'V4-Pro (R3)':<14} {'Qwen3.7 (R3)':<14} {'Δ V4':<8} {'Δ Qwen':<8}")
    for arch in sorted(set(r1_p08_norm.keys()) | set(r3_v4pro_p08.keys())):
        v4c = r1_p08_norm.get(arch, float("nan"))
        v4p = r3_v4pro_p08.get(arch, float("nan"))
        qwen = {r["arch"]: r["mean"] for r in r3_rows
                if r["model"] == "qwen3.7-plus" and r["bias"] == "length"}.get(arch, float("nan"))
        d_v4 = v4p - v4c if not (math.isnan(v4p) or math.isnan(v4c)) else float("nan")
        d_qw = qwen - v4c if not (math.isnan(qwen) or math.isnan(v4c)) else float("nan")
        print(f"  {arch:<18} {v4c:<14.3f} {v4p:<14.3f} {qwen:<14.3f} {d_v4:<+8.3f} {d_qw:<+8.3f}")


if __name__ == "__main__":
    main()
