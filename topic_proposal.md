# Topic Proposal

## 项目题目
基于巨潮资讯网公告的监管问询/关注函、回复公告与监管措施单公告结构化抽取（含证据链与页码）

## 项目范围（先锁边界）
本项目正式锁定为 **单公告抽取**：

- 一条记录 = 一份公告 PDF（`doc_id = announcementId`）
- 只抽取当前公告中明确出现的监管对象、问题点、监管动作/要求
- **不做** “问询函—回复” 跨公告闭环匹配，不判断公司是否逐项回应原函

说明：
- `reply` 类公告仍保留在范围内，但只作为单篇公告抽取
- 对于回复公告，只抽取该回复文本中实际出现的问题点、回复要求或整改动作；不回推原始问询函的完整问题列表

## 金融问题
监管问询/关注函与行政监管措施是上市公司合规风险和信息披露风险的重要信号。本项目希望把公告中的核心监管信息结构化，形成可统计、可检索、可复核的事件台账，用于：

- 统计公司被监管关注的主要风险类型
- 比较不同公司/不同时段的监管处置特征
- 为后续风控/投研提供“可追溯到原文证据”的底层结构化数据

## 巨潮数据来源
仅使用巨潮资讯网（cninfo）公开可访问数据：

- 公告检索接口：`https://www.cninfo.com.cn/new/hisAnnouncement/query`
- 公告 PDF：接口返回的 `adjunctUrl` 组合为直链 `http://static.cninfo.com.cn/<adjunctUrl>`

真实性与合规约束：

- 不绕过登录、验证码或访问限制
- 不使用任何非 cninfo 的第三方数据源
- 字段无法从公告文本直接支持时输出 `null`
- 每个关键字段必须带 `evidence_text`，且 `evidence_text` 必须来自解析文本原文片段

## 数据范围与过滤规则

### 固定范围
- 市场：沪深两市（`column=sse/szse`）
- 时间：2023-01-01 ~ 2026-05-11
- 目标数据量：80–150 份 PDF（当前锁定 `max_records=120`）

### 查询关键词（用于召回）
- 问询/关注函正文：`关注函`、`问询函`、`审核问询`、`年报问询`
- 回复类公告：`回复`、`回函`、`延期回复`
- 监管措施类公告：`行政监管措施`、`监管措施决定书`、`警示函`、`责令改正`、`监管谈话`、`整改报告`

### 标题过滤规则（用于最终入样本）
- 标题命中以下任一组才保留：
  - 问询/关注函组：`关注函`、`问询函`、`审核问询`、`年报问询`
  - 回复组：`回复`、`回函`、`延期回复`
  - 监管措施组：`行政监管措施`、`监管措施决定书`、`警示函`、`责令改正`、`监管谈话`、`整改报告`
- 标题包含以下词通常排除：
  - `募集说明书`
  - `发行保荐书`
  - `上市保荐书`
  - `法律意见书`
  - `评级报告`
  - `摘要`
  - `英文版`
  - `补充法律意见书`
- 但如果标题同时命中“回复/整改/监管措施”语境，则保留

### 实质性正文筛选（避免偏题附件）
即使标题命中问询/回复关键词，下列“低信息量更新公告”或“中介机构单独附件”也不纳入主样本：

- `提示性公告`
- `申请文件更新`
- `募集说明书`
- `法律意见书`
- `专项说明`
- `核查意见`
- `律师事务所`
- `会计师事务所`

这样做的目的，是把样本尽量收敛到“上市公司监管问询/关注函正文、公司正式回复正文、监管措施正文”，避免被募集说明书更新提示、律师意见书、会计师专项说明这类附件型公告带偏。

### 去重规则
- 先按 `doc_id` 去重
- 再按 `pdf_url` 去重
- 同一公告若因多个关键词命中，只保留一条 metadata，并合并 `matched_search_keys`

## 文书类型（doc_type）
顶层 `doc_type` 只允许以下枚举：

- `attention_letter`
- `inquiry_letter`
- `regulatory_measure`
- `reply`
- `other`

优先级规则：
`regulatory_measure > reply > attention_letter > inquiry_letter > other`

## 目标字段与 Schema

### 顶层字段
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| doc_id | str | 是 | cninfo 公告唯一 ID（即 announcementId） |
| stock_code | str | 是 | 证券代码 |
| stock_name | str | 是 | 证券简称 |
| market | str | 是 | `sse` / `szse` |
| publish_date | str | 是 | 公告日期 |
| announcement_title | str | 是 | 公告标题 |
| doc_type | enum | 是 | 文书类型 |
| regulator_name | object/null | 否 | 监管机构，带证据 |
| targets | list | 否 | 监管对象列表 |
| issues | list | 否 | 问题点列表 |
| actions | list | 否 | 措施/要求列表 |
| source | object | 是 | 可追溯 URL / PDF URL |

### `targets[]`
每个对象固定为：

- `name`: 监管对象名称
- `role`: 公告中出现的角色描述（可空）
- `target_type`: 枚举
- `evidence`: `{evidence_text, page_no}`

