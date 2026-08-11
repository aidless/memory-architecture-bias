# -*- coding: utf-8 -*-
"""PAPER5 class-A analyses: confirmatory family audit, interaction model, existing sensitivity evidence summary."""
import json, math, os, random, statistics as st
from collections import defaultdict
from itertools import combinations

OUT = r"<WORKSPACE>\thread-groups\default\科研\outputs\five_paper_acceptance_baseline_20260806\analyses"
CELLS = r"<ARCHIVE_ROOT>\PAPER5_CONSOLIDATED\outputs\recomputed_cell_means_FIXED.json"

def betacf(a,b,x,itmax=200,eps=3e-12):
    qab=a+b; qap=a+1.0; qam=a-1.0
    c=1.0; d=1.0-qab*x/qap
    if abs(d)<1e-30: d=1e-30
    d=1.0/d; h=d
    for m in range(1,itmax+1):
        m2=2*m
        aa=m*(b-m)*x/((qam+m2)*(a+m2))
        d=1.0+aa*d
        if abs(d)<1e-30: d=1e-30
        c=1.0+aa/c
        if abs(c)<1e-30: c=1e-30
        d=1.0/d; h*=d*c
        aa=-(a+m)*(qab+m)*x/((a+m2)*(qap+m2))
        d=1.0+aa*d
        if abs(d)<1e-30: d=1e-30
        c=1.0+aa/c
        if abs(c)<1e-30: c=1e-30
        d=1.0/d; delt=d*c; h*=delt
        if abs(delt-1.0)<eps: break
    return h

def betai(a,b,x):
    if x<=0: return 0.0
    if x>=1: return 1.0
    lnbt=math.lgamma(a+b)-math.lgamma(a)-math.lgamma(b)+a*math.log(x)+b*math.log1p(-x)
    bt=math.exp(lnbt)
    if x<(a+1.0)/(a+b+2.0): return bt*betacf(a,b,x)/a
    return 1.0-bt*betacf(b,a,1.0-x)/b

def f_pvalue(F, df1, df2):
    if F is None or df2<=0: return None
    return betai(df2/2.0, df1/2.0, df2/(df2+df1*F))

def t_cdf(x, df):
    if x==0: return 0.5
    ib=betai(df/2.0, 0.5, df/(df+x*x))
    return 1.0-0.5*ib if x>=0 else 0.5*ib

def ttest_paired(a,b):
    n=len(a); dif=[x-y for x,y in zip(a,b)]
    m=sum(dif)/n; s=st.stdev(dif) if n>1 else float("nan")
    if s==0 or math.isnan(s): return m, float("nan"), 1.0
    t=m/(s/math.sqrt(n)); p=2*(1-t_cdf(abs(t), n-1))
    return m, t, p

def bh(ps):
    k=len(ps); idx=sorted(range(k), key=lambda i: ps[i])
    out=[None]*k
    for r,i in enumerate(idx): out[i]=min(1.0, ps[i]*k/(r+1))
    m2=[out[i] for i in idx]
    for j in range(k-2,-1,-1): m2[j]=min(m2[j], m2[j+1])
    for r,i in enumerate(idx): out[i]=m2[r]
    return out

def holm(ps):
    k=len(ps); idx=sorted(range(k), key=lambda i: ps[i])
    out=[None]*k
    for r,i in enumerate(idx): out[i]=min(1.0, ps[i]*(k-r))
    m2=[out[i] for i in idx]
    for j in range(k-2,-1,-1): m2[j]=max(m2[j], m2[j+1])
    for r,i in enumerate(idx): out[i]=m2[r]
    return out

