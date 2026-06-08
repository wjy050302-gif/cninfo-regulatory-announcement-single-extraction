# AI Usage Statement

本项目允许使用 AI 辅助开发（Vibe Coding），但必须满足“可复现、可核对、不编造数据”的要求。

## 我们如何使用 AI
- 用于：代码骨架生成、函数/模块拆分建议、提示词初稿、文档模板初稿。
- 不用于：生成任何“看似真实”的公告内容、字段值或评估结论。

## 我们如何确保真实性与可复核
- 数据来源严格限定为 cninfo 公开接口与其公开 PDF。
- 抽取阶段执行 **Null rule**：无法从文本中确定的字段输出 `null`。
- 每个关键字段必须提供 `evidence_text`（来自输入 section_text 的原文子串），并尽量提供 `page_no`。
- `validate` step 对 `evidence_text` 做“必须为输入子串”的硬校验；不满足则置空或丢弃并记录在 `validation_errors.jsonl`。

## 密钥与隐私
- 不在仓库中保存任何真实 API key；仅提供 `.env.example`。
- 不提交 `.env` 文件。
