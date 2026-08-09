# PAPER5 — Memory-Architecture Contamination under TTRL (anonymous, available at acceptance)

Repository for the paper "Memory-Architecture Bias Propagation under Controlled Contamination"
(anonymous for double-blind review; final identity released at acceptance).

## Layout
- `source/` — paper sources (main.tex) and the collection/analysis harness:
  - `run_grid_v4flash.py` — rebuilt 18-cell grid harness (deepseek-v4-flash)
  - `run_protocol.py` — protocol runner (Round-3 cells)
  - `run_dose_response_extension.py` / `run_external_judge.py` / `run_meta_analysis.py` / `run_svd_dense_sensitivity.py` — analysis scripts
  - `verify_p5.py` — full verification suite
  - `protocol.md` — executed protocol (includes deviation record)
  - `reproduce_peer/`, `scoring/`, `tests/` — condition registry, gamma monitor, unit tests
- `evidence/` — archived per-cell logs, recomputed tables, and the 2026-08-09 external-task replication (open-ended generation; deepseek-v4-flash reversal +2.72, p<0.0001; gpt-5.4-mini null):
- `evidence/` — archived per-cell logs and recomputed tables:
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
# Re-run a single cell from scratch (requires a DeepSeek API key):
python source/run_grid_v4flash.py --model deepseek-v4-flash ...
```
All random processes use fixed seeds; outputs are deterministic.

## Integrity
- `evidence/evidence_manifest.json` lists SHA-256 for every delivered file.
- Acceptance gates: `run_acceptance_gates_R14.py` in the submission package (exit 0).
- License: MIT.
