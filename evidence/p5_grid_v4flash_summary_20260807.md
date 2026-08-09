# P5 v4-flash 确认网格结果 — 2026-08-07

数据：`outputs/grid_v4flash/`（180 文件 = 18 格 × 10 seeds × 10 rounds；模型 deepseek-v4-flash；T=10；重建 harness 哈希 A871A936…）。
口径：`gamma_per_file`（clean 归一化词数 W1），与归档 v4-pro p=0.8 一致。

## 18 格均值
| bias | arch | p=0.2 | p=0.5 | p=0.8 |
|---|---|---|---|---|
| length | Append-Only | 0.519 | 0.790 | 2.385 |
| length | Summarization | 0.580 | 0.946 | 0.974 |
| length | RAG+Filter | 0.999 | 0.786 | 0.909 |
| authority | Append-Only | 0.678 | 0.521 | 0.853 |
| authority | Summarization | 0.575 | 0.442 | 0.521 |
| authority | RAG+Filter | 0.831 | 0.987 | 0.607 |

## 族审计（k=9 × 2，BH）
- **length 族**：无对比在 BH 后显著（最小 raw p=0.0235 @ Append vs RAG p0.2 → BH 0.2115）。
- **authority 族**：无对比在 BH 后显著（最小 raw p=0.029 @ p0.5 → BH 0.1363）。
- 噪声大：length Append p0.8 mean=2.385 sd=5.0（重尾）；v4-flash 在该语料上输出稳定性弱于 v4-pro。

## 结论
- v4-flash 全网格与 v4-pro p=0.8 归档一致：**校正后无架构对比显著**——架构效应的统计支持仍然不足，论文的方向性结论维持。
- v4-flash 剂量-反应无单调趋势（与 deepseek-chat R1 的 -0.26/-0.10/-0.37 斜率不同），进一步支持「架构效应模型/语料依赖」。
- 偏差记录：重建 harness、T=10、v4-flash 替代 v4-pro；v4-pro 的 0.2/0.5 格仍未收集（不再计划）。