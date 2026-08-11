# -*- coding: utf-8 -*-
"""Regenerate held-out validations, evidence ledger, and input manifest (2026-08-06).

Usage:  python scripts/analyze_heldout_20260806.py
Outputs (overwrites):
  analyses/heldout_validations_20260806.json
  analyses/heldout_summary_20260806.md
  analyses/evidence_ledger_20260806.json
  analyses/evidence_ledger_20260806.md
  analyses/input_manifest_20260806.json
All random processes use fixed seeds; outputs are deterministic.
"""
import json, os, math, random, statistics as st, hashlib
from collections import defaultdict
from itertools import combinations

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
ANALYSES = os.path.join(BASE, "analyses")

def betacf(a, b, x, itmax=200, eps=3e-12):
    qab = a + b; qap = a + 1.0; qam = a - 1.0
    c = 1.0; d = 1.0 - qab * x / qap
    if abs(d) < 1e-30: d = 1e-30
    d = 1.0 / d; h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30: d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30: c = 1e-30
        d = 1.0 / d; h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30: d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30: c = 1e-30
        d = 1.0 / d; delt = d * c; h *= delt
        if abs(delt - 1.0) < eps: break
    return h

def betai(a, b, x):
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    lnbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    bt = math.exp(lnbt)
    if x < (a + 1.0) / (a + b + 2.0): return bt * betacf(a, b, x) / a
    return 1.0 - bt * betacf(b, a, 1.0 - x) / b

def f_pvalue(F, df1, df2):
    if F is None or df2 <= 0: return None
    return betai(df2 / 2.0, df1 / 2.0, df2 / (df2 + df1 * F))

def anova2(rows, fa, fb, n_per=15):
    cells = defaultdict(list)
    for r in rows: cells[(r[fa], r[fb])].append(r["y"])
    sub = []
    for (a, b), v in cells.items():
        for y in v[:n_per]: sub.append({fa: a, fb: b, "y": y})
    rows = sub
    n = len(rows); grand = sum(r["y"] for r in rows) / n
    Ia = sorted(set(r[fa] for r in rows)); Ib = sorted(set(r[fb] for r in rows))
    cells = defaultdict(list)
    for r in rows: cells[(r[fa], r[fb])].append(r["y"])
    ssa = ssb = ssab = ssw = 0.0
    for a in Ia:
        va = [r["y"] for r in rows if r[fa] == a]; ssa += len(va) * (sum(va) / len(va) - grand) ** 2
    for b in Ib:
        vb = [r["y"] for r in rows if r[fb] == b]; ssb += len(vb) * (sum(vb) / len(vb) - grand) ** 2
    for (a, b), v in cells.items():
        cm = sum(v) / len(v)
        am = sum(r["y"] for r in rows if r[fa] == a) / sum(1 for r in rows if r[fa] == a)
        bm = sum(r["y"] for r in rows if r[fb] == b) / sum(1 for r in rows if r[fb] == b)
        ssab += len(v) * (cm - am - bm + grand) ** 2
        ssw += sum((y - cm) ** 2 for y in v)
    dfa = len(Ia) - 1; dfb = len(Ib) - 1; dfab = (len(Ia) - 1) * (len(Ib) - 1); dfw = n - len(Ia) * len(Ib)
    def Fp(ss, df):
        if df <= 0 or dfw <= 0 or ssw == 0: return None, None
        F = (ss / df) / (ssw / dfw); return F, f_pvalue(F, df, dfw)
    Fa, pa = Fp(ssa, dfa); Fb, pb = Fp(ssb, dfb); Fab, pab = Fp(ssab, dfab)
    return {"F_a": round(Fa, 3) if Fa else None, "p_a": round(pa, 4) if pa else None,
            "F_b": round(Fb, 3) if Fb else None, "p_b": round(pb, 4) if pb else None,
            "F_ab": round(Fab, 3) if Fab else None, "p_ab": round(pab, 4) if pab else None, "n": n}

def pearson(a, b):
    n = len(a); ma = sum(a) / n; mb = sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = sum((x - ma) ** 2 for x in a); vb = sum((y - mb) ** 2 for y in b)
    return cov / math.sqrt(va * vb) if va > 0 and vb > 0 else float("nan")

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest().upper()

