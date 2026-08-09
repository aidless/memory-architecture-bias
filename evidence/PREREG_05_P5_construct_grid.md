# 预注册 05：PAPER5 判别效度 + DeepSeek authority 补格 + Qwen 全归档入表
- 状态：草案；对应验收基线 Class C 的 P5 (a)(b)(c)
- 关联论文：PAPER5（Memory Architecture Effects on Output-Length Responses under Controlled Multi-Agent Contamination）

## English (OSF-ready)
**Title:** Pre-registered discriminant-validity audit and confirmatory-grid completion for the memory-architecture contamination protocol
**Hypotheses:** (H1) Γ_temporal remains responsive to contamination injection after adjusting for verbosity, refusal rate, formatting, and task difficulty. (H2) In the completed DeepSeek V4-Chat authority grid (3 architectures × 3 rates × 10 seeds), the architecture ordering follows the length-grid pattern and the k=9 family survives BH correction. (H3) Qwen conclusions are stable between the reported n=3 and the full n=10 archive (Kendall ordering ≥ 0.8).

## 中文细则
- **(a) 判别效度**：持久化 executor 逐轮回复文本 → 计算 verbosity（字符/词数）、refusal 率（正则+judge 双重）、formatting（bullet/编号/分节）、任务难度；Γ_temporal 做偏相关/回归调整。
  - 成功标准：控制协变量后污染注入对 Γ 的方向与显著性不变。
  - 证伪标准：控制后效应消失或翻转。
- **(b) DeepSeek authority 补格**：9 格 = D-{A,S,R}-{02,05,08} × bias=authority × 10 seeds × 30 轮 × 2 agents。
  - 条件 ID 遵循协议命名（D-A-02 等，bias=authority）；种子由 `reproduce_peer.seed_lock.seed_for` 派生（0–9）。
  - 成功标准：k=9 族内至少 1 个对比经 BH 后显著，且 RAG/Summarization 与 Append-Only 的相对排序与 length 网格方向一致。
  - 证伪标准：全部 9 对比校正后不显著，或排序与 length 网格相反。
- **(c) Qwen 全归档入表**：现有 10 seeds/格（recomputed_cell_means_FIXED.json）正式入表，替代报告值 n=3；冻结 n=10 审计（BH 族校正 + 排序）。
  - 成功标准：n=3 与 n=10 排序 Kendall ≥ 0.8。
  - 证伪标准：Kendall < 0.8（此时正文按 n=10 改写结论）。
- **停止规则**：任一格 API 连续失败 >10 次暂停并报告；预算超限即停。
- **预算**：(b) ≈ 10×3×3×30×2 = 5,400 调用，约 $1.5–2（DeepSeek 定价）；(a)(c) 无新调用（文本持久化与重分析）。

> **模型决策（2026-08-06）**：执行/协议模型统一为 **deepseek-v4-flash**（api.deepseek.com，凭据待充值）；裁判/评估/辅助统一为 **gpt-5.6-luna**（Haolo 代理，实测可用）。见 `runbooks/model_decision_20260806.md`。
