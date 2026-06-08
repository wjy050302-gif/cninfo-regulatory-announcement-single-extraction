# Workflow Design

统一入口：`pipeline_run.py`，按 `--step` 分步运行。

项目口径：
- 单公告抽取
- 一条记录 = 一份公告
- 不做跨公告闭环匹配

## Steps

### 1) collect
- 输入：`configs/crawl_config.yaml`
- 输出：`data/metadata/metadata.csv`
- 逻辑：
  - 用多组关键词做召回
  - 用标题过滤规则决定是否入样本
  - 用标题规则生成 `title_rule_doc_type`
  - 合并同一公告的 `matched_search_keys`

### 2) download
- 输入：`metadata.csv`
- 输出：`data/pdf/<doc_id>.pdf`
- 约束：
  - 只允许下载 `static.cninfo.com.cn`
  - 回写 `download_status / local_pdf_path / error_message`

### 3) audit
- 输入：`metadata.csv` + 本地 PDF
- 输出：`outputs/reports/dataset_check_report.md`
- 检查：
  - 数量
  - 缺失
  - 重复
  - 下载状态

### 4) parse (MinerU)
- 输入：`metadata.csv`
- 输出：
  - `data/parsed/parsed_docs.jsonl`
  - `data/parsed/markdown/<doc_id>.md`
- 约束：
  - 必须使用 MinerU API
  - 缺少 `MINERU_API_KEY` 时直接失败，不允许 fallback

### 5) route_sections
- 输入：`parsed_docs.jsonl` + `configs/section_rules.yaml`
- 输出：
  - `data/parsed/sections.jsonl`
  - `outputs/reports/section_check_report.csv`
- 逻辑：
  - 只保留单公告正文中最相关的一段 section
  - 结合标题语境、`现回复如下/经查/存在以下问题/决定对` 等锚点、`一/二/三` 编号结构和问题列表做定位
  - 在输出中写入 `[Page N]` 标记，供 evidence / page_no 校验使用

### 6) extract
- 输入：`sections.jsonl` + `prompts/prompt_final.md`
- 输出：
  - `outputs/tmp/extracted.jsonl`
  - `outputs/tmp/llm_raw.jsonl`
  - `outputs/logs/extract_errors.jsonl`
- 逻辑：
  - 让 LLM 输出固定 schema
  - `target_type / issue_type / action_type / action_source_type` 只能使用白名单
  - reply 文档只抽取当前公告，不回指原问询函，也不判断是否逐项回应原函

### 7) validate
- 输入：`extracted.jsonl` + `sections.jsonl`
- 输出：
  - `outputs/results/final_results.jsonl`
  - `outputs/logs/validation_errors.jsonl`
- 校验：
  - `evidence_text` 必须是 `section_text` 子串
  - `page_no` 必须在 `[Page N]` 范围中
  - 枚举值必须在白名单中
  - 缺 evidence 的列表项直接丢弃并记录

### 8) report
- 输入：所有前序产物
- 输出：`outputs/reports/eval_report_final.md`
- 内容：
  - 数据质量
  - section 质量
  - 抽取质量
  - 证据质量
  - pipeline 稳定性
  - 字段级人工评估结果

## 人工评估设计
- 固定样本：20 篇 PDF
- 评估字段：
  - `doc_type`
  - `regulator_name`
  - `targets[i].name`
  - `targets[i].target_type`
  - `issues[i].issue_type`
  - `issues[i].issue_summary`
  - `actions[i].action_type`
  - `actions[i].action_source_type`
  - `actions[i].deadline`
- 错误类型：
  - `target_missing`
  - `issue_type_misclassified`
  - `issue_summary_incorrect`
  - `action_type_misclassified`
  - `action_source_type_wrong`
  - `action_requirement_confused`
  - `evidence_not_in_text`
  - `page_no_incorrect`
  - `doc_type_wrong`
