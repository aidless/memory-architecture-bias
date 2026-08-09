# OSF 预注册表单（PAPER5，执行版）— 2026-08-06 填写，2026-08-07 结果回写

## 1. Title
Rebuilt-grid completion for the memory-architecture contamination protocol (deepseek-v4-flash, 18 cells) and Qwen 10-seed archive upgrade

## 2. Authors
Anonymous (TMLR double-blind)

## 3. Research Question
Does the memory-architecture ranking under controlled contamination hold (a) across both bias types and three contamination rates in a rebuilt grid, and (b) when the Qwen arm is evaluated on its full 10-seed archive?

## 4. Background & Rationale
The manuscript declared 15 condition combinations but the original Round-3 collection harness was unavailable locally; the archive was found to contain p=0.8 cells for both models. We rebuilt the harness from the protocol prompts and executed a complete 18-cell grid on deepseek-v4-flash (project model decision).

## 5. Hypotheses (as executed)
- H1: In the rebuilt 18-cell grid (deepseek-v4-flash; length + authority x rates {0.2, 0.5, 0.8} x 3 architectures x 10 seeds x 10 rounds), at least one architecture contrast survives BH within a k=9 family.
- H2: The architecture ordering is directionally consistent across the two bias types.
- H3: Qwen architecture ordering is stable between the 3-seed subset and the 10-seed archive (Kendall >= 0.8).

## 6. Sampling Plan (as executed)
- Existing data: Round-3 live logs (deepseek-v4-pro + qwen3.7-plus, 120 per-cell JSONL); Qwen 10-seed archive (recomputed_cell_means_FIXED.json); R1 V4-Chat dose-response per-seed records (90).
- New data: rebuilt harness (run_grid_v4flash.py, frozen hash A871A936...) produced 180 per-cell JSONL (18 cells x 10 seeds, T=10, deepseek-v4-flash).

## 7. Variables
Manipulated: architecture (Append-Only / Summarization / RAG+Filter), contamination rate p in {0.2, 0.5, 0.8}, bias type (length vs authority markers). Measured: Gamma_temporal (Wasserstein-1 on normalized output length), per-seed values persisted to JSONL.

## 8. Design Plan
Confirmatory pre-registered grid completion; paired-seed within-cell design; seeds fixed by seed_lock (0-9); temperature 0; no analyst blinding (automated pipeline).

## 9. Analysis Plan
Family-level BH and Holm over each k=9 family; paired t-tests on per-seed Delta Gamma; Kendall between n=3 and n=10 orderings; reversal probability over all C(10,3) subsets reported (not used for decisions).

## 10. Other
No human participants; synthetic contamination markers only. API: deepseek-v4-flash via DeepSeek account. Data availability: 180 per-cell JSONL + 120 Round-3 logs + analysis scripts in the accompanying evidence package.

## 11. Deviation record (executed vs originally planned)
- Model: deepseek-v4-flash instead of DeepSeek V4-Chat (project model decision 2026-08-06).
- Design: T=10 rounds (matching archived Round-3 cells) instead of protocol Face-1 T=30; grid expanded to both bias types x 3 rates (18 cells).
- Harness: rebuilt from protocol prompts (protocol.md Section 4) because the original Round-3 collection harness was not available locally.

## 12. Outcome record (2026-08-07)
- H1: NOT met for the rebuilt grid - no contrast survives BH in either k=9 family (smallest raw p=0.0235 length, 0.029 authority).
- H2: Partially - Summarization is lowest in both arms at p=0.8 (0.530/0.544), but orderings differ across rates.
- H3: Length Kendall=0.33 (not met; Append/RAG flip); authority Kendall=1.0 (met).
- NOTE: the R1 V4-Chat dose-response (separate, archived) has one family-level-significant contrast (Summarization vs Append-Only at p=0.8, p_adj=0.043); it is not part of the rebuilt grid.