`target_type` 白名单：
- `listed_company`
- `controlling_shareholder`
- `actual_controller`
- `director`
- `supervisor`
- `executive`
- `intermediary`
- `subsidiary`
- `shareholder_other`
- `other`

### `issues[]`
每个对象固定为：

- `issue_type`: 枚举
- `issue_summary`: 公告原文支持的问题摘要
- `is_violation_related`: `true/false/null`
- `evidence`: `{evidence_text, page_no}`

`issue_type` 白名单：
- `information_disclosure`
- `internal_control`
- `fund_occupation`
- `related_party_transaction`
- `raised_funds`
- `financial_irregularity`
- `mna_restructuring`
- `other`

### `actions[]`
每个对象固定为：

- `action_type`: 枚举
- `action_source_type`: 枚举，用于区分“监管要求”与“公司承诺/已采取动作”
- `deadline`: 可空
- `required_disclosure`: `true/false/null`
- `evidence`: `{evidence_text, page_no}`

`action_type` 白名单：
- `inquiry_reply_required`
- `rectification_required`
- `warning_letter`
- `supervisory_talk`
- `order_correction`
- `disclosure_update_required`
- `written_report_required`
- `other`

`action_source_type` 白名单：
- `regulator_required`
- `company_committed`
- `unclear`

解释：
- `regulator_required`：监管机关、交易所、问询函正文明确提出的要求
- `company_committed`：公司、中介机构或相关主体在当前公告中明确写出的已采取/承诺采取的整改动作
- `unclear`：仅从当前公告文本无法清晰判断动作来源

## Null Rule 与证据规则
- 任何字段如果当前公告文本无法直接支持，一律输出 `null` 或空列表
- 不允许把推断结果写进自由文本字段
- 每个非空关键字段都必须有 `evidence_text`
- `evidence_text` 必须是输入 section 文本的原文子串
- `page_no` 若能从 `[Page N]` 定位则填写，否则为 `null`

## Section Routing 规则
监管函、回复公告和监管措施公告不像年报那样有稳定目录，因此 section routing 不依赖固定章节名，而是结合以下线索定位正文：

- 标题语境：先按标题区分问询/关注函正文、回复公告、监管措施公告
- 段落锚点：如 `现回复如下`、`回复如下`、`经查`、`存在以下问题`、`决定对`、`整改措施`
- 编号结构：如 `一、二、三`、`问题一/问题二`、`事项一/事项二`
- 要求性句式：如 `请你公司`、`请发行人`、`请保荐机构`、`请书面说明`
- 风险/整改提示：如 `整改情况`、`整改报告`、`风险提示`

如果文本没有标准目录，则优先保留最早出现的高信息密度正文页，并用页扩展策略补足前后相邻页，再做 section checking。

## 人工评估方案
- 固定抽样：15–20 份 PDF（当前执行口径为 20 份）
- 标量字段：`doc_type`、`regulator_name` 按 exact-match accuracy 评估
- 列表字段：`targets`、`issues`、`actions` 按 item-level 人工核对
  - `targets` 关注 `name / target_type`
  - `issues` 关注 `issue_type / issue_summary`
  - `actions` 关注 `action_type / action_source_type / deadline`
- 统计方式：
  - 字段级准确率
  - 列表项错误类型分布：`漏抽 / 误抽 / 类型错分 / evidence 不匹配 / page_no 错误`

## 示例公告（真实 cninfo 样本）
| announcementId | 公司 | 代码 | 标题 | 日期 | PDF URL |
|---|---|---|---|---|---|
| 1225282699 | *ST惠程 | 002168 | 关于对深圳证券交易所对重庆惠程信息科技股份有限公司2025年年报问询函的回复 | 2026-05-07 | http://static.cninfo.com.cn/finalpage/2026-05-08/1225282699.PDF |
| 1225274045 | *ST八钢 | 600581 | 关于最近五年被证券监管部门和交易所采取处罚或监管措施及整改情况的公告 | 2026-04-30 | http://static.cninfo.com.cn/finalpage/2026-05-01/1225274045.PDF |
| 1225190456 | *ST赛隆 | 002898 | 关于延期回复深圳证券交易所关注函的公告 | 2026-04-24 | http://static.cninfo.com.cn/finalpage/2026-04-25/1225190456.PDF |

## 最终输出
- `data/metadata/metadata.csv`
- `data/pdf/*.pdf`
- `data/parsed/parsed_docs.jsonl`
- `data/parsed/sections.jsonl`
- `outputs/results/final_results.jsonl`
- `outputs/reports/section_check_report.csv`
- `outputs/reports/eval_report_final.md`

## 难度档位
- 申请档位：标准档
- 系数：1.0

理由：
- 覆盖问询/关注函、回复、监管措施三类单公告文本
- 需要 PDF 解析、section routing、结构化列表字段、证据链校验、字段级人工评估
- 但不涉及跨公告 linking，因此仍维持标准档，不升级挑战档
