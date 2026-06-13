# Eval Report (Final) (2026-06-13T01:16:37Z)

本报告覆盖课程要求五类指标：数据质量、Section 质量、抽取质量、证据质量、Pipeline 稳定性。

## 1. 数据质量 (Data Quality)
- `metadata.csv` 记录数: **120**
- 数据来源: cninfo 巨潮资讯网公开公告查询接口
- 时间范围: 2023-01-01 ~ 2026-05-11
- 市场: 沪深两市（sse + szse）
- 项目口径: 单公告抽取（不做问询函—回复跨公告闭环匹配）
- 查询关键词按标题规则扩展到问询/关注函、回复、监管措施、整改报告等
- 难度档位: 标准档 1.0（目标 120 份 PDF）
- audit report: `outputs/reports/dataset_check_report.md`

## 2. PDF 解析 (MinerU)
- parsed docs (jsonl): **116** (`data/parsed/parsed_docs.jsonl`)
- parse 抽查: 见 `outputs/reports/parse_check.md`（至少 5 份样本）
- 强约束: 无真实 `MINERU_API_KEY` 或解析为空时直接退出，不允许 fallback

- 解析成功率: 96.7%（116/120）

## 3. Section Routing & Checking
- section check report: `outputs/reports/section_check_report.csv`
- 处理文档数: **116**（共 232 行 routing 记录）
- found rate: 86.6%（201/232）
- not_found rate: 13.4%（31/232）
- too_short rate: 6.9%（16/232）
- ok rate: 79.7%（185/232）

## 4. 抽取质量 (Extraction Quality)
- extracted (Pydantic 通过) 记录: **115** (`outputs/tmp/extracted.jsonl`)
- final results (经证据校验): **115** (`outputs/results/final_results.jsonl`)
- validation errors/repairs: **39** (`outputs/logs/validation_errors.jsonl`)

### doc_type 分布
- `reply`: 57
- `regulatory_measure`: 56
- `other`: 1
- `attention_letter`: 1

### 文档级字段填充率
| 字段 | 填充数 | 总数 | 填充率 |
|---|---|---|---|
| `regulator_name` | 87 | 115 | 75.7% |
| `targets` | 114 | 115 | 99.1% |
| `issues` | 102 | 115 | 88.7% |
| `actions` | 110 | 115 | 95.7% |

### 结构化列表项统计
- targets item 总数: **295**
- issues item 总数: **198**
- actions item 总数: **305**

### target_type 分布
- `listed_company`: 111
- `executive`: 59
- `other`: 33
- `director`: 31
- `intermediary`: 18
- `shareholder_other`: 15
- `actual_controller`: 12
- `controlling_shareholder`: 12
- `subsidiary`: 4

### issue_type 分布
- `financial_irregularity`: 53
- `information_disclosure`: 53
- `internal_control`: 32
- `related_party_transaction`: 16
- `other`: 13
- `raised_funds`: 12
- `fund_occupation`: 10
- `mna_restructuring`: 9

### action_type 分布
- `rectification_required`: 101
- `inquiry_reply_required`: 63
- `warning_letter`: 37
- `order_correction`: 33
- `other`: 32
- `written_report_required`: 18
- `supervisory_talk`: 12
- `disclosure_update_required`: 9

### action_source_type 分布
- `regulator_required`: 202
- `company_committed`: 103

## 5. 证据质量 (Evidence Quality)
- evidence 总数: **885**
- page_no 覆盖率: 100.0%（885/885）
- 硬校验: evidence_text 必须是输入 section_text 的子串，否则置 null 或丢弃

## 6. Pipeline 稳定性
| Step | Info | Error | Warn |
|---|---|---|---|
| `audit` | 1 | 0 | 0 |
| `collect` | 2 | 0 | 0 |
| `download` | 2 | 0 | 0 |
| `extract` | 18 | 152 | 0 |
| `extract_retry` | 5 | 1 | 0 |
| `extract_retry_merge` | 1 | 0 | 0 |
| `parse` | 230 | 4 | 0 |
| `report` | 16 | 0 | 0 |
| `route_sections` | 4 | 0 | 0 |
| `validate` | 14 | 0 | 0 |

## 7. 人工评估 (Manual Evaluation)
- 主评估口径: 字段级人工评估（单公告抽取）
- 标注模板: `outputs/reports/manual_eval_template.csv`
- 标量字段 `doc_type / regulator_name` 按 exact-match accuracy 评估
- 列表字段 `targets / issues / actions` 按 item-level 人工核对，重点统计漏抽、误抽、类型错分与 evidence/page_no 错误
- 已填写评估表: `outputs/reports/manual_eval_filled_single_announcement.csv`
- 样本数: **20** 篇 PDF
- 字段评估总行数: **105**

| 评估维度 | 正确数 | 总数 | 准确率 |
|---|---|---|---|
| `doc_type` | 16 | 20 | 80.0% |
| `regulator_name` | 14 | 14 | 100.0% |
| `targets` | 21 | 27 | 77.8% |
| `issues` | 17 | 20 | 85.0% |
| `actions` | 21 | 24 | 87.5% |

- evidence_correct: 74/85 = 87.1%
- 评估字段: doc_type / regulator_name / targets[i].name / targets[i].target_type / issues[i].issue_type / issues[i].issue_summary / actions[i].action_type / actions[i].action_source_type / actions[i].deadline

## 8. 错误分析 (Error Analysis)
### 错误类型分布
- `target_missing`: 6
- `doc_type_wrong`: 4
- `action_type_misclassified`: 2
- `issue_summary_incorrect`: 2
- `action_requirement_confused`: 1
- `issue_type_misclassified`: 1

### Top-5 代表性错误
- `1225286595` targets[0].name -> `target_missing` (第2页已出现上市公司名称，未抽出监管对象)
- `1225286595` targets[0].target_type -> `target_missing` (应识别为上市公司对象)
- `1225291273` targets[0].name -> `target_missing` (标题已明确上市公司名称)
- `1225291273` targets[0].target_type -> `target_missing` (应识别为上市公司对象)
- `1225285619` actions[0].deadline -> `action_requirement_confused` (签字日期被误当作监管/回复截止时间)
- prompt v1 → prompt final 的关键修改点已记录在 `prompts/prompt_final.md`