F10 = r"<ARCHIVE_ROOT>\PAPER1_CONSOLIDATED\joint_full_F_v10_results.json"
CELLS = r"<ARCHIVE_ROOT>\PAPER5_CONSOLIDATED\outputs\recomputed_cell_means_FIXED.json"
INPUTS = {
    "joint_F_v10": F10,
    "p5_cells": CELLS,
    "e4_n15": r"<ARCHIVE_ROOT>\experiments\e4_n15_results.json",
    "ece_calibration": r"<ARCHIVE_ROOT>\experiments\ece_calibration.json",
    "mm_multi": r"<ARCHIVE_ROOT>\experiments\mm_epc_multi_seed_final.json",
    "mm_multi_ds": r"<ARCHIVE_ROOT>\experiments\mm_epc_multi_seed_ds_final.json",
    "mm_ablation_max": r"<ARCHIVE_ROOT>\experiments\mm_epc_ablation_max.json",
    "mm_qwen37": r"<ARCHIVE_ROOT>\experiments\mm_epc_qwen37_final.json",
    "gamma_jsd": r"<ARCHIVE_ROOT>\experiments\gamma_jsd_correlation.json",
    "within_condition": r"<ARCHIVE_ROOT>\tmlr_p13\within_condition_results.json",
    "canonical_v5": r"<ARCHIVE_ROOT>\CALIBRATION_EFFECTS\canonical_results_v5.json",
    "p5_protocol_run": r"<ARCHIVE_ROOT>\PAPER5_CONSOLIDATED\outputs\protocol_run.jsonl",
    "p5_protocol_summary": r"<ARCHIVE_ROOT>\PAPER5_CONSOLIDATED\outputs\protocol_run_summary.json",
    "p5_meta3": r"<ARCHIVE_ROOT>\PAPER5_CONSOLIDATED\outputs\meta_analysis_three_rounds.csv",
    "p5_meta_trend": r"<ARCHIVE_ROOT>\PAPER5_CONSOLIDATED\outputs\meta_analysis_trend.csv",
    "p5_theta": r"<ARCHIVE_ROOT>\PAPER5_CONSOLIDATED\outputs\theta_sweep_summary.json",
    "p5_judge": r"<ARCHIVE_ROOT>\PAPER5_CONSOLIDATED\outputs\external_judge_summary.json",
}
for k, v in INPUTS.items():
    assert os.path.exists(v), f"missing input {k}: {v}"

f10 = json.load(open(F10, encoding="utf-8"))
sess = [{"task": s["task_id"], "seed": int(s["seed"]), "alpha": float(s["alpha_eval"]),
         "T": int(s["T"]), "y": float(s["final_ECE"])} for s in f10["sessions"]]
sess = [s for s in sess if s["T"] in (10, 20)]
tasks = sorted(set(s["task"] for s in sess))
loo = []
for held in tasks:
    sub = [s for s in sess if s["task"] != held]
    a = anova2(sub, "alpha", "T", n_per=15)
    m_a0_t20 = st.mean([s["y"] for s in sub if s["alpha"] == 0.0 and s["T"] == 20])
    m_a1_t20 = st.mean([s["y"] for s in sub if s["alpha"] == 1.0 and s["T"] == 20])
    m_a0_t10 = st.mean([s["y"] for s in sub if s["alpha"] == 0.0 and s["T"] == 10])
    loo.append({
        "held_out_task": held, "n_sessions": len(sub),
        "F_alpha": a["F_a"], "p_alpha": a["p_a"], "F_T": a["F_b"], "p_T": a["p_b"],
        "dir_alpha_T20": "increase" if m_a1_t20 > m_a0_t20 else ("decrease" if m_a1_t20 < m_a0_t20 else "flat"),
        "delta_alpha_T20": round(m_a1_t20 - m_a0_t20, 4),
        "dir_T_alpha0": "increase" if m_a0_t20 > m_a0_t10 else ("decrease" if m_a0_t20 < m_a0_t10 else "flat"),
        "delta_T_alpha0": round(m_a0_t20 - m_a0_t10, 4)})
P13 = {"held_out_results": loo,
       "provenance": {"inputs": [F10], "command": "python scripts/analyze_heldout_20260806.py"},
       "note": ("In-archive leave-one-task cross-validation on the joint F_v10 experiment (T in {10,20}). "
                "The archive contains completed sessions for 4 of the 5 planned tasks (metadata: n_tasks=5, planned=150, completed=125; "
                "the fifth task has no completed sessions), so only 4 folds are computable. "
                "Direction uses cell means of final_ECE; balanced-cell two-way ANOVA uses up to 15 sessions per cell and may be "
                "degenerate when a cell loses all distinct values after dropping a task (fact_2 fold).")}

