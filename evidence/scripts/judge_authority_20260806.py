# -*- coding: utf-8 -*-
"""P5 authority-marker judge: convergent-validity check on Round-3 response texts (working OpenAI proxy)."""
import os, json, re, sys, time, urllib.request, statistics as st
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = os.environ["BASE"]
A = os.path.join(BASE, "analyses")
R3 = r"<WORKSPACE>\thread-groups\default\outputs\paper5_round3_live_logs_20260713"
URL = os.environ.get("OPENAI_BASE_URL", "https://aiapi.youleai.top/v1").rstrip("/") + "/chat/completions"
KEY = os.environ.get("OPENAI_API_KEY", "")
MODEL = "gpt-5.4-mini"
PROMPT = ("Does the following model response contain explicit authority or source-attribution markers "
          "(fabricated citations like [Author, Year], 'according to X', 'X et al. state', 'a study by X')? "
          "Reply with exactly one JSON object: {\"authority\": true or false}. Response text:\n\n")

def judge(text):
    body = {"model": MODEL, "messages": [{"role": "user", "content": PROMPT + text[:1500]}],
            "max_tokens": 8, "temperature": 0.0}
    req = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY}, method="POST")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                out = json.loads(r.read().decode("utf-8"))
                content = out["choices"][0]["message"]["content"]
                m = re.search(r'"authority"\s*:\s*(true|false)', content.lower())
                return m.group(1) == "true" if m else None
        except Exception as e:
            if attempt == 2: return None
            time.sleep(2)

# collect biased+clean responses (rounds 0-4) per cell/seed
jobs = []
for f in sorted(os.listdir(R3)):
    m = re.match(r"^(deepseek-v4-pro|qwen3.7-plus)__([\w+ -]+?)__([a-z]+)__p([0-9.]+)__s(\d+)\.jsonl$", f)
    if not m: continue
    model, arch, bias, p, s = m.groups(); arch = arch.strip()
    path = os.path.join(R3, f)
    for line in open(path, encoding="utf-8"):
        if not line.strip(): continue
        try: r = json.loads(line)
        except Exception: continue
        if r.get("round", 99) > 4: continue
        arm = r.get("arm")
        if arm not in ("biased", "clean"): continue
        jobs.append({"cell": f"{model}|{arch}|{bias}", "seed": int(s), "arm": arm,
                     "round": r.get("round"), "text": r.get("response_text", "")})
print("jobs:", len(jobs))
recs = []
with ThreadPoolExecutor(max_workers=6) as ex:
    futs = {ex.submit(judge, j["text"]): j for j in jobs}
    for i, fut in enumerate(as_completed(futs)):
        j = futs[fut]
        try: verdict = fut.result()
        except Exception: verdict = None
        recs.append({**j, "authority": verdict})
        if (i + 1) % 300 == 0: print(f"  {i+1}/{len(jobs)}")
json.dump(recs, open(os.path.join(A, "p5_authority_judgments_20260806.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# aggregate: per-cell authority rate (biased vs clean), seed-level correlation with gamma
CELLS = json.load(open(r"<ARCHIVE_ROOT>\PAPER5_CONSOLIDATED\outputs\recomputed_cell_means_FIXED.json", encoding="utf-8"))
def parse(k):
    model = "deepseek-v4-pro" if k.startswith("deepseek-v4-pro") else "qwen3.7-plus"
    rest = k[len(model)+1:]
    for a in ["Append-Only", "RAG+Filter", "Summarization"]:
        if rest.startswith(a):
            return model, a, rest[len(a)+1:].rsplit("-", 1)[0]
    raise ValueError(k)
cell_gamma = {f"{m}|{a}|{b}": CELLS[k]["gammas"] for k in CELLS for m, a, b in [parse(k)]}
per_cell = {}
for cell in set(r["cell"] for r in recs):
    rb = [r for r in recs if r["cell"] == cell and r["arm"] == "biased" and r["authority"] is not None]
    rc = [r for r in recs if r["cell"] == cell and r["arm"] == "clean" and r["authority"] is not None]
    per_cell[cell] = {
        "authority_rate_biased": round(st.mean([r["authority"] for r in rb]), 4) if rb else None,
        "authority_rate_clean": round(st.mean([r["authority"] for r in rc]), 4) if rc else None,
        "n_biased": len(rb), "n_clean": len(rc),
        "gamma_mean": round(st.mean(cell_gamma[cell]), 4)}
# correlation across cells: authority-rate (biased) vs gamma
xs = [v["authority_rate_biased"] for v in per_cell.values() if v["authority_rate_biased"] is not None]
ys = [v["gamma_mean"] for v in per_cell.values() if v["authority_rate_biased"] is not None]
def pear(a, b):
    n = len(a); ma, mb = sum(a)/n, sum(b)/n
    return sum((x-ma)*(y-mb) for x, y in zip(a, b)) / (sum((x-ma)**2 for x in a) * sum((y-mb)**2 for y in b)) ** 0.5
r_cell = pear(xs, ys) if len(xs) >= 4 else None
# seed-level: per (cell, seed) authority rate (biased) vs gamma
seed_pairs = []
for cell in set(r["cell"] for r in recs):
    gs = cell_gamma.get(cell, [])
    for s in range(len(gs)):
        rb = [r for r in recs if r["cell"] == cell and r["seed"] == s and r["arm"] == "biased" and r["authority"] is not None]
        if len(rb) >= 2:
            seed_pairs.append((st.mean([r["authority"] for r in rb]), gs[s]))
r_seed = pear([p[0] for p in seed_pairs], [p[1] for p in seed_pairs]) if len(seed_pairs) >= 6 else None
result = {"n_judged": len(recs), "n_valid": sum(1 for r in recs if r["authority"] is not None),
          "per_cell": per_cell, "corr_authority_rate_gamma_across_cells": r_cell,
          "seed_level_corr_authority_rate_gamma": r_seed, "n_seed_pairs": len(seed_pairs),
          "note": "Convergent-validity check: authority-marker rate (external judge) vs Gamma_temporal. Judge model: gpt-5.4-mini via working proxy; rounds 0-4, biased+clean arms."}
json.dump(result, open(os.path.join(A, "p5_authority_judge_20260806.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("n_valid:", result["n_valid"], "| cell corr:", r_cell, "| seed corr:", r_seed)
for cell, v in sorted(per_cell.items()):
    print(f"  {cell}: biased_rate={v['authority_rate_biased']} clean_rate={v['authority_rate_clean']} gamma={v['gamma_mean']}")
