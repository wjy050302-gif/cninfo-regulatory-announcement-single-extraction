# 第15页评估要求自检（2026-06-08）

对照课程页面：<https://ml-nlp.netlify.app/15_evaluation_prompt_skills_optimization>

## 结论

当前仓库在“人工评估、错误分析、五类指标、自我修复记录”方面**已达到可交付状态**。  
此前发现的 3 个正式交付缺口与 2 个一致性缺口，现已完成修复。

## 已满足

### 1. 人工评估数量与粒度
- 已有 20 篇 PDF 的字段级人工评估
- 文件：`outputs/reports/manual_eval_filled_single_announcement.csv`
- 评估维度覆盖：
  - `doc_type`
  - `regulator_name`
  - `targets`
  - `issues`
  - `actions`

### 2. 五类指标报告
- `outputs/reports/eval_report_final.md` 已覆盖：
  - Data Quality
  - PDF/Parse
  - Section Routing & Checking
  - Extraction Quality
  - Evidence Quality
  - Pipeline Stability

### 3. 错误分类与代表样例
- `outputs/reports/eval_report_final.md` 已包含：
  - 错误类型分布
  - Top-5 代表性错误

### 4. 真实性约束
- 当前报告与结果都保持真实口径：
  - `parsed_docs=116`
  - `final_results=116`
  - `extract` 失败样本已通过定向延时重试全部补回
  - `parse` 仍剩 4 条失败

## 已修复的交付缺口

### 1. `optimization_log.md` 已补齐
- 文件：`optimization_log.md`
- 内容：独立记录 prompt / routing / validator / workflow 的优化历史，并单列 2026-06-08 错误驱动优化

### 2. `final_report.md` 已补齐
- 文件：`final_report.md`
- 内容：整合项目目标、方法、当前真实结果、评估结果、限制与复现命令

### 3. `final_slides.pdf` 已更新
- 现状：
  - Slide 6 已更新为 `extract ok=116/116`、`final_results=116`
  - Slide 8 已更新为最终结果 `116`
  - Slide 4 已明确展示 `action_source_type`

### 4. `README.md` 已同步最新数字
- 文件：`README.md:71-80`
- 现状：
  - `final_results.jsonl` 已更新为 `116`
  - 新增 `optimization_log.md` 与 `final_report.md` 的说明

### 5. `final_slides_notes.md` 已同步最新口径
- 文件：`final_slides_notes.md`
- 现状：
  - 已更新 `extract ok=116/116`
  - 已更新 `final_results=116`
  - 已补入 2026-06-08 优化内容

## 可接受但建议统一的点

### LOW 1. `manual_eval_template.csv` 的错误类型枚举是项目定制版
- 文件：`outputs/reports/manual_eval_template.csv:6`
- 现状：
  - 采用 `target_missing / issue_type_misclassified / action_requirement_confused ...`
- 判断：
  - 这不是错误，且更适合你的项目
  - 但如果想严格贴近课程页面，可在报告中补一句：
    - 这是在课程建议基础上的项目化细分枚举

## 当前真实状态

- `metadata.csv`: 120
- `parsed_docs.jsonl`: 116
- `final_results.jsonl`: 116
- `extract` 延时重试：4/4 成功

## 当前建议

1. 如果要继续提升覆盖率，下一步只需要考虑 4 份 MinerU `parse` 超时样本
2. 本轮 `extract` 优化效果已实际落地，不需要再重跑 MinerU