def anova2(rows, fa, fb):
    cells = defaultdict(list)
    for r in rows: cells[(r[fa], r[fb])].append(r["y"])
    n_per = min(len(v) for v in cells.values())
    sub=[]
    for (a,b), v in cells.items():
        for y in v[:n_per]: sub.append({fa:a, fb:b, "y":y})
    rows=sub
    n=len(rows); grand=sum(r["y"] for r in rows)/n
    Ia=sorted(set(r[fa] for r in rows)); Ib=sorted(set(r[fb] for r in rows))
    cells=defaultdict(list)
    for r in rows: cells[(r[fa],r[fb])].append(r["y"])
    ssa=ssb=ssab=ssw=0.0
    for a in Ia:
        va=[r["y"] for r in rows if r[fa]==a]; ssa+=len(va)*(sum(va)/len(va)-grand)**2
    for b in Ib:
        vb=[r["y"] for r in rows if r[fb]==b]; ssb+=len(vb)*(sum(vb)/len(vb)-grand)**2
    for (a,b),v in cells.items():
        cm=sum(v)/len(v)
        am=sum(r["y"] for r in rows if r[fa]==a)/sum(1 for r in rows if r[fa]==a)
        bm=sum(r["y"] for r in rows if r[fb]==b)/sum(1 for r in rows if r[fb]==b)
        ssab+=len(v)*(cm-am-bm+grand)**2
        ssw+=sum((y-cm)**2 for y in v)
    dfa=len(Ia)-1; dfb=len(Ib)-1; dfab=(len(Ia)-1)*(len(Ib)-1); dfw=n-len(Ia)*len(Ib)
    def Fp(ss,df):
        if df<=0 or dfw<=0 or ssw==0: return None,None
        F=(ss/df)/(ssw/dfw); return F, f_pvalue(F, df, dfw)
    Fa,pa=Fp(ssa,dfa); Fb,pb=Fp(ssb,dfb); Fab,pab=Fp(ssab,dfab)
    return {"SS_a":round(ssa,4),"SS_b":round(ssb,4),"SS_ab":round(ssab,4),"SS_w":round(ssw,4),
            "df_a":dfa,"df_b":dfb,"df_ab":dfab,"df_w":dfw,
            "F_a":round(Fa,3) if Fa else None,"p_a":round(pa,4) if pa else None,
            "F_b":round(Fb,3) if Fb else None,"p_b":round(pb,4) if pb else None,
            "F_ab":round(Fab,3) if Fab else None,"p_ab":round(pab,4) if pab else None,"n":n}

d = json.load(open(CELLS, encoding="utf-8"))
cells = {}
ARCHES = ["Append-Only", "RAG+Filter", "Summarization"]
def parse_cell_key(k):
    model = "deepseek-v4-pro" if k.startswith("deepseek-v4-pro") else "qwen3.7-plus"
    rest = k[len(model)+1:]
    for a in ARCHES:
        if rest.startswith(a):
            arch = a
            bias = rest[len(a)+1:].rsplit("-", 1)[0]
            return model, arch, bias
    raise ValueError(k)
for k, v in d.items():
    cells[parse_cell_key(k)] = v["gammas"]
models = ["deepseek-v4-pro", "qwen3.7-plus"]
arches = ["Append-Only", "RAG+Filter", "Summarization"]
biases = ["authority", "length"]

result = {"paper": "PAPER5", "date": "2026-08-06",
          "source": CELLS,
          "cells": {k: {"mean": round(v["mean"],4), "n": v["n"]} for k,v in d.items()}}

# ---------- 1. confirmatory family audit (pairwise architecture contrasts, BH/Holm) ----------
audit = {}
for model in models:
    for bias in biases:
        tests = []
        for (a1,a2) in combinations(arches, 2):
            g1, g2 = cells[(model,a1,bias)], cells[(model,a2,bias)]
            n = min(len(g1), len(g2))
            m,t,p = ttest_paired(g1[:n], g2[:n])
            tests.append({"contrast": f"{a1} vs {a2}", "n": n, "diff": round(m,4), "t": None if math.isnan(t) else round(t,3), "raw_p": round(p,4)})
        ps=[x["raw_p"] for x in tests]
        h, b = holm(ps), bh(ps)
        for x,hp,bp in zip(tests,h,b): x["holm_p"]=round(hp,4); x["bh_p"]=round(bp,4)
        audit[f"{model}_{bias}"] = {"tests": tests,
          "survive_bh_005": [x["contrast"] for x in tests if x["bh_p"]<0.05],
          "survive_holm_005": [x["contrast"] for x in tests if x["holm_p"]<0.05]}
result["family_audit"] = audit

# ---------- 2. interaction model ----------
inter = {}
for model in models:
    rows = [{"a": arch, "b": bias, "y": g} for (m,arch,bias), gs in cells.items() if m==model for g in gs]
    inter[model] = anova2(rows, "a", "b")
result["interaction_anova_per_model"] = inter
# combined rank-based permutation test: model x architecture interaction on pooled ranks
def rankall(vals):
    o = sorted(range(len(vals)), key=lambda i: vals[i])
    r = [0]*len(vals)
    for pos, i in enumerate(o): r[i] = pos+1
    return r
obs = []
for (m,arch,bias), gs in cells.items():
    for g in gs: obs.append({"model": m, "arch": arch, "bias": bias, "y": g})
