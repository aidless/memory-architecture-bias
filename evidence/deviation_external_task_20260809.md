# Deviation: external-task replication model substitution (2026-08-09)

## Preregistered design
P5_EXTERNAL_TASK_PLAN_20260809.md (frozen 2026-08-09): external-task replication of the
architecture-order reversal (Summ vs Append gamma direction) on an open-ended text
generation task, model pair = **qwen3.7-plus** (cross-family R1-direction candidate,
Summ-lower in the main protocol) vs **deepseek-v4-flash** (reversal, Summ-higher).
Design: 2 models x 3 architectures x 10 seeds x 10 rounds x 2 arms; gamma = length
Wasserstein-1 with clean-arm normalization (identical to the P5 main protocol).

## Blocking condition (machine-verified)
At collection start (2026-08-09), every call to DashScope
(https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions) with the available
Qwen credential returned HTTP 400 with `"code": "Arrearage"` (account overdue) for
`qwen3.7-plus`, `qwen-plus`, and `qwen-max`; no other working Qwen credential or relay
exposing qwen models was available. This blocks the preregistered second model.

## Deviation applied
- qwen3.7-plus -> **gpt-5.4-mini** (OpenAI family) via the Youle relay
  (OPENAI_BASE_URL = https://aiapi.youleai.top/v1), chosen to preserve the cross-family
  R1-direction role (non-DeepSeek, non-v4 family).
- All other design elements unchanged: 3 architectures (Append-Only / Summarization /
  RAG+Filter), 10 seeds, 10 rounds, biased arm = "expand with more detail" note,
  gamma definition identical to prereg.
- Honest caveat: gpt-5.4-mini's direction was not known in advance from the main
  protocol (it was never run there); its observed direction on the external task is
  reported as measured, and the reversal-replication conclusion depends on the contrast
  actually observed (gpt Summ-lower vs v4-flash Summ-higher).

## Artifacts
- Script: evidence/scripts/run_p5_external_task_20260809.py
- Results: evidence/analyses/p5_external_task_20260809.json