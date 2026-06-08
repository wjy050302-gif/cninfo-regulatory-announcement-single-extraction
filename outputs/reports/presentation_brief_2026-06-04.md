# 汇报提纲（最新口径）

本文件用于配合 `final_slides.pdf` 和 `final_slides_notes.md` 做现场汇报。所有数字以当前仓库真实产物为准。

## 1. 题目与问题
- 题目：cninfo 监管公告单公告结构化抽取
- 核心问题：把监管类公告中的监管对象、问题点、监管动作与要求抽成结构化结果，并保留 evidence/page_no 证据链
- 项目边界：单公告抽取，一条记录 = 一份公告；不做问询函—回复跨公告闭环匹配

## 2. 数据来源与范围
- 数据源：cninfo 公开公告接口 + cninfo PDF
- 时间范围：2023-01-01 ~ 2026-05-11
- 市场：沪深两市
- 标题过滤：问询/关注函、回复、监管措施、警示函、整改报告
- 附件排除：募集说明书、法律意见书、核查意见等附件型文本

## 3. 当前真实样本量
- metadata：120
- 已下载 PDF：120
- MinerU 成功解析：116
- section routing 成功：116
- 最终结构化结果：116

说明：
- `parse` 少 4 份，是因为 MinerU 在 `420s` 内超时
- `extract` 在 2026-06-08 新一轮重跑中先完成 `112/116`
- 对 4 条失败样本做 `600s` 延时重试后，4 条全部补回

## 4. Schema 与约束
- 顶层字段：`doc_id / stock_code / stock_name / market / publish_date / announcement_title / doc_type / source`
- `targets[]`：`name / role / target_type / evidence`
- `issues[]`：`issue_type / issue_summary / is_violation_related / evidence`
- `actions[]`：`action_type / action_source_type / deadline / required_disclosure / evidence`
- `action_source_type`：`regulator_required / company_committed / unclear`
- null rule：无证据不补全，直接 `null` 或空列表

## 5. PDF 处理逻辑
- 先完整下载 PDF
- 再用 MinerU 完整解析整份 PDF
- 再做 section routing，只保留最相关正文
- 在送给 LLM 前，对 routed section 做长度控制：
  - 前 5 个 `[Page N]` block
  - 最多 20000 字符

原因：
- reply/整改类公告可能很长
- LLM 长文本超时风险高
- 监管对象、问题点、要求通常集中在正文前段

## 6. Workflow
- `collect` -> `data/metadata/metadata.csv`
- `download` -> `data/pdf/*.pdf`
- `parse` -> `data/parsed/parsed_docs.jsonl`
- `route_sections` -> `data/parsed/sections.jsonl`
- `extract` -> `outputs/tmp/extracted.jsonl`
- `validate` -> `outputs/results/final_results.jsonl`
- `report` -> `outputs/reports/eval_report_final.md`

## 7. Demo 样本
- 固定 `doc_id=1225290815`
- 标题：`关于收到江苏证监局警示函的公告`
- 路径：
  - `data/metadata/metadata.csv`
  - `data/pdf/1225290815.pdf`
  - `data/parsed/sections.jsonl`
  - `outputs/results/final_results.jsonl`

## 8. 当前评估口径
- 人工评估：20 篇 PDF
- 主文件：`outputs/reports/manual_eval_filled_single_announcement.csv`
- 主报告：`outputs/reports/eval_report_final.md`
- 评估重点：`doc_type / regulator_name / targets / issues / actions / evidence`

## 9. 需要现场讲清楚的几个点
- 为什么是单公告抽取，而不是闭环任务
- 为什么保留 reply 公告，但不做跨公告匹配
- 为什么 actions 需要 `action_source_type`
- 为什么 parse 只有 116，final results 是 116
- 为什么证据必须来自 routed section 原文

## 10. 当前最终状态
- 当前可提交结果：116 条
- 提交目录已准备：桌面 `提交`
- 汇报目录已准备：桌面 `汇报`
