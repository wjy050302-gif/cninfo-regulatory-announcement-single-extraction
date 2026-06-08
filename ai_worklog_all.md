# AI Worklog (All)

记录所有使用 AI 的时间点、输入/输出、以及对结果的验证方式。该文件需要随最终提交一并提供。

## Log Entries

### 2026-05-11
- 工作：确定选题（监管问询/关注函 + 监管措施结构化抽取）、固化 `topic_proposal.md`、搭建 `final_repo/` 骨架、实现 `collect/download/audit` 三步并用 cninfo 真实数据跑通。
- AI 用途：代码与文档初稿生成（pipeline 结构、csv 读写、cninfo client、下载器、审计报告模板）。
- 验证方式：
  - 用真实 cninfo 接口调用生成 `data/metadata/metadata.csv`。
  - 下载 `static.cninfo.com.cn` 的真实 PDF 并检查文件存在与大小。
  - 生成 `dataset_check_report.md` 与 `sample_run_log.jsonl`，人工抽查内容合理性。
- 备注：MinerU/LLM steps 已实现接口与约束，但需要用户本地配置真实 key 才能运行（无 key 时会硬失败，不做假输出）。

### 2026-05-12
- 工作：扩展 metadata 字段（doc_id/url/source/crawl_time 等）、实现按 (market, keyword) 覆盖采样到 120 篇、下载并缓存 120 份 PDF、完善 parse/route_sections/extract/validate/report 模块与文档（含 parse_manifest.csv 约束与 parse_check.md 模板），生成 `final_slides.pdf`。
- AI 用途：代码补全（parser/validator/section router）、文档措辞优化。
- 验证方式：
  - `collect/download/audit/report` 已用真实 cninfo 数据跑通并落盘 `sample_run_log.jsonl`。
  - `parse/extract` 在缺少 key 时会按要求直接失败（不产生伪造输出）。

### 2026-05-12（续 — 全量 pipeline 推进）
- 工作：parse 全量继续跑（目标 120 份，当前 38+ 份已完成，MinerU API 真实调用）；完成 parse_check.md 抽查（5 份样本，含长文档/短文档/监管措施/问询函类型）；计划全量 route_sections → extract → validate → report 推进。
- AI 用途：课程要求分析（读取全部 12 个章节内容，确认交付物清单与评分标准）、parse_check 抽查记录填写、pipeline 推进计划。
- 验证方式：
  - 已读取课程网站 Week 11–16 全部章节与 Lab，对照 spec 确认每个交付物。
  - parse_check.md 已基于真实 MinerU 解析结果填写 5 份抽查。
  - parse 进程使用真实 MINERU_API_KEY，失败记录在 parse_failures.jsonl。
- AI 出过的错：无重大错误；parse 超时属于 MinerU API 正常限制（大 PDF >100 页），已通过 fail cache 机制跳过。

### 2026-05-13
- 工作：确认 extract 全量完成（112 sections -> 104 ok / 8 failed），重新执行 validate/report 生成一致的 `final_results.jsonl=104`；补充代码审查记录；生成一份“基于证据链完整性”的人工评估填表（20 篇样本，104 行字段）。
- AI 用途：用脚本自动抽样、用 `pdftotext` 对照证据页做可定位性检查并生成 `manual_eval_filled_evidence_chain.csv`；更新 `eval_report_final.md` 的错误分布与 Top-5 样例。
- 验证方式：
  - 以 `sample_run_log.jsonl` 中 `extract done total=112 ok=104 failed=8` 为完成证据。
  - `final_results.jsonl` 行数与 ok 数一致（104）。
  - 人工评估文件中每条 evidence 的可定位性通过 `pdftotext` 的证据页检索得到（去空白归一化）。
- 备注：该“人工评估”更偏向证据链与页码可回溯性检查，不等价于对每个字段语义正确性的逐字人工判定；若需要更严格语义评估，应由学生再对照 PDF 原文逐条确认并修订 `is_correct/error_type/notes`。

### 2026-05-24
- 工作：根据老师反馈，将项目口径正式重构为“单公告抽取”，不做“问询函—回复”跨公告闭环；同步升级 schema、标题过滤规则、prompt、validator、reporter 和说明文档，并从 `collect` 开始重跑。
- AI 用途：辅助重写 `topic_proposal.md`、`crawl_spec.md`、`difficulty_declaration.md`、`workflow_design.md`、`README.md`、`prompt_final.md`；更新主评估口径为字段级人工评估，并将主评估文件切换为 `manual_eval_filled_single_announcement.csv`。
- 验证方式：
  - 新版 `collect` 已完成并生成 120 条 metadata。
  - `metadata.csv` 已验证 `doc_id` 唯一、`pdf_url` 唯一，且 `matched_search_keys` 已合并多关键词命中。
  - 提交清单与 sample check 文档已改为单公告口径，不再把旧 `manual_eval_filled_evidence_chain.csv` 当作主提交文件。
- 备注：`manual_eval_filled_evidence_chain.csv` 仅保留为历史辅助思路，不再作为本次老师反馈后的主评估交付物。
