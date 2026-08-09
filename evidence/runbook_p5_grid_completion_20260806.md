# 冻结执行手册：PAPER5 (b)(c) — 2026-08-06（含 2026-08-06 执行偏差记录）

## 模型决策（2026-08-06，用户指定）
- 执行/协议模型：**deepseek-v4-flash**（api.deepseek.com；凭据 PAPER5_DEEPSEEK_API_KEY 账户，需充值）。
- 裁判/评估/辅助：**gpt-5.6-luna**（Haolo 代理，实测可用）。
- 详见 `model_decision_20260806.md`。

## 执行偏差记录（2026-08-06，执行前发现）
- **归档发现**：Round-3 日志（`paper5_round3_live_logs_20260713`）与 legacy 日志（`cow/.../deepseek_authority`）中**已存在** DeepSeek V4-Chat × authority × p=0.8 的三格数据（n=10 seeds，T=10）。`recomputed_cell_means_FIXED.json` 亦已含该三格（0.822/0.818/0.661）。
- **据此变更**：(b) 的 p=0.8 部分**无需新 API 调用**，已在 Revision 4 直接分析（`scripts/analyze_p5_completion_20260806.py` → `analyses/p5_completion_20260806.json`）；(b) 剩余范围缩小为 authority × p∈{0.2,0.5}（该数据从未收集，如执行仍按本手册条件 ID 与预算执行）。
- (c) 已完成：Qwen 两臂按 n=10 正式入表（Revision 4），n3/n10 Kendall：length 0.33（翻转）、authority 1.0（稳定）。
- 原始预注册文档哈希见 `prereg_freeze_hashes.json`；本变更按"执行前发现、先更新文档再执行"纪律记录。
> 先完成 `osf_forms/OSF_registration_P5_bc.md` 的 OSF 提交，再执行本手册。结果产出前不更改以下任何参数。

## 环境
- 工作目录：`F:\Research\PAPER5_CONSOLIDATED`
- 密钥（环境变量，禁止写入文件）：`DEEPSEEK_API_KEY`（DeepSeek V4-Chat）、`QWEN_API_KEY`（如需要）、`OPENAI_API_KEY`（外部裁判）
- 模型快照：DeepSeek V4-Chat（以提交时协议解析为准，冻结于执行前）

## (b) DeepSeek V4-Chat × authority 补格（新 API 调用）
- 条件：9 格 = D-{A,S,R}-{02,05,08}，bias=authority；10 seeds（seed_lock 0–9）；30 轮 × 2 agents。
- **执行前冻结**（结果产出前完成并哈希）：
  1. 在 `reproduce_peer/condition_registry.py` 中按现有约定新增 `deepseek_authority` 族（9 格：3 arch × 3 rates × 10 seeds，rounds=30），冻结该文件 SHA-256；
  2. 确认 `CONDITION_GROUPS` 只包含本族，避免误跑其他族产生额外费用。
- 执行（本地根目录入口）：
```powershell
$env:PYTHONIOENCODING='utf-8'; $env:PYTHONUTF8='1'
Set-Location 'F:\Research\PAPER5_CONSOLIDATED'
python run_protocol.py --fresh --family deepseek_authority   # 需要 $env:DEEPSEEK_API_KEY
python scoring/gamma_monitor.py --input outputs/protocol_run.jsonl
```
- 产出：每格 `{model}__{arch}__authority__p{rate}__s{seed}.jsonl`（追加进 `tmp/windows/w1-paper5/data/logs/` 或协议指定位置）+ 合并 `outputs/protocol_run.jsonl` + `outputs/protocol_run_summary.json`。
- 预算：≈5,400 调用 ≈ $1.5–2；墙钟 60–90 分钟（3 workers）。
- 停止规则：单格连续 API 失败 >10 次 → 暂停并报告；预算超限 → 停止。

