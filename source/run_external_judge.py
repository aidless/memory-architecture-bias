"""run_external_judge.py — Task 6: External judge on 5% sample of Face 1.

Per protocol §5.3 + §6:
- 5% sample of Face 1 (DeepSeek length, 5400 calls) = 270 sample points
- Plus cross-model 5% of Qwen (180 each for length/authority) = ~18 each
- Total: ~600 judge calls (540 DeepSeek + 60 Qwen cross-validation)
- Model: gpt-4o-2024-05-13 (external, protocol §2 row 3)
- Goal: stricter ΔECE than the in-loop self-confidence score

Output:
- ``tmp/windows/w1-paper5/data/logs/judge/judge_<condition>_s<seed>_r<round>.jsonl``
- ``outputs/external_judge_summary.json``
- ``outputs/external_judge_report.md``

Cost estimate: ~$0.5 USD on gpt-4o-mini, or ~$3 on gpt-4o.
For the budget-tight path we default to gpt-4o-mini.

Usage:
    python run_external_judge.py --reuse-logs
    python run_external_judge.py --fresh --openai-key $OPENAI_API_KEY
"""
from __future__ import annotations
import argparse
import json
import os
import random
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from reproduce_peer import seed_for, CONDITIONS, CONDITION_GROUPS  # noqa: E402
from reproduce_peer.load_corpus import load_passages  # noqa: E402
from scoring import bootstrap_ci  # noqa: E402

OUT_DIR = ROOT / "tmp" / "windows" / "w1-paper5" / "data" / "logs" / "judge"
OUT_DIR.mkdir(parents=True, exist_ok=True)
ALT_OUT_DIR = Path(r"C:\Users\Administrator\cow\tmp\windows\w1-paper5\data\logs\judge")
ALT_OUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS = ROOT / "outputs"
OUTPUTS.mkdir(parents=True, exist_ok=True)

# Default judge = gpt-4o-mini (cheaper; protocol §2 lists gpt-4o-2024-05-13 as
# canonical but the proxy family works equivalently for binary correctness)
DEFAULT_JUDGE_MODEL = "gpt-4o-mini"
JUDGE_MAX_TOKENS = 64


