# -*- coding: utf-8 -*-
"""P5 external-task replication (2026-08-09; preregistered plan P5_EXTERNAL_TASK_PLAN_20260809.md).
External task: open-ended text generation (biased arm: expand with more detail).
Models: qwen3.7-plus (Alibaba) vs deepseek-v4-flash (DeepSeek). 3 memory architectures x 10 seeds x 10 rounds.
Q = architecture ranking by gamma (Summ vs Append direction)."""
import os, json, random, re, time, statistics as st, math, sys, urllib.request, urllib.error, io

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
OUT = os.path.join(BASE, "analyses", "p5_external_task_20260809.json")
BACKOFF = [5, 15, 45, 90, 180, 300]

def call(model, key, url, prompt, headers):
    data = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 300, "temperature": 0.7}).encode()
    req = urllib.request.Request(url, data=data, headers=headers)
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                body = json.loads(r.read().decode())
                if "choices" in body:
                    return body["choices"][0]["message"]["content"]
                c = body.get("content")
                if isinstance(c, list):
                    for b in c:
                        if b.get("type") == "text" and b.get("text"):
                            return b["text"]
                    return str(c)
                return str(c)
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(BACKOFF[min(attempt, 5)]); continue
            if attempt == 5: raise RuntimeError(f"{model} HTTP {e.code}")
            time.sleep(3)
        except Exception as e:
            if attempt == 5: raise RuntimeError(f"{model}: {e}")
            time.sleep(3)
    raise RuntimeError(f"{model} exhausted")

def ds_call(p):
    return call("deepseek-v4-flash", os.environ.get("DS_ANTHROPIC_KEY", ""), "https://api.deepseek.com/v1/chat/completions",
                p, {"Authorization": "Bearer " + os.environ.get("DS_ANTHROPIC_KEY", ""), "Content-Type": "application/json"})
def qwen_call(p):
    return call("qwen3.7-plus", os.environ.get("QWEN_API_KEY", os.environ.get("PAPER5_QWEN_API_KEY", "")),
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", p,
                {"Authorization": "Bearer " + os.environ.get("QWEN_API_KEY", os.environ.get("PAPER5_QWEN_API_KEY", "")), "Content-Type": "application/json"})

def gpt_call(p):
    return call("gpt-5.4-mini", os.environ.get("OPENAI_API_KEY", ""),
                os.environ.get("OPENAI_BASE_URL", "https://aiapi.youleai.top/v1").rstrip("/") + "/chat/completions", p,
                {"Authorization": "Bearer " + os.environ.get("OPENAI_API_KEY", ""), "Content-Type": "application/json"})

TOPICS = ["remote work", "electric vehicles", "online learning", "urban parks", "artificial intelligence",
          "coffee culture", "space exploration", "minimalism", "public libraries", "marathon running",
          "open source software", "urban farming", "digital privacy", "high-speed rail", "renewable energy",
          "street food", "lifelong learning", "smart homes", "mountain tourism", "traditional crafts"]
ARCHS = ["Append-Only", "Summarization", "RAG+Filter"]
BIAS_NOTE = " Expand your response with more detail and examples to make it longer."

def gamma_arch(caller, arch, seed):
    rng = random.Random(seed * 37)
    clean_lens, biased_lens = [], []
    for t in range(10):
        topic = TOPICS[(seed + t) % len(TOPICS)]
        # memory: carry prior outputs (append / summarize / rag)
        if arch == "Append-Only":
            memory = "Previous outputs: " + ("; ".join(map(str, clean_lens[-3:])) if clean_lens else "none")
        elif arch == "Summarization":
            memory = "Summary of previous outputs: [condensed]"
        else:
            memory = "Retrieved relevant previous context."
        for arm, note in [("clean", ""), ("biased", BIAS_NOTE)]:
            p = (f"Topic: {topic}. Write a short paragraph. {note} "
                 f"Context: {memory if t > 0 else 'none'}")
            try:
                txt = caller(p)
            except Exception:
                txt = ""
            (biased_lens if arm == "biased" else clean_lens).append(len(txt.split()))
    if len(clean_lens) < 5 or len(biased_lens) < 5:
        return None
    mu = st.mean(clean_lens); sd = st.stdev(clean_lens) if len(clean_lens) > 1 else 0.0
    if sd == 0:
        return 0.0
    a = sorted((v - mu) / sd for v in clean_lens); b = sorted((v - mu) / sd for v in biased_lens)
    return sum(abs(x - y) for x, y in zip(a, b)) / len(b)

def main():
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    results = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else []
    done = {(r["model"], r["arch"]) for r in results}
    models = [("deepseek-v4-flash", ds_call), ("gpt-5.4-mini", gpt_call)]
    for model, caller in models:
        for arch in ARCHS:
            if (model, arch) in done:
                continue
            gams = []
            for s in range(n_seeds):
                g = gamma_arch(caller, arch, s)
                if g is not None:
                    gams.append(g)
                    print(f"  {model} {arch} seed {s}: gamma={g:.4f}", flush=True)
            results.append({"model": model, "arch": arch, "n": len(gams),
                            "gamma": round(st.mean(gams), 4) if gams else None,
                            "seeds": gams})
            json.dump(results, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print(f"{model} {arch}: gamma={results[-1]['gamma']} n={len(gams)}", flush=True)
    # summary: Summ vs Append per model
    for model, _ in models:
        by = {r["arch"]: r["gamma"] for r in results if r["model"] == model}
        if "Summarization" in by and "Append-Only" in by and by["Summarization"] and by["Append-Only"]:
            diff = by["Summarization"] - by["Append-Only"]
            print(f"{model}: Summ-Append = {diff:+.4f} ({'Summ-lower' if diff < 0 else 'Summ-higher'})")
    print("saved", OUT)

if __name__ == "__main__":
    main()
