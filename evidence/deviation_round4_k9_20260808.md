# Deviation record: Round-4 family-level correction（2026-08-08, R15 后补正）

## 问题
- OSF 预注册（OSF_registration_P5_bc.md §9 Analysis Plan）规定：**Family-level BH and Holm over each k=9 family**。
- 首版分析器 `analyze_round4_20260808.py`（2026-08-08 首版）实现的是**逐格 BH（k=3 per model|bias|rate）**，未跑 Holm、未做 k=9 族级——与预声明不符（R15 复审指出）。

## 补正（2026-08-08，R15 后）
1. 分析器扩展：新增 **k=9 族级 BH + Holm**（每 model × bias 的 9 对比：3 rates × 3 pairs），paired t-tests on per-seed ΔΓ；输出进 `analyses/round4_validation_20260808.json`（`family_audit_k9_holm`）。
2. 正文 §6.7 以 **k=9 族级 Holm** 为准更新存活清单；k=3 逐格 BH 保留为敏感性分析（JSON 中 `family_audit_round4`）。
3. 论文正文与 OSF §12 的 H1 判定对齐：H1（k=9 族内至少一个对比经 BH 存活）在重建网格上……（见正文 Round-4 item）。

## k=9 族级结果（Holm 存活，2026-08-08 rerun）
- deepseek-v4-pro|length：p0.2（Append-RAG、RAG-Summ）、p0.5（全部 3 对）、p0.8（Append-RAG、RAG-Summ）
- deepseek-v4-pro|authority：p0.2（Append-RAG、RAG-Summ）、p0.8（RAG-Summ）
- deepseek-v4-flash|length：p0.8（全部 3 对）；p0.5（Append-Summ）仅 BH 存活
- deepseek-v4-flash|authority：无 Holm 存活

## 验收
- `python evidence/scripts/analyze_round4_20260808.py` rerun 输出 `family_audit_k9_holm` 与上述一致。


## 预声明关系澄清（2026-08-09，R16 复审后补充）
本包内**唯一的分析预声明是 OSF_registration_P5_bc.md §9 Analysis Plan**："Family-level BH and Holm over each k=9 family; paired t-tests on per-seed Delta Gamma; Kendall ...; reversal probability ..."。不存在独立的"混合效应模型 / omnibus gating"预声明文档；早期审稿中提到的混合模型/omnibus 表述来自审阅假设，未在本包任何预声明中出现。因此：
- 执行与报告均以 OSF k=9 族级 BH+Holm 为准（本 deviation 已补正）；
- 若评审要求混合效应/omnibus 作为敏感性，可后续补充，但不构成对预声明的偏差。