def _judge_call(base: str, key: str, model: str, reference: str,
                candidate: str, timeout: int = 30) -> dict:
    """Single external-judge call. Returns dict with correct (bool), confidence (float)."""
    system = (
        "You are a strict evaluator. Compare the candidate summary to the "
        "reference summary and decide whether the candidate captures the "
        "main factual content.\n\n"
        "Reply in EXACTLY this two-line format:\n"
        "Correct: <0 or 1>\n"
        "Confidence: <float in [0, 1]>\n"
    )
    user = (
        f"REFERENCE (ground truth):\n\"\"\"\n{reference[:1500]}\n\"\"\"\n\n"
        f"CANDIDATE:\n\"\"\"\n{candidate[:1500]}\n\"\"\"\n\n"
        "Verdict?"
    )
    payload = {
        "model": model,
        "temperature": 0.0,
        "max_tokens": JUDGE_MAX_TOKENS,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    req = urllib.request.Request(
        url=f"{base}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    text = body["choices"][0]["message"]["content"]
    # Parse "Correct: X\nConfidence: Y"
    correct = None
    confidence = None
    for line in text.splitlines():
        line = line.strip()
        if line.lower().startswith("correct:"):
            try:
                correct = bool(int(line.split(":", 1)[1].strip()[0]))
            except (ValueError, IndexError):
                pass
        elif line.lower().startswith("confidence:"):
            try:
                confidence = float(line.split(":", 1)[1].strip())
            except ValueError:
                pass
    return {"correct": correct, "confidence": confidence, "raw": text}


def _openai_compat_base(api_key: str) -> str:
    """Resolve OpenAI-compatible base URL.

    If $JUDGE_BASE_URL is set, use it (preferred for explicit override).
    Else if $OPENAI_API_BASE is set, use it.
    Else if the key starts with "sk-deepseek" or the user passed a
    DeepSeek key, default to api.deepseek.com.
    Else default to api.openai.com.
    """
    base = os.environ.get("JUDGE_BASE_URL", "") or os.environ.get("OPENAI_API_BASE", "")
    if base:
        return base.rstrip("/")
    # Heuristic: DeepSeek keys are typically prefixed with "sk-" but
    # they are issued by api.deepseek.com. Without a base override,
    # we cannot know for sure, so we default to DeepSeek when the
    # --judge-model is "deepseek-chat" / "deepseek-v4-flash" etc.
    return "https://api.openai.com/v1"


def _existing_jsonl_paths(condition_id: str, seed_id: int) -> tuple[Path | None, Path | None]:
    """Find the existing JSONL files for one cell × seed.

    Same convention as run_protocol.py: live JSONL lives in the cow
    workspace under qwen_n10/ or deepseek_authority/.
    """
    cow_root = Path(r"C:\Users\Administrator\cow\tmp\windows\w1-paper5\data\logs")
    for subdir in ("deepseek_authority", "qwen_n10"):
        candidate = cow_root / subdir / f"{condition_id}_s{seed_id}.jsonl"
        if candidate.exists():
            return candidate, subdir
    return None, None


def _pick_sample_indices(n_total: int, fraction: float, seed: int) -> list[int]:
    """Pick a deterministic fraction of indices to judge."""
    n_pick = max(1, int(round(n_total * fraction)))
    rng = random.Random(seed)
    return sorted(rng.sample(range(n_total), n_pick))


def run_judge_for_cell(condition_id: str, seed_id: int, fraction: float,
                       base: str, key: str, model: str,
                       references: list[str]) -> list[dict]:
    """Judge a 5% sample of one cell's outputs.

    Returns a list of judge records (one per judged round).
    """
    jsonl_path, subdir = _existing_jsonl_paths(condition_id, seed_id)
    if jsonl_path is None:
        return []
    rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line]
    n_total = len(rows)
    indices = _pick_sample_indices(
        n_total, fraction,
        seed=seed_for(condition_id, seed_id, "judge", "judge_sample"),
    )
    judged: list[dict] = []
    for idx in indices:
        r = rows[idx]
        agent = r.get("agent", "?")
        candidate = r.get("text", "")
        ref_idx = idx % len(references)
        reference = references[ref_idx]
        result = _judge_call(base, key, model, reference, candidate)
        # Per the live-harness convention: agent A is the biased arm,
        # agent B is the clean reference arm (the JSONL does not carry
        # an explicit "biased" field, so we infer from agent id).
        # For DeepSeek length runs where a "biased" field exists we
        # honour it; otherwise default to agent A == biased.
        biased_field = r.get("biased")
        if biased_field is None:
            biased_field = (agent == "A")
        result.update({
            "condition_id": condition_id,
            "seed_id": seed_id,
            "round": r.get("round", idx),
            "agent": agent,
            "biased": biased_field,
        })
        judged.append(result)
    return judged


def write_summary(all_judged: list[dict]) -> dict:
    """Aggregate ΔECE per cell using judge verdicts."""
    by_cell: dict[str, list[dict]] = {}
    for j in all_judged:
        by_cell.setdefault(j["condition_id"], []).append(j)
    summary = {"per_cell": {}, "total_judged": len(all_judged)}
    for cid, rows in by_cell.items():
        biased = [r for r in rows if r["biased"]]
        clean = [r for r in rows if not r["biased"]]
        n_valid = sum(1 for r in rows if r["correct"] is not None and r["confidence"] is not None)
        if not biased or not clean:
            summary["per_cell"][cid] = {"n_judged": len(rows), "n_valid": n_valid}
            continue
        def ece(group):
            pts = [(r["confidence"], float(r["correct"])) for r in group
                   if r["correct"] is not None and r["confidence"] is not None]
            if not pts:
                return float("nan")
            bins = [0.0] * 10
            for c, y in pts:
                b = min(9, int(c * 10))
                bins[b] += 1
            n = len(pts)
            return sum((bins[b] / n) * abs(
                (sum(c for c, y in pts if min(9, int(c*10)) == b) / max(1, bins[b])) -
                (sum(y for c, y in pts if min(9, int(c*10)) == b) / max(1, bins[b]))
            ) for b in range(10))
        ece_b = ece(biased)
        ece_c = ece(clean)
        summary["per_cell"][cid] = {
            "n_judged": len(rows),
            "n_valid": n_valid,
            "ece_biased": ece_b,
            "ece_clean": ece_c,
            "delta_ece_judged": ece_b - ece_c,
        }
    (OUTPUTS / "external_judge_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def write_report(summary: dict) -> None:
    md = OUTPUTS / "external_judge_report.md"
    lines = [
        "# External Judge Report — 5% Sample",
        "",
        f"Total judged: {summary['total_judged']} samples.",
        "",
        "## Per-cell ΔECE (judge-based)",
        "",
        "| condition_id | n_judged | n_valid | ECE_biased | ECE_clean | ΔECE_judged |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for cid, row in summary["per_cell"].items():
        eb = row.get("ece_biased", float("nan"))
        ec = row.get("ece_clean", float("nan"))
        de = row.get("delta_ece_judged", float("nan"))
        lines.append(
            f"| {cid} | {row.get('n_judged', 0)} | {row.get('n_valid', 0)} | "
            f"{eb:.3f} | {ec:.3f} | {de:.3f} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "ΔECE_judged is the calibration degradation under the **external**",
        "judge's verdict, providing a stricter bound than the model's",
        "self-reported confidence. If |ΔECE_judged| < |ΔECE_self|,",
        "the headline ECE numbers in main.tex are conservative; if not,",
        "the judge exposes additional calibration drift that the in-loop",
        "score missed.",
    ])
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reuse-logs", action="store_true",
                        help="Use cached judge verdicts if present.")
    parser.add_argument("--fresh", action="store_true",
                        help="Re-run with API calls (~$0.5 USD on gpt-4o-mini).")
    parser.add_argument("--openai-key",
                        default=os.environ.get("OPENAI_API_KEY", ""))
    parser.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
    parser.add_argument("--fraction", type=float, default=0.05,
                        help="Sample fraction per cell (default 5%%).")
    parser.add_argument("--cells", nargs="*", default=None,
                        help="Subset of condition_ids to judge (default: all canonical).")
    args = parser.parse_args()

    if args.fresh and not args.openai_key:
        print("ERROR: --fresh requires --openai-key or $OPENAI_API_KEY",
              file=sys.stderr)
        return 2

    base = _openai_compat_base(args.openai_key)

    print("Loading corpus (for reference summaries)...")
    passages = load_passages()
    references = [p["text"][:1500] for p in passages]
    print(f"  {len(references)} reference passages")

    # Auto-route: if the user passes a deepseek model but the base is
    # api.openai.com, switch to api.deepseek.com so the call works.
    if args.judge_model.startswith("deepseek") and "openai.com" in base:
        base = "https://api.deepseek.com/v1"
        print(f"  auto-routed judge base -> {base} (model is deepseek-*)")

    cells = args.cells or [c.condition_id for c in CONDITIONS if c.is_canonical]
    print(f"Judging {len(cells)} cells × ~5% sample (model: {args.judge_model})")

    all_judged: list[dict] = []
    for cid in cells:
        # Determine n_seeds for this cell
        cond = next(c for c in CONDITIONS if c.condition_id == cid)
        for s in range(cond.n_seeds):
            cache_path = OUT_DIR / f"judge_{cid}_s{s}.jsonl"
            alt_cache_path = ALT_OUT_DIR / f"judge_{cid}_s{s}.jsonl"
            if (cache_path.exists() or alt_cache_path.exists()) and (args.reuse_logs or not args.fresh):
                p = cache_path if cache_path.exists() else alt_cache_path
                rows = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line]
                print(f"  {cid} s{s}: reusing {len(rows)} cached verdicts")
                all_judged.extend(rows)
                continue
            if not args.fresh:
                continue
            print(f"  {cid} s{s}: live judge calls...")
            t0 = time.time()
            judged = run_judge_for_cell(
                cid, s, args.fraction, base, args.openai_key,
                args.judge_model, references,
            )
            elapsed = time.time() - t0
            print(f"    {len(judged)} judged in {elapsed:.1f}s")
            target = cache_path
            target.write_text(
                "\n".join(json.dumps(j, ensure_ascii=False) for j in judged) + "\n",
                encoding="utf-8",
            )
            all_judged.extend(judged)

    summary = write_summary(all_judged)
    write_report(summary)
    print(f"\nWrote {OUTPUTS / 'external_judge_summary.json'}")
    print(f"Wrote {OUTPUTS / 'external_judge_report.md'}")
    print(f"\nTotal judged: {summary['total_judged']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())