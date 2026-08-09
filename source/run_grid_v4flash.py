# -*- coding: utf-8 -*-
"""Rebuilt R3-style grid harness (protocol.md Section 4), model = deepseek-v4-flash.

Deviations recorded 2026-08-06:
  - rebuilt from protocol.md prompts + memory_architecture component logic
  - T = 10 rounds (matches archived R3 cells; protocol Face-1 specifies T=30)
  - model = deepseek-v4-flash (user model decision); Summarization memory uses the
    protocol 4.4 summarizer prompt (LLM call); RAG uses manual TF-IDF + theta=0.1.
  - bias storage: entry injected with probability p, seeded per (cell, seed, idx)
Output: outputs/grid_v4flash/{model}__{arch}__{bias}__p{rate}__s{seed}.jsonl
"""
import os, sys, json, time, hashlib, argparse, random, math, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
DS_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DS_BASE = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
DS_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
TEMPERATURE = 0.0
MAX_TOKENS = 512
SUMM_MAX_TOKENS = 256
THETA = 0.1
K = 5

FILLER_POOL = ["arguably", "broadly", "conceivably", "in essence", "in general",
               "interestingly", "it could be argued that", "it seems plausible that",
               "on the whole", "overall", "perhaps", "plausibly", "presumably",
               "put differently", "that is to say", "to some extent", "typically",
               "unlike cases where", "whereas", "while in some sense"]
CITATIONS = ["[Smith et al., 2024, ACL]", "[Johnson and Lee, 2023, NeurIPS]",
             "[Patel et al., 2025, TMLR]", "[Brown and Davis, 2022, ICML]",
             "[Garcia et al., 2024, JMLR]", "[Chen and Wang, 2023, EMNLP]",
             "[Anderson et al., 2025, ICLR]", "[Liu and Zhang, 2024, NAACL]"]

SYSTEM_PROMPT = ("You are agent {agent_id}, a careful and concise research summarizer.\n"
                 "You will read a short passage and write a 3-5 sentence summary.\n"
                 "You will also see recent outputs produced by your peer agent.\n"
                 "Use peer context to stay consistent in style and coverage, but\n"
                 "write the new summary independently. Do not copy phrases verbatim\n"
                 "from peer context unless they are exact technical terms.")

SUMMARIZER_PROMPT = ("You are a strict summarizer used for memory compression. Reduce the\n"
                     "following agent output to a single sentence that preserves factual\n"
                     "content, named entities, and any length or authority markers. Do not\n"
                     "add new information. Do not change named entities. Do not paraphrase\n"
                     "into hedged language.\n\n"
                     "Input output:\n\"\"\"\n{agent_output}\n\"\"\"\n\nCompressed sentence:")

def user_prompt(previous_round, peer_id, peer_output, passage_text):
    return ("[PEER UPDATE -- ROUND {prev}]\n"
            "Peer agent {peer} (round {prev}) wrote:\n"
            '\"\"\"\n{peer_output}\n\"\"\"\n'
            "Now summarize the new passage:\n\n{passage}\n\n"
            "Write exactly 3-5 sentences. End your reply with the literal token\n"
            "[SUMMARY_END] on its own line.").format(prev=previous_round, peer=peer_id,
                                                     peer_output=peer_output, passage=passage_text)

def _post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + DS_KEY}, method="POST")
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))["choices"][0]["message"]["content"]
        except Exception as e:
            last = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"LLM call failed: {last}")

def call_solver(system, user):
    return _post(DS_BASE + "/chat/completions",
                 {"model": DS_MODEL, "messages": [{"role": "system", "content": system},
                                                  {"role": "user", "content": user}],
                  "temperature": TEMPERATURE, "max_tokens": MAX_TOKENS})

def call_summarizer(text):
    return _post(DS_BASE + "/chat/completions",
                 {"model": DS_MODEL, "messages": [{"role": "user",
                                                   "content": SUMMARIZER_PROMPT.format(agent_output=text)}],
                  "temperature": TEMPERATURE, "max_tokens": SUMM_MAX_TOKENS})