rows5 = [
    {"cond": "DS Self-Eval", "gamma": 0.033, "H": 0.999, "CV5": 2.42},
    {"cond": "DS x Qwen", "gamma": 0.187, "H": 0.988, "CV5": 1.025},
    {"cond": "Qwen x DS", "gamma": 0.766, "H": 0.931, "CV5": 0.157},
    {"cond": "Ablation mid", "gamma": 0.560, "H": 0.954, "CV5": 0.184},
    {"cond": "Ablation max", "gamma": 1.038, "H": 0.913, "CV5": 0.157},
]
g = [r["gamma"] for r in rows5]; h = [r["H"] for r in rows5]
r_full = pearson(g, h)
loo2 = []
for i, r in enumerate(rows5):
    g2 = [x["gamma"] for j, x in enumerate(rows5) if j != i]
    h2 = [x["H"] for j, x in enumerate(rows5) if j != i]
    loo2.append({"dropped": r["cond"], "r_without": round(pearson(g2, h2), 4)})
rng = random.Random(5)
perm = []
for _ in range(10000):
    hh = h[:]; rng.shuffle(hh)
    perm.append(pearson(g, hh))
perm.sort()
P2 = {"full_r_gamma_H": round(r_full, 4), "loo": loo2,
      "permutation_95ci": [round(perm[250], 4), round(perm[9750], 4)],
      "provenance": {"inputs": ["main.tex Table 2 (5-row empirical table)"],
                     "command": "python scripts/analyze_heldout_20260806.py"},
      "note": "n=5 rows; leave-one-condition-out and permutation CI reported descriptively (manuscript already notes the n=5 sensitivity)."}

d = json.load(open(CELLS, encoding="utf-8"))
ARCHES = ["Append-Only", "RAG+Filter", "Summarization"]
def parse(k):
    model = "deepseek-v4-pro" if k.startswith("deepseek-v4-pro") else "qwen3.7-plus"
    rest = k[len(model) + 1:]
    for a in ARCHES:
        if rest.startswith(a):
            return model, a, rest[len(a) + 1:].rsplit("-", 1)[0]
    raise ValueError(k)
qwen_len = {k: v["gammas"] for k, v in d.items() if parse(k)[0] == "qwen3.7-plus" and parse(k)[2] == "length"}
gA, gR = qwen_len["qwen3.7-plus-Append-Only-length-p0.8"], qwen_len["qwen3.7-plus-RAG+Filter-length-p0.8"]
n10_order = "RAG>Append" if st.mean(gR) > st.mean(gA) else "Append>RAG"
rev = 0; total = 0
for idx in combinations(range(10), 3):
    mA = sum(gA[i] for i in idx) / 3; mR = sum(gR[i] for i in idx) / 3
    total += 1
    if (mA > mR) != (n10_order == "RAG>Append"):
        rev += 1
P4 = {
  "n10_means": {"Append": round(st.mean(gA), 4), "RAG": round(st.mean(gR), 4), "n10_order": n10_order},
  "n3_first3_means": {"Append": round(st.mean(gA[:3]), 4), "RAG": round(st.mean(gR[:3]), 4)},
  "reported_n3_order": "Append>RAG",
  "reversal_fraction_over_all_120_3subsets": round(rev / total, 4),
  "fraction_reproducing_n3_order": round(1 - rev / total, 4),
  "fraction_giving_reversed_order": round(rev / total, 4),
  "decision": ("Criterion (i) satisfied (ordering flips between n=3 and n=10); of the 120 three-seed subsets, only 34.2% reproduce the n=3 "
               "Append>RAG ordering and 65.8% give the reversed RAG>Append ordering, i.e., the reversal is majority-supported at n=3 but "
               "the 65.8% reproduction rate of the reversed ordering does not meet the 0.8 replication threshold of criterion (iv); "
               "under the full rule the comparison is borderline and should be reported with its reversal probability."),
  "provenance": {"inputs": [CELLS], "command": "python scripts/analyze_heldout_20260806.py"},
  "note": ("Prospective-style application of the frozen decision rule to existing data: the Qwen length ordering flips between "
           "n=3 (Append>RAG) and n=10 (RAG>Append); 34.2% of the 120 three-seed subsets reproduce the n=3 Append>RAG ordering and "
           "65.8% give the reversed RAG>Append ordering (reversal reproduction rate 0.658 < 0.8), so criterion (iv) is not met and "
           "the comparison is borderline.")}