## (c) Qwen 全归档（n=10）正式入表（无新 API）
- 输入：`outputs/recomputed_cell_means_FIXED.json`（12 格 × 10 seeds）。
- 冻结审计（BH 族校正 + 排序 + n3/n10 对比）：
```powershell
python 'C:\Users\Administrator\AppData\Roaming\haolo_desktop\thread-groups\default\科研\outputs\five_paper_acceptance_baseline_20260806\scripts\analyze_p5.py'
```
- 产出：`analyses/p5_robustness.json`（族审计 + 交互模型）；n3/n10 排序对照见 `analyses/heldout_validations_20260806.json` → `P4_decision_rule_Qwen_n3_vs_n10`。
- 判定：Kendall(n3, n10) ≥ 0.8 → 正文升级为 n=10；<0.8 → 按 n=10 改写结论并在正文报告排序不稳定性。

## 结果回写（完成后）
1. 新 9 格均值并入 `recomputed_cell_means_FIXED.json` 的扩展版本（36 格）。
2. 更新 `analyses/evidence_ledger_20260806.json` 中 PAPER5 行状态（RECOMPUTED）。
3. 更新 Revision4 正文（k=9 authority 族、n=10 Qwen、判别效度段落如有 (a) 结果）。
4. 重编译五篇 PDF → 新哈希 → 更新 `REVISION_STATUS` 与基线文档。
5. 交由 Review-Agent/用户复审（本代理不代跑审稿）。

## 变更日志（执行时逐条填写）
- [ ] 预注册提交时间与 URL：
- [ ] 实际调用数与费用：
- [ ] 偏离项（若有）：

## 执行记录（2026-08-06 21:20）
- **P3 E4 种子扩充已启动**（后台 PID 17948，`run_e4_n15.py --n-seeds 30 --rounds 30 --resume`）：
  - executor = deepseek-v4-pro（协议模型，充值后可用）；evaluator = gpt-5.6-luna（Haolo 代理；原 GLM5.2 密钥失效，**偏差已记录**，PREREG_03 哈希已更新）。
  - 种子 0–14 跳过（检查点已有），15–29 新跑；预计 ~10,800 调用、数小时。
  - `run_e4_n15.py` 已打 env 补丁（DS_URL/DS_MODEL/GLM_URL/GLM_MODEL 可环境覆盖，默认不变）。
- **P5 authority 0.2/0.5 补格：BLOCKED（harness 缺失）**：Round-3 实况采集 harness（R3 日志生成器）不在本地任何仓库；`memory_architecture` 是 R1 配置（AGENTS=3、模型 deepseek-chat 已不在充值账户模型列表，仅 deepseek-v4-flash/v4-pro）且 schema 与 R3 不一致，**不能伪跑冒充补格**。维持 p=0.8 已完成结论；0.2/0.5 待原 harness 或重建授权。

## 方案 A 执行记录（2026-08-06 21:40）
- **R3 harness 已重建并冻结**：`F:\Research\PAPER5_CONSOLIDATED\run_grid_v4flash.py`（SHA-256 `A871A93676BCC44C…`）。
  - 提示词/偏置/引用/语料严格取自 protocol.md §4；T=10（与 R3 归档一致）；模型 deepseek-v4-flash；温度 0；max_tokens 512；Summarization 用 §4.4 摘要压缩；RAG 手工 TF-IDF + θ=0.1；偏置施加于 biased agent 输出（与 legacy/R3 日志格式一致）。
  - **偏差**：重建 harness + 新模型（v4-flash）替代 v4-pro 原网格；T=10 而非协议 Face-1 的 30。
- **全网格已启动**：18 格（length+authority × 0.2/0.5/0.8 × 3 arch）× 10 seeds × 10 rounds，8 进程并行（pids.txt），预计 2.5–3 小时；每格完成即写 `outputs/grid_v4flash/*.jsonl`（可断点续跑）。
- 完成后：gamma_per_file 计算 → 18 格逐种子表 → k=9 length 族 + k=9 authority 族 BH 审计 → Revision6。