# restrict qwen to first 3 seeds to balance (DS also first 3) for a fair permutation test
bal_obs = []
for (m,arch,bias), gs in cells.items():
    for g in gs[:3]: bal_obs.append({"model": m, "arch": arch, "bias": bias, "y": g})
ranks = rankall([r["y"] for r in bal_obs])
for r, rk in zip(bal_obs, ranks): r["rank"] = rk
def interaction_stat(rows):
    # sum of squared cell-mean deviations from additive model on ranks
    grand = sum(r["rank"] for r in rows)/len(rows)
    cells2 = defaultdict(list)
    for r in rows: cells2[(r["model"], r["arch"])].append(r["rank"])
    ms = defaultdict(list); as_ = defaultdict(list)
    for r in rows: ms[r["model"]].append(r["rank"]); as_[r["arch"]].append(r["rank"])
    mmean = {k: sum(v)/len(v) for k,v in ms.items()}; amean = {k: sum(v)/len(v) for k,v in as_.items()}
    stat = 0.0
    for (mm, aa), v in cells2.items():
        cm = sum(v)/len(v)
        stat += len(v)*(cm - mmean[mm] - amean[aa] + grand)**2
    return stat
obs_stat = interaction_stat(bal_obs)
rng = random.Random(11)
count = 0
B = 5000
for _ in range(B):
    perm = bal_obs[:]
    ranks_perm = rankall([r["y"] for r in perm])
    for r, rk in zip(perm, ranks_perm): r["rank"] = rk
    # permute ranks across model-arch cells preserving marginals? simpler: permute ranks among all rows
    rng.shuffle(perm)
    for r, rk in zip(perm, ranks_perm): r["rank"] = rk
    if interaction_stat(perm) >= obs_stat: count += 1
result["interaction_permutation_model_x_arch"] = {
  "design": "rank-transformed gamma, model x architecture interaction SS, B=5000 permutations, balanced 3 seeds per cell",
  "obs_stat": round(obs_stat,4), "perm_p": round(count/B,4),
  "note": "Permutation test on rank-transformed per-seed gammas: tests whether the architecture ranking differs across models (crossover)."}

# ---------- 3. existing sensitivity evidence ----------
import csv
rows_csv = list(csv.DictReader(open(r"<ARCHIVE_ROOT>\PAPER5_CONSOLIDATED\outputs\meta_analysis_three_rounds.csv", encoding="utf-8")))
dose = [r for r in rows_csv if r["round"]=="R1_dose_response" and r["note"]=="dose-response"]
trend = list(csv.DictReader(open(r"<ARCHIVE_ROOT>\PAPER5_CONSOLIDATED\outputs\meta_analysis_trend.csv", encoding="utf-8")))
theta = json.load(open(r"<ARCHIVE_ROOT>\PAPER5_CONSOLIDATED\outputs\theta_sweep_summary.json", encoding="utf-8"))
judge = json.load(open(r"<ARCHIVE_ROOT>\PAPER5_CONSOLIDATED\outputs\external_judge_summary.json", encoding="utf-8"))
result["existing_sensitivity_evidence"] = {
  "dose_response_deepseek_chat_length": [{"arch": r["arch"], "p": r["p"], "mean_gamma": round(float(r["mean"]),4), "sem": float(r["sem"])} for r in dose],
  "dose_trend_slopes": [{"arch": r["arch"], "slope": float(r["slope"]), "p_slope": ("<0.001" if float(r["p_slope"]) < 0.001 else round(float(r["p_slope"]), 4))} for r in trend],
  "theta_sweep": {"sweep_values": theta["sweep_theta"], "chosen_theta": theta["chosen_theta"], "reason": theta["chosen_theta_reason"]},
  "external_judge_authority_validation": {
    "total_judged": judge["total_judged"],
    "per_cell_delta_ece_judged": {k: round(v["delta_ece_judged"],4) for k,v in judge["per_cell"].items()},
    "max_abs_delta": round(max(abs(v["delta_ece_judged"]) for v in judge["per_cell"].values()),4),
    "note": "An external judge model assessed 120 responses for authority markers; judged-authority ECE deltas are all near zero, meaning the judge did not detect authority bias in the responses. This is relevant to construct validity but does not by itself validate or invalidate Gamma_temporal; verbosity/refusal/formatting discriminant checks require the executor response texts, which are not persisted locally (Class C)."}}

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "p5_robustness.json"), "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=1)
print(json.dumps(result["family_audit"], ensure_ascii=False, indent=1)[:2600])
print("interaction per model:", json.dumps(result["interaction_anova_per_model"], indent=1))
print("perm test:", result["interaction_permutation_model_x_arch"])
print("saved.")
