# Parse Check

> 该表用于 Week13 要求的"MinerU 解析抽样检查"。每次 parse 至少抽查 3–5 份 PDF，并记录问题与是否需要修正规则/更换样本。

## 抽查样本 1：1225286933
- doc_id: 1225286933
- title: 关于西安旅游股份有限公司申请向特定对象发行股票的审核问询函的回复报告
- pdf_path: data/pdf/1225286933.pdf
- markdown_path: data/parsed/markdown/1225286933.md
- parser: mineru
- status: success
- error_message: (无)

### Page Check
- 页码是否保留（pages[].page_no）：是，共110页，page_no从1到110连续
- 是否有乱码：否，中文/数字/标点均正常
- 表格是否完整（如有）：表格内容以文本形式保留，部分复杂表格有合并单元格缺失但不影响主体内容
- 标题层级是否合理：是，章节标题清晰（"一、"、"二、"等）
- 目录/页眉页脚是否混入正文：少量页眉（如证券代码/简称）混入，但不影响主体抽取

### Target Content
- 目标内容是否出现：是，审核问询函回复的主体内容完整（涉及公司经营风险、财务状况等）
- 关键字段是否能在解析文本中找到：是（深交所、西部证券、ST西旅等）
- 是否需要人工修正：否

---

## 抽查样本 2：1225284585
- doc_id: 1225284585
- title: 西安爱科赛博电气股份有限公司关于对陕西证监局行政监管措施决定书的整改报告
- pdf_path: data/pdf/1225284585.pdf
- markdown_path: data/parsed/markdown/1225284585.md
- parser: mineru
- status: success
- error_message: (无)

### Page Check
- 页码是否保留（pages[].page_no）：是，共5页
- 是否有乱码：否
- 表格是否完整（如有）：无复杂表格
- 标题层级是否合理：是
- 目录/页眉页脚是否混入正文：无

### Target Content
- 目标内容是否出现：是，监管措施整改报告的主体内容完整（涉及财务核算不规范、关联交易披露问题等）
- 关键字段是否能在解析文本中找到：是（陕西证监局、行政监管措施、整改等关键词明确）
- 是否需要人工修正：否，这是典型的监管措施类公告，内容质量好

---

## 抽查样本 3：1225282699
- doc_id: 1225282699
- title: 关于对深圳证券交易所对重庆惠程信息科技股份有限公司2025年年报问询函的回复
- pdf_path: data/pdf/1225282699.pdf
- markdown_path: data/parsed/markdown/1225282699.md
- parser: mineru
- status: success
- error_message: (无)

### Page Check
- 页码是否保留（pages[].page_no）：是，共33页
- 是否有乱码：否
- 表格是否完整（如有）：部分表格以文本形式保留
- 标题层级是否合理：是
- 目录/页眉页脚是否混入正文：少量

### Target Content
- 目标内容是否出现：是，深交所年报问询函回复完整（涉及债务豁免、净资产转正、退市风险等）
- 关键字段是否能在解析文本中找到：是（深交所、问询函、回复等关键词明确）
- 是否需要人工修正：否

---

## 抽查样本 4：1225286077
- doc_id: 1225286077
- title: 关于最近五年被证券监管部门和交易所采取监管措施及整改情况的公告
- pdf_path: data/pdf/1225286077.pdf
- markdown_path: data/parsed/markdown/1225286077.md
- parser: mineru
- status: success
- error_message: (无)

### Page Check
- 页码是否保留（pages[].page_no）：是，共1页
- 是否有乱码：否
- 表格是否完整（如有）：无
- 标题层级是否合理：是
- 目录/页眉页脚是否混入正文：无

### Target Content
- 目标内容是否出现：是，但内容极短（仅声明"被采取监管措施"的概括性说明）
- 关键字段是否能在解析文本中找到：部分（有监管措施关键词但细节不充分）
- 是否需要人工修正：不需要修正解析，但此文档在 section routing 时可能因太短被标记为 too_short

---

## 抽查样本 5：1225282701
- doc_id: 1225282701
- title: 独立董事关于对深圳证券交易所2025年年报问询函回复的意见
- pdf_path: data/pdf/1225282701.pdf
- markdown_path: data/parsed/markdown/1225282701.md
- parser: mineru
- status: success
- error_message: (无)

### Page Check
- 页码是否保留（pages[].page_no）：是，共24页
- 是否有乱码：否
- 表格是否完整（如有）：部分表格保留
- 标题层级是否合理：是
- 目录/页眉页脚是否混入正文：少量

### Target Content
- 目标内容是否出现：是，独立董事对问询函回复的意见（涉及退市风险警示、净资产变化、关联交易等）
- 关键字段是否能在解析文本中找到：是
- 是否需要人工修正：否

---

## 总体评估
- 5份样本中解析质量均良好，无乱码、页码保留正确
- 短文档（1页）内容有限但解析本身无误
- 长文档（100+页）可能包含较多页眉页脚噪声，section routing 已配置 exclude_regex 过滤
- 解析失败的文档（4份timeout/4份skip_failed）主要是超大PDF（>100页）导致MinerU超时，这是预期行为
