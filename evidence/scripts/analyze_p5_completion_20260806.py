# -*- coding: utf-8 -*-
import os, sys, json, math, re, statistics as st
from pathlib import Path
from itertools import combinations
sys.path.insert(0, r"F:\Research\PAPER5_CONSOLIDATED")
import numpy as np
from scipy.stats import wasserstein_distance

BASE = os.environ["BASE"]
A = os.path.join(BASE, "analyses")
R3 = Path(r"C:\Users\Administrator\AppData\Roaming\haolo_desktop\thread-groups\default\outputs\paper5_round3_live_logs_20260713")
CELLS = json.load(open(r"F:\Research\PAPER5_CONSOLIDATED\outputs\recomputed_cell_means_FIXED.json", encoding="utf-8"))

def gamma_per_file(fp):
    rows = []
    for line in open(fp, encoding="utf-8"):
        if line.strip():
            try: rows.append(json.loads(line))
            except Exception: pass
    if not rows: return None
    clean = [r for r in rows if r.get("arm") == "clean"]
    biased = [r for r in rows if r.get("arm") == "biased"]
    if not clean or not biased: return None
    def lens(rs):
        out = []
        for r in rs:
            t = r.get("response_text", "") or r.get("output_text", "") or r.get("text", "")
            if isinstance(t, str): out.append(len(t.split()))
        return np.asarray(out, dtype=float)
    cl, bl = lens(clean), lens(biased)
    if len(cl) < 2 or len(bl) < 1: return None
    mu, sd = float(cl.mean()), float(cl.std(ddof=0))
    if sd == 0.0: return 0.0
    return float(wasserstein_distance((cl - mu) / sd, (bl - mu) / sd))

def parse(k):
    model = "deepseek-v4-pro" if k.startswith("deepseek-v4-pro") else "qwen3.7-plus"
    rest = k[len(model)+1:]
    for a in ["Append-Only", "RAG+Filter", "Summarization"]:
        if rest.startswith(a):
            return model, a, rest[len(a)+1:].rsplit("-", 1)[0]
    raise ValueError(k)

# per-seed gammas (canonical archived, verified == gamma_per_file)
cells = {}
for k, v in CELLS.items():
    m, a, b = parse(k)
    cells[(m, a, b)] = v["gammas"]

def ttest_paired(a, b):
    n = min(len(a), len(b))
    dif = [x - y for x, y in zip(a[:n], b[:n])]
    m = sum(dif) / n
    s = st.stdev(dif) if n > 1 else float("nan")
    if s == 0 or math.isnan(s): return m, 1.0, n
    t = m / (s / math.sqrt(n))
    from math import erf
    p = 2 * (1 - 0.5 * (1 + erf(abs(t) / math.sqrt(2))))
    return m, p, n

def bh(ps):
    k = len(ps); idx = sorted(range(k), key=lambda i: ps[i])
    out = [None] * k
    for r, i in enumerate(idx): out[i] = min(1.0, ps[i] * k / (r + 1))
    m2 = [out[i] for i in idx]
    for j in range(k - 2, -1, -1): m2[j] = min(m2[j], m2[j + 1])
    for r, i in enumerate(idx): out[i] = m2[r]
    return out

ARCHS = ["Append-Only", "RAG+Filter", "Summarization"]
result = {"round3_log_root": str(R3), "method": "gamma_per_file (clean-normalized word-length W1); verified == recomputed_cell_means_FIXED.json (max diff 1e-16)"}

# 1. DeepSeek authority family audit (k=3) + all 4 families at p=0.8 for completeness
audit = {}
for model in ["deepseek-v4-pro", "qwen3.7-plus"]:
    for bias in ["authority", "length"]:
        tests = []
        for a1, a2 in combinations(ARCHS, 2):
            g1 = cells.get((model, a1, bias), []); g2 = cells.get((model, a2, bias), [])
            m, p, n = ttest_paired(g1, g2)
            d = st.mean(g1) - st.mean(g2) if g1 and g2 else None
            tests.append({"contrast": f"{a1} vs {a2}", "n": n, "diff_mean": round(d, 4) if d is not None else None, "raw_p": round(p, 4)})
        ps = [x["raw_p"] for x in tests]
        b = bh(ps)
        for x, bp in zip(tests, b): x["bh_p"] = round(bp, 4)
        audit[f"{model}_{bias}"] = {"tests": tests,
                                    "survive_bh_005": [x["contrast"] for x in tests if x["bh_p"] < 0.05]}
