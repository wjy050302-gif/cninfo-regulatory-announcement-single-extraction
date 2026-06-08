# Demo Script

本 demo 固定使用 `doc_id=1225290815`，目标是从 **cninfo 真实公告 PDF** 出发，展示“单公告结构化抽取 + evidence/page_no 证据链”。

## Demo 口径
- 一条记录 = 一份公告
- 不做“问询函—回复”跨公告闭环匹配
- reply 文档只抽取当前公告中明确出现的对象、问题、要求

## 固定样本
- `doc_id`: `1225290815`
- 标题: `关于收到江苏证监局警示函的公告`
- `doc_type`: `regulatory_measure`
- `pdf_url`: `http://static.cninfo.com.cn/finalpage/2026-05-11/1225290815.PDF`

## 演示路径
1. 在 `data/metadata/metadata.csv` 中搜索 `1225290815`，展示 `doc_id / pdf_url / stock_code / stock_name`
2. 打开 `data/pdf/1225290815.pdf`
3. 在 `data/parsed/sections.jsonl` 中搜索 `1225290815`，展示带 `[Page N]` 的 `section_text`
4. 在 `outputs/results/final_results.jsonl` 中搜索 `1225290815`，展示最终结构化记录
5. 现场解释 3 个字段的 `evidence_text` 和 `page_no`

## 建议现场讲解字段
### 1. regulator_name
- value: `中国证券监督管理委员会江苏监管局`
- evidence: `中国证券监督管理委员会江苏监管局（以下简称江苏证监局）`
- `page_no`: `1`

### 2. issues[0]
- `issue_type`: `information_disclosure`
- `issue_summary`: `未按规定及时履行信息披露义务，未在定期报告中披露多起诉讼仲裁案件`
- evidence: `公司未按规定及时履行信息披露义务，也未在相应的定期报告中披露`
- `page_no`: `1`

### 3. actions[0]
- `action_type`: `warning_letter`
- `deadline`: `10 个工作日内`
- evidence: `你们应当于收到本决定书之日起10 个工作日内向我局报送书面报告`
- `page_no`: `1`

## 建议现场讲解点
- metadata 可追溯：`doc_id`、`pdf_url` 来自 cninfo
- section 可复核：`[Page N]` 标记来自 MinerU + section router
- schema 有白名单：`target_type / issue_type / action_type`
- 不编造：字段无证据即 `null` 或空列表
- 评估可复核：该样本也在 `outputs/reports/manual_eval_filled_single_announcement.csv` 的 20 篇人工评估样本中