cells = []
for k, v in d.items():
    m, a, b = parse(k)
    cells.append({"cell": k, "model": m, "arch": a, "bias": b, "n": v["n"],
                  "mean": round(v["mean"], 4), "sd": round(st.stdev(v["gammas"]), 4)})
P5 = {"cells": cells,
      "provenance": {"inputs": [CELLS], "command": "python scripts/analyze_heldout_20260806.py"},
      "note": ("Machine-readable per-cell table at p=0.8 only: 12 cells = 2 models x 3 architectures x 2 bias types. "
               "The full 36-cell grid (x 3 contamination rates) is not persisted for deepseek-v4-pro; only deepseek-chat "
               "dose-response means (n=10, rates 0.2/0.5/0.8) exist in outputs/meta_analysis_three_rounds.csv. "
               "Pairwise family audit (BH) is in p5_robustness.json.")}

ledger = {
 "PAPER1": [
  {"headline": "C5 real-image DeltaCAF = -0.107", "value": "-0.107", "source": "source-study artifact (not in local archive)", "seeds": "n/a", "estimator": "CAF sync-nosync", "tier": "Primary empirical", "status": "needs source traces"},
  {"headline": "temporal contrast +0.207 / sync +0.021", "value": "+0.207 / +0.021", "source": "source-study 8-condition design (not in local archive)", "seeds": "30 per condition", "estimator": "matched ECE contrast", "tier": "Primary", "status": "needs source traces"},
  {"headline": "joint experiment F=8.16, p=0.0006", "value": "F=8.16, p=0.0006", "source": "joint_full_F_v10_results.json", "seeds": "4-5 tasks x 5 seeds x 6 cells (125 sessions)", "estimator": "two-way ANOVA ECE", "tier": "Pattern-level", "status": "RECOMPUTED: F_a=6.61 p=0.0022 (balanced 15/cell); pairwise family null after Holm/BH"},
  {"headline": "ECE-Brier consistency", "value": "r=0.986", "source": "experiments/ece_calibration.json", "seeds": "10", "estimator": "Pearson", "tier": "Estimator check", "status": "RECOMPUTED"},
 ],
 "PAPER2": [
  {"headline": "5-row empirical table (gamma, H, CV(N=5))", "value": "rows in main.tex", "source": "main.tex Table 2 + experiments/mm_epc_*.json", "seeds": "5-30", "estimator": "normalized distance proxy", "tier": "Empirical", "status": "RECOMPUTED CV subset ranges; gamma-JSD Spearman 0.998"},
  {"headline": "empty region {gamma<0.2, CV<0.3}", "value": "empty in 5 rows", "source": "main.tex Table 2", "seeds": "5", "estimator": "threshold grid", "tier": "Descriptive", "status": "threshold-robust within 5 rows; 6 rows missing"},
  {"headline": "Chatbot Arena r(H,dec)=-0.895", "value": "-0.895", "source": "external public data", "seeds": "20 models", "estimator": "Pearson", "tier": "External association", "status": "not re-run locally"},
 ],
 "PAPER3": [
  {"headline": "temporal +0.207 / sync +0.021 / 90.8%", "value": "+0.207/+0.021/90.8%", "source": "source-study 8-condition design", "seeds": "30 per condition", "estimator": "matched ECE contrast", "tier": "Primary", "status": "needs source traces; joint-experiment SS check: T 2.8% / alpha 12.6%"},
  {"headline": "self-eval gamma=1.064 [0.76,1.41] (5 seeds)", "value": "1.064", "source": "experiments/e4_n15_results.json", "seeds": "first 5 of 15", "estimator": "gamma_TV mean", "tier": "Exploratory", "status": "REPLACED by 15-seed: 0.991 [0.907,1.085]"},
  {"headline": "calibrated reduction -42%", "value": "-42%", "source": "experiments/e4_n15_results.json", "seeds": "15", "estimator": "paired gamma", "tier": "Exploratory", "status": "REPLACED by -37% (15-seed archive)"},
 ],
 "PAPER4": [
  {"headline": "Case1 +0.207/+0.021 reversal", "value": "+0.207/+0.021", "source": "source-study", "seeds": "30", "estimator": "deconfounded contrasts", "tier": "Case study", "status": "needs source traces"},
  {"headline": "Case2 Qwen gamma 0.77 vs 1.38 (LR mode)", "value": "0.77/1.38", "source": "source-study", "seeds": "5", "estimator": "gamma by LR mode", "tier": "Case study", "status": "sign-flip prob 49.6-84.3% at N=5 subsampling"},
  {"headline": "minimal simulation figure", "value": "CV=0.9, gamma=0.35", "source": "main.tex + tmlr_p13/within_condition_results.json", "seeds": "200", "estimator": "simulation", "tier": "Illustration", "status": "CV ranking stable N=5 vs N=30 (Spearman=1.0)"},
 ],
 "PAPER5": [
  {"headline": "DeepSeek authority p=0.8 (k=3)", "value": "0.822/0.818/0.661", "source": "paper5_round3_live_logs_20260713 (Round-3)", "seeds": "10/cell", "estimator": "gamma_per_file (clean-normalized W1)", "tier": "Descriptive", "status": "RECOMPUTED in Revision 4; no contrast survives BH (smallest raw p=0.340)"},
  {"headline": "Qwen length n=10", "value": "0.627/0.530/0.752", "source": "recomputed_cell_means_FIXED.json + Round-3 logs", "seeds": "10/cell", "estimator": "gamma_per_file", "tier": "Descriptive", "status": "n=10 formalized in Revision 4; n3/n10 Kendall=0.33 (ordering flip)"},
  {"headline": "Qwen authority n=10", "value": "0.802/0.544/0.818", "source": "recomputed_cell_means_FIXED.json + Round-3 logs", "seeds": "10/cell", "estimator": "gamma_per_file", "tier": "Descriptive", "status": "n=10 formalized; Kendall=1.0 stable"},
  {"headline": "dose-response slopes (deepseek-chat)", "value": "-0.257/-0.096/-0.366", "source": "outputs/meta_analysis_trend.csv", "seeds": "10", "estimator": "slope", "tier": "Sensitivity", "status": "existing evidence; deepseek-v4-pro 0.2/0.5 per-seed not persisted"},
  {"headline": "discriminant validity (verbosity)", "value": "cell-dependent r", "source": "Round-3 response_text", "seeds": "10", "estimator": "seed-level correlation", "tier": "Construct check", "status": "DS cells negative (-0.51..-0.08), Qwen positive (up to 0.88); incomplete"},
 ],
}
for paper_rows in ledger.values():
    for r in paper_rows:
        r["provenance"] = "see analyses/input_manifest_20260806.json and analyses/evidence_ledger_20260806.md"