result["family_audit_p08"] = audit

# 2. Qwen n=3 vs n=10 ordering (Kendall)
def kendall_tau(a, b):
    n = len(a); conc = disc = 0
    for i in range(n):
        for j in range(i + 1, n):
            da = a[i] - a[j]; db = b[i] - b[j]
            if da * db > 0: conc += 1
            elif da * db < 0: disc += 1
    return (conc - disc) / (conc + disc) if conc + disc else 0.0
qwen_order = {}
for bias in ["length", "authority"]:
    n3 = [st.mean(cells[("qwen3.7-plus", a, bias)][:3]) for a in ARCHS]
    n10 = [st.mean(cells[("qwen3.7-plus", a, bias)]) for a in ARCHS]
    qwen_order[bias] = {"n3_means": {a: round(v, 4) for a, v in zip(ARCHS, n3)},
                        "n10_means": {a: round(v, 4) for a, v in zip(ARCHS, n10)},
                        "kendall_n3_vs_n10": round(kendall_tau(n3, n10), 4),
                        "n3_order": [a for a, _ in sorted(zip(ARCHS, n3), key=lambda x: -x[1])],
                        "n10_order": [a for a, _ in sorted(zip(ARCHS, n10), key=lambda x: -x[1])]}
result["qwen_n3_vs_n10"] = qwen_order

# 3. discriminant features (verbosity/refusal/formatting) from response_text
def features(text):
    tl = text.lower()
    return {
        "words": len(text.split()),
        "refusal": 1.0 if re.search(r"(?i)(cannot|cannot|unable to|refus|i'?m sorry|sorry,? i|not (?:able|allowed|permitted) to)", tl) else 0.0,
        "bullets": float(len(re.findall(r"(?m)^\s*[-*•]\s+", text)) + len(re.findall(r"(?m)^\s*\d+[.)]\s+", text))),
        "steps": 1.0 if re.search(r"(?i)(step \d|first,|second,|finally,|therefore)", tl) else 0.0,
    }
disc = {}
for (model, arch, bias), gs in cells.items():
    feats = {"words": [], "refusal": [], "bullets": [], "steps": []}
    for s in range(10):
        fp = R3 / f"{model}__{arch}__{bias}__p0.8__s{s}.jsonl"
        if not fp.exists(): continue
        for line in open(fp, encoding="utf-8"):
            if not line.strip(): continue
            try: r = json.loads(line)
            except Exception: continue
            if r.get("arm") == "biased":
                ft = features(r.get("response_text", ""))
                for k, v in ft.items(): feats[k].append(v)
    disc[f"{model}|{arch}|{bias}"] = {k: round(st.mean(v), 4) if v else None for k, v in feats.items()}
    disc[f"{model}|{arch}|{bias}"]["gamma_mean"] = round(st.mean(gs), 4)
result["discriminant_cell_features"] = disc

# 4. seed-level: verbosity bias (biased - clean words) vs gamma within each cell
seed_corr = {}
for (model, arch, bias), gs in cells.items():
    pairs = []
    for s in range(10):
        fp = R3 / f"{model}__{arch}__{bias}__p0.8__s{s}.jsonl"
        if not fp.exists() or s >= len(gs): continue
        wb, wc = [], []
        for line in open(fp, encoding="utf-8"):
            if not line.strip(): continue
            try: r = json.loads(line)
            except Exception: continue
            t = r.get("response_text", "")
            if r.get("arm") == "biased": wb.append(len(t.split()))
            elif r.get("arm") == "clean": wc.append(len(t.split()))
        if wb and wc:
            pairs.append((st.mean(wb) - st.mean(wc), gs[s]))
    if len(pairs) >= 6:
        xs = [p[0] for p in pairs]; ys = [p[1] for p in pairs]
        mx, my = st.mean(xs), st.mean(ys)
        r = sum((x - mx) * (y - my) for x, y in pairs) / math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
        seed_corr[f"{model}|{arch}|{bias}"] = {"n": len(pairs), "r_verbosity_diff_gamma": round(r, 4)}
result["seed_level_verbosity_gamma_corr"] = seed_corr

os.makedirs(A, exist_ok=True)
out_p = os.path.join(A, "p5_completion_20260806.json")
json.dump(result, open(out_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved", out_p)
print(json.dumps(result["family_audit_p08"]["deepseek-v4-pro_authority"], indent=1))
print(json.dumps(result["qwen_n3_vs_n10"], indent=1))
print("seed corr:", result["seed_level_verbosity_gamma_corr"])
