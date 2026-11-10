# PAPER5 — Memory-Architecture Contamination under TTRL (public evidence snapshot)

[![CI](https://github.com/aidless/memory-architecture-bias/actions/workflows/ci.yml/badge.svg)](https://github.com/aidless/memory-architecture-bias/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)  [![Data](https://img.shields.io/badge/data-CC--BY--4.0-lightgrey.svg)](LICENSE-DATA)

Repository for the paper "Memory-Architecture Bias Propagation under Controlled Contamination"
(public evidence snapshot. The manuscript is kept anonymous; no author identity is embedded in this repository.)

**What this is.** A frozen, offline-checkable evidence snapshot: 18-cell grid harness, protocol runners, analysis scripts and a verification suite, kept public so the reported numbers can be re-derived instead of trusted.

**Verified how.** `python3 source/verify_p5.py` re-runs the 6-category manuscript audit (abstract symbols, Bonferroni families, formalization, citation hygiene, reproducibility) offline with no model calls; measured status today: 0 HIGH / 0 MEDIUM / 4 LOW. Every evidence file also carries a SHA-256 in `evidence/evidence_manifest.json`.

**Run it.** `python3 source/verify_p5.py` (no install needed); full re-derivation needs `pip install -r source/requirements.txt`.

Quickstart 实测（2026-11-10，Linux · Python 3.12，真实输出节选）：

```text
$ python3 source/verify_p5.py
...
========================================================================
TOTAL: 4 findings (HIGH=0, MEDIUM=0, LOW=4)
========================================================================
```

（与 README 声明的 today's status「0 HIGH / 0 MEDIUM / 4 LOW」一致；LOW 项
为文档级提示，如未报告库版本号。）

## Key findings（核心结论，数字均取自 `source/main.tex` 与 `evidence/`）

- **主估计量**：偏置 vs clean 归一化输出长度分布的 Wasserstein-1 距离
  Γ_temporal 的配对架构对比；确认性推断仅限 DeepSeek V4-Chat length-injection
  网格（每格 n=10 配对种子，9 条预声明对比做 family-level Bonferroni）。
- **p=0.2**：RAG+Filter 点估计最低（−27.9% vs Append-Only，d_z=0.96，但
  k=9 校正后 p_adj=0.124，**不显著**）。
- **p=0.8**：Summarization 最低（−27.3%，d_z=1.18），该对比**通过** k=9
  family-level Bonferroni（p_raw=0.0047，p_adj=0.043）——全网格唯一存活的确认性显著对比。
- **authority-marker 注入（p=0.8，n=10）**：Summarization 指标最低
  （0.544 vs Append-Only 0.802），但**不构成** authority-bias 传播证据
  （指标可能捕捉冗长/格式/拒答/任务难度）。
- **总体结论**：只支持「架构排序在所测输出长度协议内变化」，构念验证仍需进行。
- **外部任务复现（开放式生成，2026-08-09）**：v4-flash 反转复现
  （Summ − Append = **+2.72**，p<0.0001）；gpt-5.4-mini 方向相反/ null——
  架构效应是**模型与语料依赖**的。
- **两模型 model-by-bias 因子（v4-pro + v4-flash，每格 30 seeds）**：
  排序随版本变化——Summarization 在两个 Round-4 模型上均最高，与 R1
  V4-Chat 排序（Summ 最低）**相反**。

## Results（结果表）

### 18 格网格均值（v4-flash 确认网格，2026-08-07；`evidence/p5_grid_v4flash_summary_20260807.md`）

| bias | arch | p=0.2 | p=0.5 | p=0.8 |
|---|---|---|---|---|
| length | Append-Only | 0.519 | 0.790 | 2.385 |
| length | Summarization | 0.580 | 0.946 | 0.974 |
| length | RAG+Filter | 0.999 | 0.786 | 0.909 |
| authority | Append-Only | 0.678 | 0.521 | 0.853 |
| authority | Summarization | 0.575 | 0.442 | 0.521 |
| authority | RAG+Filter | 0.831 | 0.987 | 0.607 |

族审计（k=9 × 2，BH）：length 族与 authority 族**均无**对比在 BH 后显著
（最小 raw p=0.0235 / 0.029）；length Append p0.8 重尾（mean 2.385, sd 5.0）。

### 唯一存活的 R1 显著对比跨模型方向核验（`evidence/analyses/p5_third_model_direction_20260809.json`）

| 模型 | Summ − Append @ p=0.8 | p_raw | n | 方向 |
|---|---|---|---:|---|
| R1 V4-Chat | −0.0727 | 0.0002 | 10 | Summ 更低 |
| Qwen3.7-Plus | −0.0969 | 0.4106 | 10 | Summ 更低（NS） |
| deepseek-v4-pro | +0.0007 | 0.9944 | 30 | NS |
| deepseek-v4-flash | +0.2024 | 0.0001 | 30 | **Summ 更高（反转）** |

### 手稿审计状态（`source/verify_p5.py`，离线可复算）

| 审计类别 | 状态 |
|---|---|
| HIGH / MEDIUM | 0 / 0（2026-11-10 实测） |
| LOW | 4（文档级提示） |
| 证据完整性 | `evidence/evidence_manifest.json` 逐文件 SHA-256 |

## What this doesn't claim / Limits

- **不声明** authority-bias 传播：authority 指标可能捕捉冗长、格式、拒答或任务难度（构念验证 required）。
- **不声明** 架构效应普适：v4-flash 全网格与外部任务均显示效应依赖模型与语料；Qwen3.7-Plus 与 gpt-5.4-mini 数字为描述性。
- Round-3 的六个验收文件（validator report、collection validation 等）在作者本地输出目录，未随仓库分发；`source/REPRODUCE.md` 记录核对方法。
- v4-pro 的 p=0.2/0.5 格未收集且不再计划（偏差记录见 `evidence/deviation_round4_k9_20260808.md`）。


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