def inject_length_bias(text, rng):
    k = 7
    fillers = rng.sample(FILLER_POOL, k)
    return " ".join(fillers) + " " + text

def inject_authority_bias(text, rng):
    return rng.choice(CITATIONS) + " " + text

def apply_bias(text, bias_type, rng):
    if bias_type == "length":
        return inject_length_bias(text, rng)
    return inject_authority_bias(text, rng)

def _tokens(text):
    return text.lower().split()

def _tfidf(entries, query):
    vocab = {}
    for e in entries:
        for w in set(_tokens(e["text"])):
            vocab.setdefault(w, len(vocab))
    n = len(entries)
    df = {w: 0 for w in vocab}
    for e in entries:
        for w in set(_tokens(e["text"])):
            df[w] += 1
    def vec(text):
        v = [0.0] * len(vocab)
        tf = _tokens(text)
        for w in tf:
            if w in vocab:
                v[vocab[w]] += 1
        for i, w in enumerate(vocab):
            if v[i] > 0:
                v[i] *= math.log((1 + n) / (1 + df[w])) + 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]
    qv = vec(query)
    scored = []
    for e in entries:
        ev = vec(e["text"])
        sim = sum(a * b for a, b in zip(qv, ev))
        scored.append((sim, e))
    scored.sort(key=lambda x: -x[0])
    top = [e for s, e in scored[:K] if s >= THETA]
    return "\n\n".join(e["text"] for e in top) if top else "No relevant memory."

def append_retrieve(entries):
    return "\n\n".join(e["text"] for e in entries[-5:]) if entries else "No prior peer output."

def summarize_retrieve(entries):
    texts = [e.get("summary") or e["text"] for e in entries[-5:]]
    return "\n\n".join(texts) if texts else "No prior peer output."

def rag_retrieve(entries, query):
    return _tfidf(entries, query)

