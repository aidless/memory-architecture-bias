"""run_dose_response_extension.py — Path 1 dose-response extension.

Runs DeepSeek V4-Pro length bias at p=0.5 and p=0.2, Append-Only only,
n=10 paired seeds, T=10 rounds. Appends to the existing Round-3 collection.

The new files are written in Round-3 flat-naming convention:
    deepseek-v4-pro__Append-Only__length__p0.5__s{N}.jsonl
    deepseek-v4-pro__Append-Only__length__p0.2__s{N}.jsonl

Round-3 schema is preserved (run_id, condition_id, seed_id, round, agent_id,
arm, architecture, bias_type, contamination_rate, model_alias, etc.).

Usage:
    python run_dose_response_extension.py --api-key sk-... --cells p0.5,p0.2

Cost: ~$1 per cell, ~5-7 min per cell (parallelised at 8 concurrent).
"""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import json
import os
import random
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DEFAULT_MODEL = "deepseek-v4-pro"
CORPUS_SAMPLE_SIZE = 30
T = 10
N_SEEDS = 10
ALPHA = 1.5

# A simple filler pool (length bias injection)
FILLER_POOL = [
    "in general", "broadly speaking", "in essence", "as a whole",
    "typically", "on the whole", "put differently", "it seems plausible that",
    "by and large", "all things considered", "in the main", "to be sure",
    "as it were", "so to speak", "more or less", "in a sense",
    "for the most part", "in practice", "as a matter of fact", "in principle",
    "with respect to", "in the context of", "with regard to", "from the standpoint of",
]

ARCHITECTURE = "Append-Only"
BIAS_TYPE = "length"
AGENT_IDS = ["A", "B"]


def seed_for(*parts) -> int:
    """Deterministic seed derivation (matches reproduce_peer/seed_lock.py)."""
    h = hashlib.sha256()
    for p in parts:
        h.update(str(p).encode("utf-8"))
        h.update(b"|")
    return int.from_bytes(h.digest()[:4], "big")


def filler(alpha_tokens: int) -> str:
    """Generate filler text of approximately alpha_tokens tokens."""
    n = max(1, int(alpha_tokens))
    out = []
    while sum(len(s.split()) for s in out) < n:
        out.append(random.choice(FILLER_POOL))
    return " ".join(out)


def make_prompt(passage: str, biased: bool) -> str:
    """Make a summarisation prompt (with optional length bias)."""
    instruction = "Summarise the following passage in 1-2 sentences."
    if biased:
        instruction = (
            "Provide a detailed, comprehensive, multi-paragraph expansion of the "
            "following passage, drawing out every nuance, example, and edge case."
        )
    return f"{instruction}\n\nPassage:\n{passage}"


def call_api(prompt: str, api_key: str, model: str = DEFAULT_MODEL,
             temperature: float = 0.0, max_tokens: int = 512) -> str:
    """Single DashScope chat completion call."""
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    req = urllib.request.Request(
        DASHSCOPE_URL, data=body,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
    )
    last_err = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                resp = json.loads(r.read())
                return resp["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            raise
        except Exception as e:
            last_err = e
            time.sleep(1)
    raise RuntimeError(f"DashScope call failed after 4 attempts: {last_err}")


async def run_one_seed(model: str, p: float, seed_id: int,
                       corpus: list[str], api_key: str,
                       out_path: Path) -> None:
    """Run one seed (10 rounds × 2 agents) and write to JSONL."""
    rows = []
    random.seed(seed_for(model, ARCHITECTURE, BIAS_TYPE, p, seed_id))
    n_biased = int(round(p * T))
    biased_round_indices = set(random.sample(range(T), n_biased))

    for r in range(T):
        for agent_id in AGENT_IDS:
            passage = random.choice(corpus)
            biased = r in biased_round_indices
            text = make_prompt(passage, biased)
            if biased:
                # length bias injection: append filler ~50% of original length
                target_tokens = int(ALPHA * len(passage.split()))
                text = text + " " + filler(target_tokens)
            try:
                response = call_api(text, api_key, model=model)
            except Exception as e:
                print(f"  ERR {model} p={p} s={seed_id} r={r} a={agent_id}: {e}")
                continue
            row = {
                "run_id": "paper5-dose-response-extension-20260714",
                "condition_id": f"{model}__{ARCHITECTURE}__{BIAS_TYPE}__p{p}",
                "seed_id": seed_id,
                "round": r,
                "agent_id": agent_id,
                "arm": "biased" if biased else "clean",
                "architecture": ARCHITECTURE,
                "bias_type": BIAS_TYPE,
                "contamination_rate": p,
                "model_alias": model,
                "provider_response_model": model,
                "provider_endpoint_id": "dashscope-compatible",
                "temperature": 0.0,
                "max_tokens": 512,
                "request_id": f"dose-ext-{p}-s{seed_id}-r{r}-a{agent_id}",
                "memory_update_request_id": "",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "prompt_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "response_text": response,
            }
            rows.append(row)
    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


async def run_cell(model: str, p: float, corpus: list[str], api_key: str,
                   out_dir: Path, semaphore: asyncio.Semaphore) -> list[Path]:
    """Run one cell (10 seeds) with bounded concurrency."""
    written: list[Path] = []
    async def run_one(seed_id: int):
        async with semaphore:
            out_path = out_dir / f"{model}__{ARCHITECTURE}__{BIAS_TYPE}__p{p}__s{seed_id}.jsonl"
            await run_one_seed(model, p, seed_id, corpus, api_key, out_path)
            written.append(out_path)
            print(f"  ✓ {out_path.name}", flush=True)
    await asyncio.gather(*[run_one(s) for s in range(N_SEEDS)])
    return written


def load_corpus() -> list[str]:
    """30-passage corpus (synthetic, deterministic)."""
    rng = random.Random(20260714)
    words = [f"word{i}" for i in range(60)]
    passages = []
    for _ in range(CORPUS_SAMPLE_SIZE):
        n_words = rng.randint(40, 60)
        passage = " ".join(rng.choice(words) for _ in range(n_words))
        passages.append(passage)
    return passages


async def main(api_key: str, cells: list[float], out_dir: Path) -> None:
    corpus = load_corpus()
    out_dir.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(8)  # 8 concurrent
    for p in cells:
        print(f"\n=== Cell: {DEFAULT_MODEL} | {ARCHITECTURE} | {BIAS_TYPE} | p={p} ===")
        t0 = time.time()
        written = await run_cell(DEFAULT_MODEL, p, corpus, api_key, out_dir, semaphore)
        dt = time.time() - t0
        print(f"  Cell complete: {len(written)} seeds in {dt:.1f}s "
              f"({dt/60:.1f} min)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default=os.environ.get("DASHSCOPE_API_KEY", ""))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--cells", default="0.5,0.2",
                        help="comma-separated contamination rates")
    parser.add_argument("--out-dir", default=r"C:\Users\Administrator\AppData\Roaming\haolo_desktop\thread-groups\default\outputs\paper5_dose_response_extension_20260714")
    args = parser.parse_args()
    if not args.api_key:
        print("Error: --api-key or DASHSCOPE_API_KEY env required", file=sys.stderr)
        sys.exit(1)
    cells = [float(c) for c in args.cells.split(",")]
    asyncio.run(main(args.api_key, cells, Path(args.out_dir)))