manifest = {}
for k, path in INPUTS.items():
    manifest[k] = {"path": path, "sha256": sha256(path), "size": os.path.getsize(path)}
REV3 = r"<WORKSPACE>\thread-groups\default\outputs\Five_Papers_MultiReview_Revision3_2026-08-06"
for p in ["PAPER1", "PAPER2", "PAPER3", "PAPER4", "PAPER5"]:
    tex = os.path.join(REV3, p, "source", "main.tex")
    pdf = os.path.join(REV3, p, "main.pdf")
    manifest[f"{p}_main_tex"] = {"path": tex, "sha256": sha256(tex), "size": os.path.getsize(tex)}
    manifest[f"{p}_main_pdf"] = {"path": pdf, "sha256": sha256(pdf), "size": os.path.getsize(pdf)}

os.makedirs(ANALYSES, exist_ok=True)
out = {"evidence_ledger": ledger, "heldout_validations": {
    "P1P3_leave_one_task_out_F_v10": P13,
    "P2_leave_one_condition_out": P2,
    "P4_decision_rule_Qwen_n3_vs_n10": P4,
    "P5_p08_archive_cells": P5,
}}
json.dump(out, open(os.path.join(ANALYSES, "heldout_validations_20260806.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(ledger, open(os.path.join(ANALYSES, "evidence_ledger_20260806.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(manifest, open(os.path.join(ANALYSES, "input_manifest_20260806.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

md = [
 "# 内部交叉验证与 9 分门槛证据（in-archive cross-validation）— 2026-08-06",
 "",
 "**术语说明**：本文件中的留一任务/留一条件/判定规则应用均为**同一归档内部的交叉验证**，不是外部 held-out；",
 "外部 held-out 与独立验证仍属 Class C（见 class_c_preregistrations_20260806.md）。",
 "数据源全部为本地已有归档；未运行任何新 API 实验。生成命令：`python scripts/analyze_heldout_20260806.py`。",
 "",
 "## 1. PAPER1/PAPER3 联合实验：留一任务内部交叉验证（F_v10）",
 "- 归档实际完成会话 125/150 格，含 4 个任务（fact_2/logic_1/math_5/opinion_3）；第 5 个计划任务无完成会话，故只有 4 折。",
 "",
 "| Held-out 任务 | α 效应方向 @T=20 | ΔECE(α1−α0) | T 效应方向 @α=0 | 备注 |",
 "|---|---|---|---|---|",
 "| fact_2 | 持平 (null) | 0.0000 | 持平 | 平衡格退化，ANOVA 不可算 |",
 "| logic_1 | 增加 | +0.1375 | 下降 | p_α=0.535 |",
 "| math_5 | 增加 | +0.1000 | 下降 | p_α=0.368 |",
 "| opinion_3 | 增加 | +0.0542 | 下降 | p_α=0.002 |",
 "",
 "- **结论**：α→ECE 方向 3/4 折一致（增加），1 折持平；T→ECE 方向全部非正——联合实验不能复现源研究的时间轴正向效应（与 SS 分解 T 轴仅 2.8% 一致），只支持「模式级证据」定位。",
 "",
 "## 2. PAPER2：留一条件相关（5 行表，γ vs H）",
 "- 全表 r = -0.9977（论文报告 -0.989，差异来自表格舍入）；留一范围 [-0.9997, -0.9963]；置换 95% CI [-0.916, 0.890]（n=5，区间极宽）。",
 "- 结论：方向稳健但 n=5 证据强度有限，正文已如实标注描述性。",
 "",
 "## 3. PAPER4：判定规则在既有数据上的前瞻式应用（Qwen length p=0.8）",
 "- n=10 全归档：Append 0.6269 < RAG 0.7524（RAG>Append）；n=3（前 3 种子）：Append 0.7768 > RAG 0.7693——排序翻转。",
 "- 全部 120 个 3-种子子集：仅 34.2% 复现 n3 的 Append>RAG 排序，65.8% 为反转（RAG>Append）；判据 (i) 满足、(iv) 未达 0.8 → 边界情形，应报告反转概率。",
 "",
 "## 4. PAPER5：p=0.8 归档逐格表（12 格 = 2 models × 3 arch × 2 bias）",
 "- 机器可读表见 `heldout_validations_20260806.json` → `P5_p08_archive_cells`；族级 BH 审计见 `p5_robustness.json`。",
 "- 完整 36 格（×3 污染率）未持久化：deepseek-v4-pro 仅 p=0.8；deepseek-chat 剂量-反应均值（n=10）在 meta_analysis_three_rounds.csv。",
 "",
 "## 5. 输入文件哈希",
 "- 全部关键输入与交付件的 SHA-256 见 `input_manifest_20260806.json`；账本每行数据的来源映射见 `evidence_ledger_20260806.md`。",
]
open(os.path.join(ANALYSES, "heldout_summary_20260806.md"), "w", encoding="utf-8").write("\n".join(md))

md2 = ["# 五篇论文头条数字证据账本 — 2026-08-06", "",
       "每条：头条数字 → 数据源 → 种子 → 估计器 → 证据层级 → 状态（RECOMPUTED=本地重算一致/已修正；needs source traces=需源研究原始轨迹）。",
       "输入文件哈希见 `input_manifest_20260806.json`；生成命令：`python scripts/analyze_heldout_20260806.py`。", ""]
for p, rows in ledger.items():
    md2.append(f"## {p}")
    md2.append("| 头条数字 | 值 | 数据源 | 种子 | 估计器 | 层级 | 状态 |")
    md2.append("|---|---|---|---|---|---|---|")
    for r in rows:
        md2.append(f"| {r['headline']} | {r['value']} | {r['source']} | {r['seeds']} | {r['estimator']} | {r['tier']} | {r['status']} |")
    md2.append("")
open(os.path.join(ANALYSES, "evidence_ledger_20260806.md"), "w", encoding="utf-8").write("\n".join(md2))
print("regenerated all outputs")
