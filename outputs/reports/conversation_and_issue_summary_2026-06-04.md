# 对话过程中的主要问题、发现与处理

本文件总结本次项目推进过程中，在对话中明确过的主要问题、已确认的事实、处理方法，以及当前状态。

## 1. 项目边界问题
### 发现
- 初始题目表述容易让人误以为项目要做“问询函—回复”跨公告闭环匹配
- 但现有代码和数据流实际上是一条记录对应一份公告，属于单公告抽取

### 处理
- 明确把项目边界锁定为：单公告抽取，不做闭环匹配
- `reply` 类公告保留在样本里，但只抽取该回复公告文本本身，不回指原函
- 同步修改：
  - `topic_proposal.md`
  - `crawl_spec.md`
  - `workflow_design.md`
  - `README.md`
  - `prompt_final.md`

### 结果
- 项目口径与代码实现一致
- 现场答辩时可以清楚解释为什么保留 reply 样本但不做闭环

## 2. Schema 不够细、后续统计不稳定
### 发现
- 早期 `targets / issues / actions` 粒度过粗
- 没有白名单时，模型会输出很多近义标签，不利于统计

### 处理
- 升级 schema：
  - `targets[]`: `name / role / target_type / evidence`
  - `issues[]`: `issue_type / issue_summary / is_violation_related / evidence`
  - `actions[]`: `action_type / action_source_type / deadline / required_disclosure / evidence`
- 增加白名单：
  - `target_type`
  - `issue_type`
  - `action_type`
  - `action_source_type`
- 在 `validator` 中增加枚举合法性校验

### 结果
- 结果更适合做结构化统计
- 字段口径更稳定

## 3. 样本过滤不够严格
### 发现
- 仅靠简单关键词，容易把募集说明书、法律意见书、核查意见等附件型文档混入样本

### 处理
- 在 `crawl_config.yaml` 和 `collector.py` 中增加：
  - 标题包含词
  - 标题排除词
  - 标题优先级
  - 去重规则

### 结果
- 样本边界更接近监管正文公告
- 与项目目标一致性更强

## 4. 旧产物残留与覆盖问题
### 发现
- 多次重跑 `extract` 时，旧的 `extracted.jsonl / llm_raw.jsonl / final_results.jsonl` 可能被覆盖
- `data/parsed/markdown/` 和 `zip/` 里曾经存在旧缓存残留

### 处理
- 先做备份，再清理孤儿 parsed 文件
- 把当前有效样本和桌面提交目录对齐
- 对补跑任务采用单独输出文件，再并回主结果，避免直接覆盖

### 结果
- 当前主结果稳定
- 工作目录与桌面提交目录保持同版

## 5. PDF 很长，LLM 超时严重
### 发现
- reply/整改类公告页数多、表格多，整段送入 LLM 时容易超时
- 超时会导致 `extract` 速度慢，且失败率高

### 处理
- 完整下载、完整 MinerU 解析整份 PDF
- 先做 section routing，找最相关正文
- 再对 routed section 做输入长度控制：
  - 只保留前 5 个 `[Page N]` block
  - 最多 20000 字符

### 结果
- 显著降低了长文本导致的超时风险
- 同时保留了真实证据链

## 6. section routing 需要可解释的锚点
### 发现
- reply 公告和监管措施公告不像年报那样有固定目录
- 仅用简单页面匹配不够稳定

### 处理
- 在 routing 中引入线索：
  - `现回复如下`
  - `经查`
  - `存在以下问题`
  - `决定对`
  - `一、二、三`
  - `问题一/问题二`
- 另外做了 10 份样本的 anchor clue 验证报告

### 结果
- routed section 中可以重新找到大部分抽取字段的 evidence
- 这组线索被证明对当前项目有效

## 7. parse 为什么只有 116
### 发现
- metadata 是 120
- 但 `parsed_docs.jsonl` 只有 116

### 确认结果
- 不是漏抓样本
- 是 4 份文档在 MinerU `parse` 阶段超时失败
- 4 个 `doc_id`：
  - `1225286613`
  - `1225284401`
  - `1225282404`
  - `1225274900`

### 进一步尝试
- 单独把 MinerU 等待上限从 `420s` 提高到 `1200s`
- 只重跑这 4 份中的第一份进行验证

### 结果
- 第一份仍然在 `1200s` 后超时
- 说明这类文档的失败不是简单的“等久一点就一定成功”
- 因此当前稳定口径仍然是 `parse=116`

