# 模型决策记录（Model Decision）— 2026-08-06

**决策（用户指定，2026-08-06）**：后续实验与辅助调用统一使用两个模型：
1. **deepseek-v4-flash** — 作为 DeepSeek 相关实验的执行/协议模型（P3 E4 种子扩充、P5 补格等）。
2. **gpt-5.6-luna** — 作为裁判/评估/辅助模型（经 Haolo 代理，OpenAI-compatible）。

## 可用性实测（2026-08-06）
| 模型 | 路径 | 状态 |
|---|---|---|
| gpt-5.6-luna | Haolo 代理 `{OPENAI_BASE_URL}/chat/completions`（`gpt-5.6-luna`） | ✅ 可用（实测 OK） |
| deepseek-v4-flash | 代理 /chat/completions | ❌ 400（代理白名单无此模型） |
| deepseek-v4-flash | 代理 /responses | ❌ 502（网关后端不可用） |
| deepseek-v4-flash | api.deepseek.com（DEEPSEEK_API_KEY / HAOLO_DEEPSEEK_EXECUTION_TOKEN / EXECUTOR_API_KEY） | ❌ 401（密钥无效） |
| deepseek-v4-flash | api.deepseek.com（PAPER5_DEEPSEEK_API_KEY） | ⚠️ 402 欠费——**充值即用** |

## 执行规则
- 需要 DeepSeek 的协议内实验（P3 executor、P5 补格）：使用 deepseek-v4-flash，端点 api.deepseek.com，凭据 = PAPER5_DEEPSEEK_API_KEY 对应账户（充值后）。
- 裁判/评估/辅助（判别效度、外部裁判、evaluator 替代、烟测）：使用 gpt-5.6-luna（Haolo 代理）。
- 与原始协议模型（DeepSeek V4-Chat/V4-Pro、GLM5.2）不一致处，一律在变更日志记为偏差并说明影响。

## 变更日志
- [ ] deepseek-v4-flash 首次可用时间与端点：
- [ ] 充值后预算上限确认：
