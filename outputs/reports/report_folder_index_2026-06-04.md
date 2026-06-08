# 汇报文件夹使用说明

桌面 `汇报` 文件夹按以下顺序使用：

## 01_项目文档
- 用来讲项目边界、选题、数据范围、难度档位
- 重点文件：
  - `topic_proposal.md`
  - `crawl_spec.md`
  - `difficulty_declaration.md`
  - `workflow_design.md`
  - `final_report.md`

## 02_展示材料
- 用来做正式汇报
- 重点文件：
  - `final_slides.pdf`
  - `final_slides_notes.md`
  - `presentation_brief_2026-06-04.md`
  - `demo_script.md`

## 03_核心结果
- 用来回答“数据是多少、结果是多少、评估怎么样”
- 重点文件：
  - `metadata.csv`
  - `final_results.jsonl`
  - `eval_report_final.md`
  - `section_check_report.csv`
  - `manual_eval_filled_single_announcement.csv`

## 04_证据链样例
- 用来现场演示从 PDF 到结构化结果的完整链路
- 固定样本：`doc_id=1225290815`

## 05_过程与问题
- 用来解释项目推进中遇到的问题、修改原因和处理方式
- 重点文件：
  - `optimization_log.md`
  - `conversation_and_issue_summary_2026-06-04.md`
  - `refactor_change_summary_2026-05-24.md`
  - `project_review_and_cleanup_2026-05-24.md`
  - `anchor_clue_validation_10docs*.md`

## 06_核心代码与配置
- 用来回答“系统怎么实现”
- 重点文件：
  - `pipeline_run.py`
  - `configs/*.yaml`
  - `src/schemas.py`
  - `src/section_router.py`
  - `src/extractor.py`
  - `src/validator.py`

## 07_AI使用记录
- 用来回答 AI 参与了什么、人是如何验证的
- 重点文件：
  - `ai_usage_statement.md`
  - `ai_worklog_all.md`