## 8. extract 原始失败 8 条
### 发现
- `extract` 最初为 `116 -> ok 108 / failed 8`
- 失败类型主要有两类：
  - `Read timed out (300s)`
  - `failed to parse JSON object from LLM output`

### 处理
- 单独抽出这 8 个 `doc_id`
- 把超时提高到 `600s`
- 单线程、2 次重试，单独补跑，不覆盖主结果

### 结果
- 8 条中成功补回 7 条
- 仅剩 1 条失败：
  - `1224636453`
  - 原因：`failed to parse JSON object from LLM output`

### 最终影响
- `final_results.jsonl` 从 `108` 提升到 `116`

## 9. validate 与 evidence 校验
### 发现
- 即使抽取成功，也可能存在 evidence 不规范、page_no 不规范、坏 item 等问题

### 处理
- `validate` 增加硬校验：
  - `evidence_text` 必须是 routed section 原文子串
  - `page_no` 必须能和 `[Page N]` 对应
  - 枚举字段必须合法

### 结果
- 当前 `validate` 对 116 条记录全部通过
- 并做了 60 处修复，但没有丢记录

## 10. 提交物整理与安全问题
### 发现
- 提交目录必须不含真实 `.env`
- 桌面上曾有旧版提交副本，容易拿错

### 处理
- 重新整理桌面提交目录
- 删除旧版提交副本
- 只保留 `.env.example`

### 结果
- 当前桌面提交目录不含真实密钥
- 可直接作为 GitHub 上传基线

## 11. 当前稳定状态
- metadata：120
- pdf：120
- parsed_docs：116
- sections：116
- final_results：116
- unresolved extract failure：1
- unresolved parse failure：4

## 12. 当前仍存在的明确缺口
- 4 份公告仍未完成 MinerU 解析
- 1 份公告仍未完成 extract（JSON 输出格式失败）

结论：
- 当前项目已经达到可提交状态
- 但如果要追求更高完成率，下一步优先级应是：
  1. 继续研究这 4 份超长 reply 文档的 MinerU 解析策略
  2. 单独处理 `1224636453` 的 LLM 输出格式问题

## 13. 2026-06-08 第15页自检与第二轮优化
### 发现
- 对照课程第 15 页后，发现虽然评估主体已经基本齐全，但仍有几类正式交付和一致性问题：
  - 缺少独立的 `optimization_log.md`
  - 缺少独立的 `final_report.md`
  - `final_slides.pdf`、`final_slides_notes.md`、`README.md` 里仍保留旧数字 `110`
- 同时，人工评估中的主要错误类型已经比较集中：
  - `target_missing`
  - `doc_type_wrong`
  - `action_type_misclassified`
  - `action_requirement_confused`

### 处理
- 新增正式交付件：
  - `optimization_log.md`
  - `final_report.md`
- 更新正式展示材料：
  - `final_slides_notes.md`
  - `final_slides.pdf`
  - `README.md`
- 针对下一轮准确率做规则级优化：
  - `section routing` 跳过目录/摘要页
  - `prompt` 强化 listed_company / deadline / action_type 规则
  - `validator` 基于 evidence 修正明显错误的 `action_type`，并清除 evidence 不支持的 `deadline`

### 为什么这样处理
- 这轮优化的目标不是“改文档看起来更完整”，而是把人工评估里已经暴露的主要错误类型，转换成可以解释、可以复现的规则修正
- 同时，这些优化不依赖重新做 MinerU 解析，因此成本最低、最适合在当前阶段继续提升抽取准确率

### 结果
- 第 15 页要求中的交付缺口已补齐
- `final_slides.pdf`、`final_slides_notes.md`、`README.md` 已和当前真实结果 `116` 对齐
- 这轮优化已经写入：
  - `optimization_log.md`
  - `outputs/reports/refactor_change_summary_2026-05-24.md`
- 但注意：
  - 当前 `eval_report_final.md` 仍然是“优化前最后一次全量运行”的结果摘要
  - 如果要验证这轮优化是否真的提升准确率，还需要重跑：
    1. `route_sections`
    2. `extract`
    3. `validate`
    4. `report`

### 结论
- 这轮优化完成后，**不需要重跑 MinerU**
- 只需要重跑 `route_sections -> extract -> validate -> report`
- 是否提升准确率，要以重跑后的新 `eval_report_final.md` 为准
