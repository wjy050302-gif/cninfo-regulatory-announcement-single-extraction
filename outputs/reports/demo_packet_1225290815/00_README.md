# Demo Packet for 1225290815

本文件夹按课堂 Demo 要求组织，建议现场按以下顺序打开：

1. `01_original_pdf_1225290815.pdf`
2. `02_metadata_row.csv`
3. `03_mineru_parsed_fragment.md`
4. `04_section_check_record.csv`
5. `05_section_record.json`
6. `06_llm_raw.json`
7. `07_extracted_record.json`
8. `08_validation_record.json`
9. `09_final_result.json`

## 这条样本最适合讲什么

- 它完整覆盖了 `PDF -> metadata -> MinerU -> section -> LLM -> validation -> final result`。
- 它还能展示 validator 如何作为质量闸门：只有 evidence 能在 routed section 中找到，字段才进入 final result。
- 最新规则下，validator 会修复仅空格差异导致的误判，但不会放过真正不在原文中的 evidence。

## 这条样本的验证结论

- Pydantic/validator 最终通过，进入 `final_results.jsonl`。
- 最新 `validation_errors.jsonl` 中没有该样本的修正记录，说明它的 evidence、page_no、枚举值和字段类型均通过校验。
- final result 保留了 3 个 targets：公司、时任董事长/总经理周文彬、时任董事会秘书曹晔。
- final result 保留了 3 个 actions：警示函、报送书面报告、公司整改承诺。
- `actions[1].deadline` 保留为原文写法：`收到本决定书之日起10 个工作日内`。

## 现场建议重点解释的 2 个字段

### regulator_name
- final value: `中国证券监督管理委员会江苏监管局`
- evidence_text: `中国证券监督管理委员会江苏监管局（以下简称江苏证监局）`
- page_no: 1

### issues[0]
- issue_type: `information_disclosure`
- issue_summary: `公司发生多起诉讼、仲裁案件，未按规定及时履行信息披露义务，也未在相应定期报告中披露。`
- evidence_text: `经查，2022 年3月至2025 年5月期间，江苏宝利国际投资股份有限公司（以下简称宝利国际或公司）发生多起诉讼、仲裁案件，公司未按规定及时履行信息披露义务，也未在相应的定期报告中披露。`
- page_no: 1

### actions[1]
- action_type: `written_report_required`
- action_source_type: `regulator_required`
- deadline: `收到本决定书之日起10 个工作日内`
- evidence_text: `你们应当于收到本决定书之日起10 个工作日内向我局报送书面报告。`
- page_no: 1

## 为什么这个样本适合讲 validator

这条样本里既有监管机关动作，也有公司后续承诺：
- `warning_letter` 对应监管机关“采取出具警示函”的处罚动作。
- `written_report_required` 对应监管机关“报送书面报告”的要求。
- `rectification_required` 对应公司“积极进行整改”的承诺。

最新版 validator 不再把“公司高度重视《警示函》中所指出的问题，积极进行整改”误修成 `warning_letter`，而是保留为 `rectification_required`。这说明 validator 的修正规则不仅检查格式，也会避免背景词压过真实动作词。

## section 检查记录要怎么讲

打开 `04_section_check_record.csv` 时，重点讲：
- 这里保留了 2 条 routing 尝试记录，分别对应 `inquiry_attention_body` 和 `regulatory_measure_body`。
- 两条都 `found=1`，说明这份公告同时命中了两套规则。
- 最终 `05_section_record.json` 里选中的是 `regulatory_measure_body`，因为该公告标题和项目规则更匹配监管措施口径。
- `match_strategy=anchor_regex`：说明是通过强锚点规则命中的，不是随机截取。
- `page_start=1, page_end=3`：说明最终正文范围覆盖了第 1 到 3 页。
- `char_len=1850`：说明送入 extract 的正文长度可控。
