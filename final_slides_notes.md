# Final Slides Notes

本文件对应 `final_slides.pdf` 的最新版讲稿口径，所有数字以当前仓库实际产物为准。

## 1. 题目与金融问题
- 题目：cninfo 监管公告单公告结构化抽取
- 问题：把监管类公告中的监管对象、问题点、监管动作与要求抽成结构化表，支持后续风险点统计与证据回溯
- 口径：单公告抽取，一条记录 = 一份公告；不做问询函—回复跨公告闭环匹配
- reply 公告只抽取当前回复文本中实际写出的事项，不判断是否逐项回应原函

## 2. 巨潮数据来源
- 数据源：cninfo 公开公告查询接口 + cninfo 公告 PDF
- 时间范围：2023-01-01 ~ 2026-05-11
- 市场：沪深两市
- 关键词与过滤：问询/关注函、回复、监管措施、警示函、整改报告；排除募集说明书、法律意见书、核查意见等附件型文本
- 当前样本：`metadata=120`，`pdf=120`

## 3. 难度档位
- 申请：标准档 1.0
- 理由：
  - 目标规模 120 份 PDF，落在 80–150 标准档区间
  - 包含 collect / download / parse / route / extract / validate / report 全流程
  - 有 section checking、evidence 校验、字段级人工评估
  - 未进入多文档 linking，因此不升级为闭环挑战档

## 4. 字段与 Schema
- 顶层字段：`doc_id / stock_code / stock_name / market / publish_date / announcement_title / doc_type / source`
- `targets[]`: `name / role / target_type / evidence`
- `issues[]`: `issue_type / issue_summary / is_violation_related / evidence`
- `actions[]`: `action_type / action_source_type / deadline / required_disclosure / evidence`
- 白名单：
  - `target_type`: `listed_company / controlling_shareholder / actual_controller / director / supervisor / executive / intermediary / subsidiary / shareholder_other / other`
  - `issue_type`: `information_disclosure / internal_control / fund_occupation / related_party_transaction / raised_funds / financial_irregularity / mna_restructuring / other`
  - `action_type`: `inquiry_reply_required / rectification_required / warning_letter / supervisory_talk / order_correction / disclosure_update_required / written_report_required / other`
  - `action_source_type`: `regulator_required / company_committed / unclear`
- null rule：没有证据就 `null` 或空列表，不做推断补全

## 5. PDF 解析与 Section 检查
- 解析工具：MinerU API，禁止本地 fallback
- 当前解析结果：`parsed_docs=116/120`，解析成功率 `96.7%`
- section routing：对每篇文档生成目标 section，并注入 `[Page N]`
- routing 线索：标题语境 + `现回复如下/经查/存在以下问题/决定对` 等锚点 + `一、二、三` 编号结构 + 问题列表/整改提示
- 当前 routing：`sections=116`
- section 检查统计：`found 201/232`，`ok 183/232`
- 长文本处理：reply/监管报告常很长，实际抽取前按页切片并优先保留前 5 个 page block，减少 LLM 超时；因为核心监管对象、问题和要求通常集中在前几页正文

## 6. Workflow
- `collect` -> `metadata.csv`
- `download` -> `data/pdf/*.pdf`
- `parse` -> `parsed_docs.jsonl`
- `route_sections` -> `sections.jsonl`
- `extract` -> `outputs/tmp/extracted.jsonl`
- `validate` -> `outputs/results/final_results.jsonl`
- `report` -> `outputs/reports/eval_report_final.md`
- 当前全量结果：`extract ok=115/116`，`final_results=115`，剩余 1 条为远端 LLM API 500 失败

## 7. Demo
- 固定样本：`doc_id=1225290815`
- 标题：`关于收到江苏证监局警示函的公告`
- 展示路径：
  - `metadata.csv` 中的 `doc_id / pdf_url`
  - `data/pdf/1225290815.pdf`
  - `sections.jsonl` 中带 `[Page 1]` 的正文
  - `final_results.jsonl` 中对应结构化结果
- 现场解释 3 个字段：
  - `regulator_name = 中国证券监督管理委员会江苏监管局`
  - `issues[0].issue_type = information_disclosure`
  - `actions[0].action_type = warning_letter`
  - `actions[0].action_source_type = regulator_required`

## 8. 评估结果
- 最终结果数：`115`
- 人工评估：20 篇 PDF，105 行字段级评估
- 准确率：
  - `doc_type`: `16/20 = 80.0%`
  - `regulator_name`: `14/14 = 100.0%`
  - `targets`: `21/27 = 77.8%`
  - `issues`: `17/20 = 85.0%`
  - `actions`: `21/24 = 87.5%`
  - `evidence_correct`: `74/85 = 87.1%`
- 主要错误：
  - `target_missing`: 6
  - `doc_type_wrong`: 4
  - `action_type_misclassified`: 2
  - `issue_summary_incorrect`: 2

## 9. 优化过程
- 先按老师意见把项目边界锁成单公告抽取
- schema 从粗粒度数组升级为带枚举和 evidence 的结构对象
- actions 增加 `action_source_type`，区分监管要求和公司承诺
- collect 增加标题过滤与附件排除词，减少“说明书/法律意见书”混入
- router 改为优先遵循标题推断 section 类型，避免 reply 文档被路由到监管措施 section
- extract 增加并发、超时重试、长文本截断和坏 item 清洗
- validator 增加枚举合法性和 evidence/page_no 硬校验
- 2026-06-08 新增优化：reply 路由跳过目录页；prompt 强化 listed_company / deadline / action_type 规则；validator 基于 evidence 修正明显错误的 action_type 并清除无证据支持的 deadline
- 2026-06-13 新增优化：对 10 条 extract 失败样本做 900 秒延时重试，补回 9 条；同时修正 validator 的 action_type 优先级，避免把公司整改承诺误修成警示函动作

## 10. Vibe Coding 反思
- 先与 AI 写清楚目标、输入输出、约束、done definition，再让 AI 落代码，而不是直接让 AI 自由生成
- 关键硬约束：
  - 只用 cninfo 元数据和 cninfo PDF
  - MinerU 失败就报错，不允许 fallback
  - evidence 必须来自输入原文，缺证据就 `null`
- AI 的作用：搭流水线骨架、生成 schema/prompt、补日志与报告
- 人的作用：锁边界、审查样本、核对 evidence、做字段级人工评估、修正口径
- 典型错误：
  - doc_type 把“延期回复公告”错分成 `attention_letter / inquiry_letter / other`
  - reply / 整改报告里漏抽 target 或 issue
  - deadline 误抽签字日期
