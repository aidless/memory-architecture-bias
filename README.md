# PAPER5 — Memory-Architecture Contamination under TTRL (public evidence snapshot)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)  [![Data](https://img.shields.io/badge/data-CC--BY--4.0-lightgrey.svg)](LICENSE-DATA)

Repository for the paper "Memory-Architecture Bias Propagation under Controlled Contamination"
(public evidence snapshot. The manuscript is kept anonymous; no author identity is embedded in this repository.)

**What this is.** A frozen, offline-checkable evidence snapshot: 18-cell grid harness, protocol runners, analysis scripts and a verification suite, kept public so the reported numbers can be re-derived instead of trusted.

**Verified how.** `python3 source/verify_p5.py` re-runs the 6-category manuscript audit (abstract symbols, Bonferroni families, formalization, citation hygiene, reproducibility) offline with no model calls; measured status today: 0 HIGH / 0 MEDIUM / 4 LOW. Every evidence file also carries a SHA-256 in `evidence/evidence_manifest.json`.

**Run it.** `python3 source/verify_p5.py` (no install needed); full re-derivation needs `pip install -r source/requirements.txt`.

## Layout
- `source/` — paper sources (main.tex) and the collection/analysis harness:
  - `run_grid_v4flash.py` — rebuilt 18-cell grid harness (deepseek-v4-flash)
  - `run_protocol.py` — protocol runner (Round-3 cells)
  - `run_dose_response_extension.py` / `run_external_judge.py` / `run_meta_analysis.py` / `run_svd_dense_sensitivity.py` — analysis scripts
  - `verify_p5.py` — full verification suite
  - `protocol.md` — executed protocol (includes deviation record)
  - `reproduce_peer/`, `scoring/`, `tests/` — condition registry, gamma monitor, unit tests
- `evidence/` — archived per-cell logs, recomputed tables, and the 2026-08-09 external-task replication (open-ended generation; deepseek-v4-flash reversal +2.72, p<0.0001; gpt-5.4-mini null):
  - `round4_live.zip` (1,080 per-cell logs: v4-pro + v4-flash, 36 cells x 30 seeds)
  - `r1_v4chat_dose_response_per_seed.json` (90 per-seed records)
  - `recomputed_cell_means_FIXED.json` (Round-3, 12 cells x 10 seeds)
  - `p5_grid_v4flash_20260807.json` / `p5_grid_v4flash_summary_20260807.md`
  - analysis scripts under `scripts/`, outputs under `analyses/`
  - `evidence_manifest.json` (SHA-256 of every file, self excluded)
  - preregistration chain (`OSF_registration_P5_bc.md`, `prereg_freeze_hashes.json`, `deviation_round4_k9_20260808.md`)

## Reproduction
```
pip install -r source/requirements.txt
# Regenerate the reported per-cell tables from archived logs:
python source/verify_p5.py
python evidence/scripts/analyze_round4_20260808.py      # Round-4 k=9 family audits (needs evidence/round4_live.zip)
python evidence/scripts/analyze_r1_dose_response_20260807.py  # Table 2 recomputation
python evidence/scripts/analyze_p5_third_model_20260809.py    # cross-model direction check
# Re-run a single cell from scratch (requires a DeepSeek API key; the model
# defaults to deepseek-v4-flash and can be switched via DEEPSEEK_MODEL):
DEEPSEEK_API_KEY=... python source/run_grid_v4flash.py --rounds 10 --seeds 10
```
All random processes use fixed seeds; outputs are deterministic.

## Environment
- Python 3.12 (the version CI runs), dependencies in `source/requirements.txt`
  (`pip install -r source/requirements.txt`). `source/verify_p5.py` itself only
  needs the standard library; `source/run_meta_analysis.py` additionally needs
  `numpy` and `scipy`.
- Seeding: every harness draw flows through `source/reproduce_peer/seed_lock.py`
  (`seed_for(...)`, master salt `20260708`), seeds 0-9 per cell, temperature 0
  at the model API.

## Data availability
All delivered evidence is in this repository under `evidence/`, with a SHA-256
listing in `evidence/evidence_manifest.json`:
- `evidence/paper5_round3_live_logs.zip` — 120 Round-3 per-cell JSONL logs
  (`unzip evidence/paper5_round3_live_logs.zip -d source/paper5_round3_live_logs_20260713`
  to recompute the R3 arm in `run_meta_analysis.py`; verified to yield 12 cells).
- `evidence/round4_live.zip`, `evidence/grid_v4flash_logs.zip`,
  `evidence/p5_external_task_logs.zip` — archived live logs for the later rounds.
- The six Round-3 acceptance files listed in `source/REPRODUCE.md` (validator
  report, collection validation, confirmatory CSV/manifest, deviation record)
  live in the author's local output directory and are not distributed with the
  repository; `source/REPRODUCE.md` documents the checks to run against them.
  Everything else needed to recompute the reported tables ships here.

## Integrity
- `evidence/evidence_manifest.json` lists SHA-256 for every delivered file.
- Acceptance gates: `run_acceptance_gates_R14.py` in the submission package (exit 0).
- License: MIT.

## License

Code is MIT-licensed ([LICENSE](LICENSE)). Paper 5 (memory architectures) releases the logs and evidence archives under `evidence/` under
[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/).

GitHub's license detector reports this repository as `NOASSERTION` because it reads
a single SPDX id per repository and this one carries two. The split is deliberate:
the code stays permissively licensed so it can be reused, and the research material
stays attributable so a citation is required.