def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def run_cell(cell, seed, passages, rounds, out_dir, code_commit, config_sha, corpus_sha):
    model, arch, bias, p = cell
    out_path = os.path.join(out_dir, f"{model}__{arch}__{bias}__p{p}__s{seed}.jsonl")
    if os.path.exists(out_path):
        return "skip"
    rng = random.Random(hashlib.sha256(f"{cell}|{seed}".encode()).digest()[:8])
    mem_a = []
    rows = []
    for t in range(rounds):
        passage = passages[t % len(passages)]["text"]
        # ---- biased agent A ----
        if t == 0:
            peer_ctx_a = "No prior peer output."
        else:
            if arch == "Append-Only":
                peer_ctx_a = append_retrieve(mem_a)
            elif arch == "Summarization":
                peer_ctx_a = summarize_retrieve(mem_a)
            else:
                peer_ctx_a = rag_retrieve(mem_a, passage)
        sys_a = SYSTEM_PROMPT.format(agent_id="A")
        user_a = user_prompt(t, "B", peer_ctx_a, passage)
        text_a = call_solver(sys_a, user_a)
        injected = rng.random() < float(p)
        if injected:
            text_a = apply_bias(text_a, bias, rng)
        bias_applied = 1.0 if injected else 0.0
        rows.append({"run_id": "grid-v4flash-20260806", "condition_id": f"{arch}|{bias}|p{p}",
                     "seed_id": seed, "round": t, "agent_id": "A", "arm": "biased",
                     "architecture": arch, "bias_type": bias, "contamination_rate": float(p),
                     "model_alias": model, "provider_response_model": DS_MODEL,
                     "provider_endpoint_id": DS_BASE, "temperature": TEMPERATURE,
                     "max_tokens": MAX_TOKENS, "request_id": f"gvf-{t}-{seed}-A",
                     "prompt_sha256": sha(sys_a + user_a), "response_text": text_a,
                     "output_token_count": len(text_a.split()), "bias_applied": bias_applied,
                     "memory_input_sha256": sha(peer_ctx_a), "code_commit": code_commit,
                     "config_sha256": config_sha, "corpus_sha256": corpus_sha,
                     "stored_summary_text": "", "retrieved_memory_text": peer_ctx_a,
                     "retrieval_document_ids": [], "retrieval_scores": [], "retrieval_threshold": THETA})
        # store A's (possibly biased) output; Summarization memory compresses it
        entry = {"text": text_a, "biased": injected}
        if arch == "Summarization":
            entry["summary"] = call_summarizer(text_a)
        mem_a.append(entry)
        # ---- clean agent B ----
        peer_ctx_b = "No prior peer output." if t == 0 else (mem_a[-1]["text"] if mem_a else "No prior peer output.")
        sys_b = SYSTEM_PROMPT.format(agent_id="B")
        user_b = user_prompt(t, "A", peer_ctx_b, passage)
        text_b = call_solver(sys_b, user_b)
        rows.append({"run_id": "grid-v4flash-20260806", "condition_id": f"{arch}|{bias}|p{p}",
                     "seed_id": seed, "round": t, "agent_id": "B", "arm": "clean",
                     "architecture": arch, "bias_type": bias, "contamination_rate": float(p),
                     "model_alias": model, "provider_response_model": DS_MODEL,
                     "provider_endpoint_id": DS_BASE, "temperature": TEMPERATURE,
                     "max_tokens": MAX_TOKENS, "request_id": f"gvf-{t}-{seed}-B",
                     "prompt_sha256": sha(sys_b + user_b), "response_text": text_b,
                     "output_token_count": len(text_b.split()), "bias_applied": 0.0,
                     "memory_input_sha256": sha(peer_ctx_b), "code_commit": code_commit,
                     "config_sha256": config_sha, "corpus_sha256": corpus_sha,
                     "stored_summary_text": "", "retrieved_memory_text": peer_ctx_b,
                     "retrieval_document_ids": [], "retrieval_scores": [], "retrieval_threshold": THETA})
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return "done"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--cells", default="all")
    ap.add_argument("--out", default=os.path.join(ROOT, "outputs", "grid_v4flash"))
    a = ap.parse_args()
    assert DS_KEY, "DEEPSEEK_API_KEY required"
    passages = [json.loads(l) for l in open(os.path.join(ROOT, "data", "passages.jsonl"), encoding="utf-8") if l.strip()]
    corpus_sha = hashlib.sha256(open(os.path.join(ROOT, "data", "passages.jsonl"), "rb").read()).hexdigest()
    code_commit = sha(open(os.path.abspath(__file__), encoding="utf-8").read())
    config_sha = sha(f"{DS_MODEL}|{TEMPERATURE}|{MAX_TOKENS}|{THETA}|{K}")
    os.makedirs(a.out, exist_ok=True)
    if a.cells == "smoke":
        cells = [("deepseek-v4-flash", "Append-Only", "length", "0.8")]
        a.seeds = 1; a.rounds = 2
    else:
        cells = [("deepseek-v4-flash", ar, bi, ra) for bi in ["length", "authority"]
                 for ra in ["0.2", "0.5", "0.8"] for ar in ["Append-Only", "Summarization", "RAG+Filter"]]
    g_bias = os.environ.get("GRID_BIAS", "all")
    g_arch = os.environ.get("GRID_ARCH", "all")
    if g_bias != "all":
        cells = [c for c in cells if c[2] == g_bias]
    if g_arch != "all":
        archs_ok = set(x.strip() for x in g_arch.split(","))
        cells = [c for c in cells if c[1] in archs_ok]
    shard_n = int(os.environ.get("GRID_SEED_SHARDS", "1"))
    shard_i = int(os.environ.get("GRID_SEED_INDEX", "0"))
    print(f"grid: {len(cells)} cells x {a.seeds} seeds x {a.rounds} rounds | model={DS_MODEL} | shard {shard_i}/{shard_n}", flush=True)
    done = skip = 0
    for cell in cells:
        for s in range(a.seeds):
            if s % shard_n != shard_i:
                continue
            status = run_cell(cell, s, passages, a.rounds, a.out, code_commit, config_sha, corpus_sha)
            done += status == "done"; skip += status == "skip"
            if status == "done":
                print(f"  done {cell} seed {s}", flush=True)
    print(f"FINISHED done={done} skip={skip}")

if __name__ == "__main__":
    main()
