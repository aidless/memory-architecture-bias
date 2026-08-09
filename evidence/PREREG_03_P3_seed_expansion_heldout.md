# 预注册 03：PAPER3 自评种子扩充与分解复核（Seed Expansion + Held-out）
- 状态：草案
- 关联论文：PAPER3（Calibration Dynamics in Multi-Agent LLM Systems）

## English (OSF-ready)
**Title:** Pre-registered DeepSeek-V4-Pro self-evaluation seed expansion and held-out replication of the temporal-decomposition share
**Hypotheses:** (H1) With 30 seeds, γ_T→V remains far from the DeepSeek-chat CI [0.00, 0.07] (lower bound ≥ 0.2). (H2) The 90.8% temporal share of ΔECE reproduces (share ≥ 70%) on a held-out task set and on a second model family.

## 中文细则
- **假设**：30 种子下自评 γ_T→V 的 95% CI 下界 ≥0.2（非免疫）；held-out 任务集/第二模型族上纯时间占比 ≥70%。
- **设计**：E4 协议冻结，新增 15 种子（总 30，种子 16–30 由 `seed_lock` 派生）；held-out 任务集不与 8 条件设计任务重叠；第二模型族（建议 DeepSeek-V4-Flash，E4 同 prompt 集）。
- **Estimand**：γ_T→V（标准/校准）、ΔECE(pure T) 占比。
- **样本量**：自评 30 seeds × 2 模式；held-out 30 重复/条件 × 1 任务集 + 1 模型族。
- **排除规则**：API 失败种子重试 ≤2 次后排除并报告；禁止事后挑选种子。
- **分析计划**：bootstrap CI（B=10000）；占比 delta 法 CI；与 15 种子归档并表。
- **成功标准**：30 种子 CI 下界 ≥0.2 且 held-out 占比 ≥70%。
- **证伪标准**：CI 包含 0.2 以下值，或 held-out 占比 <70%。
- **停止规则**：任一子实验 API 连续失败 >10 次即暂停并报告。
- **预算**：DeepSeek 定价约 $0.14/M input、$0.28/M output；15 seeds × 2 模式 × 30 轮 × 2 agents ≈ 1,800 调用，约 $0.5–1；held-out 30×2×30×2 ≈ 3,600 调用，约 $1–2。合计约 $1.5–3。

> **模型决策（2026-08-06）**：执行/协议模型统一为 **deepseek-v4-flash**（api.deepseek.com，凭据待充值）；裁判/评估/辅助统一为 **gpt-5.6-luna**（Haolo 代理，实测可用）。见 `runbooks/model_decision_20260806.md`。

> **执行偏差（2026-08-06）**：evaluator 由 GLM5.2（密钥失效）改为 gpt-5.6-luna（Haolo 代理）；executor 保持 deepseek-v4-pro（协议模型）。种子 15–29 于 2026-08-06 21:20 启动。
