# Demo Script

本项目的 demo 不应只展示“最后抽出了一个表”，而应按照 Week 14 的 workflow 逻辑，证明：

1. 每一步都有明确输入和输出。
2. 每一步都有可检查结果和日志。
3. 最终结构化结果能回溯到真实 PDF 与证据片段。

---

## 1. Demo 总体策略

结合 [Week 14 Workflow Demo](https://ml-nlp.netlify.app/labs/week14_workflow_demo) 的要求，**正式答辩建议采用“先 workflow，后单样本证据链”** 的展示方式，而不是一上来就打开 `final_results.jsonl`。

推荐顺序：

1. 先展示 workflow 配置和 step 形状
2. 再展示历史运行日志，证明全流程真实跑通过
3. 再展示一条固定样本，从 metadata 到 PDF 到 routed section 到 final result
4. 最后补一句：如果某一步失败，可以单步重跑，不需要整条链路重跑

同时必须满足你刚整理的 Demo 最低要求：

1. 展示 1 份原始 PDF
2. 展示该 PDF 在 `metadata.csv` 中的记录
3. 展示 MinerU 解析后的目标文本片段
4. 展示 section 检查记录
5. 展示 LLM 抽取 JSON / JSONL
6. 展示 Pydantic / validator 校验结果
7. 展示最终结果中的对应记录
8. 至少解释 2 个关键字段的 `evidence_text / page_no`

---

## 2. 为什么不建议在 `final_repo/` 现场重跑全流程

你当前项目的 `pipeline_run.py` 是**正式输出型入口**，不是纯演示型入口。

这意味着：

- `parse` 依赖 MinerU API，现场跑可能慢
- `extract` 依赖 LLM API，现场跑可能超时
- `validate` 会重写 `outputs/results/final_results.jsonl`
- `report` 会重写 `outputs/reports/eval_report_final.md`

所以：

- **不建议**在正式答辩时直接在 `final_repo/` 中运行 `--step all`
- **也不建议**在 `final_repo/` 中随意运行会改写正式结果的步骤

更合理的答辩方式是：

- 用**已有正式产物 + 历史日志**展示全流程已经跑完
- 用**一个固定样本**展示 evidence 链
- 口头说明：若步骤失败，可以按 `route_sections / extract / validate` 单步重跑

这更符合 Week 14 页面强调的“workflow 可检查、可定位、可重跑”，同时不会破坏你已完成的最终结果。

---

## 3. 当前稳定版项目状态

- `metadata.csv`：120 条元数据
- `data/pdf/`：120 份 PDF
- `parsed_docs.jsonl`：116 份 MinerU 成功解析
- `sections.jsonl`：116 条 routed section
- `final_results.jsonl`：115 条最终结构化结果
- `extract_errors.jsonl`：1 条远端 LLM API 500 失败记录

关键完成日志：

- `2026-06-12T19:07:43Z extract done total=116 ok=106 failed=10`
- `2026-06-13T01:07:47Z extract_retry done total=10 ok=9 failed=1`
- `2026-06-13T01:16:32Z validate done total=115 ok=115 repaired=39 dropped=0`

---

## 4. 正式答辩推荐展示顺序

### Part A. 先讲 workflow，不先讲结果

先打开：

- `configs/workflow.yaml`
- `outputs/logs/sample_run_log.jsonl`

要讲清楚：

1. 我的项目不是“直接让 LLM 读 PDF 输出答案”
2. 而是拆成 `collect -> download -> audit -> parse -> route_sections -> extract -> validate -> report`
3. 每一步都有独立输入、输出和日志
4. 如果某一步失败，可以只修那一步，不用整条链路重跑

这一步对应 Week 14 页面中的：

- 查看 workflow 配置
- 一键运行
- 单步运行
- 检查日志

### Part B. 再讲固定样本证据链

固定展示样本：

- `doc_id=1225290815`
- 标题：`关于收到江苏证监局警示函的公告`
- `doc_type=regulatory_measure`

展示顺序：

1. 在 `data/metadata/metadata.csv` 中找到这条公告
2. 打开对应 PDF：`data/pdf/1225290815.pdf`
3. 在 `data/parsed/sections.jsonl` 中找到该文档的 routed section
4. 在 `outputs/results/final_results.jsonl` 中找到最终结构化结果
5. 解释 2 到 3 个字段的 `evidence_text + page_no`

这里要特别说明：

- `section_check_report.csv` 里对同一公告可能有多条 routing 尝试记录
- `sections.jsonl` 只保留最终选中的那一条 section
- 所以现场要先讲“尝试记录”，再讲“最终选中结果”

### Part C. 最后补“失败如何定位”

最后不用真的重跑，只要打开日志说明：

- 主 extract 首轮有 4 条失败
- 错误类型包括超时和 JSON 解析失败
- 后续单独对失败 doc 做 retry，最终补齐

这一段正好对应 Week 14 的核心思想：

- 失败时不重跑所有步骤
- 先定位失败点
- 再做单步修复或局部重跑

---

## 5. 现场建议讲法

### 第一步：展示 workflow 配置

建议打开：

- `configs/workflow.yaml`

重点讲：

- `paths` 规定了各阶段输入输出目录
- `steps.allowed` 规定了这条 pipeline 可以单步运行
- 这保证 workflow 不是“写死在一个 notebook 里”，而是可重复执行的工程化链路

### 第二步：展示历史运行日志

建议打开：

- `outputs/logs/sample_run_log.jsonl`

重点讲：

- 日志记录了 `extract -> retry -> validate -> report`
- 可以看到全量样本是怎样从失败到补齐的
- 这证明结果不是手工拼出来的，而是通过 workflow 真实生成的

### 第三步：展示 metadata

建议搜索：

- `1225290815`

重点讲：

- `doc_id` 对应 `announcementId`
- `pdf_url` 来自 cninfo
- 这说明数据是可追溯的

### 第四步：展示原始 PDF

建议打开：

- `data/pdf/1225290815.pdf`

重点讲：

- 这是原始公告
- 项目所有抽取都必须回到这份原始 PDF 来解释

### 第五步：展示 routed section

建议打开：

- `data/parsed/sections.jsonl`

重点讲：

- 这里不是直接把整份 PDF 全送给 LLM
- 是先把整份 PDF 用 MinerU 解析
- 再用 section routing 从全文中定位最相关正文
- section 中带有 `[Page N]` 标记，后面 validator 会校验 `page_no`

### 第六步：展示 final result

建议打开：

- `outputs/results/final_results.jsonl`

重点讲：

- 最终不是原始 LLM 输出
- 而是经过 validator 校验后的结果
- 非法枚举值、无证据字段、不可靠页码都会在这一层被修正或剔除

### 第七步：解释 3 个字段

建议固定讲这 3 个字段：

1. `regulator_name`
2. `issues[0]`
3. `actions[0]`

因为这 3 个字段最能体现：

- 监管机关是谁
- 核心问题是什么
- 监管动作或整改要求是什么

---

## 6. 建议现场使用的具体文件

### Workflow 层

- `configs/workflow.yaml`
- `outputs/logs/sample_run_log.jsonl`
- `outputs/reports/pipeline_flowchart_annotated.md`

### 证据链层

- `data/metadata/metadata.csv`
- `data/pdf/1225290815.pdf`
- `data/parsed/sections.jsonl`
- `outputs/tmp/llm_raw.jsonl`
- `outputs/tmp/extracted.jsonl`
- `outputs/logs/validation_errors.jsonl`
- `outputs/results/final_results.jsonl`

### 离线 Demo Packet

如果现场网络或 API 不稳定，建议直接使用已经保存好的离线样本包：

- `outputs/reports/demo_packet_1225290815/`

其中已经包含：

1. 原始 PDF
2. metadata 单行
3. MinerU 解析片段
4. section 检查记录
5. section 定位结果
6. LLM 原始抽取结果
7. extracted 记录
8. validation 记录
9. final result

---

## 7. 固定样本讲解内容

### 样本信息

- `doc_id`: `1225290815`
- 标题：`关于收到江苏证监局警示函的公告`
- `doc_type`: `regulatory_measure`
- `pdf_url`: `http://static.cninfo.com.cn/finalpage/2026-05-11/1225290815.PDF`

### 建议讲解字段 1：regulator_name

- value：`江苏证监局`
- evidence：`中国证券监督管理委员会江苏监管局（以下简称江苏证监局）`
- `page_no`：`1`

讲法：

- 监管机关不是凭标题猜的
- 是从正文证据直接抽出来的
- 并且能回到第 1 页定位

### 建议讲解字段 2：issues[0]

- `issue_type`：`information_disclosure`
- `issue_summary`：`未按规定及时履行信息披露义务，未在定期报告中披露多起诉讼仲裁案件`
- evidence：`公司未按规定及时履行信息披露义务，也未在相应的定期报告中披露`
- `page_no`：`1`

讲法：

- 问题类型用了白名单枚举
- 不是任意生成的自然语言标签
- 这样后面才能做同类风险统计

### 建议讲解字段 3：actions[0]

- `action_type`：`written_report_required`
- `deadline`：`10 个工作日`
- evidence：`你们应当于收到本决定书之日起10 个工作日内向我局报送书面报告`
- `page_no`：`1`

讲法：

- `action_type` 表示监管要求类型，这条样本里是“报送书面报告”
- `deadline` 现在会在有明确期限表达时保留，并在仅有空格差异时修回原文写法
- validator 仍然会删除没有合格 evidence 的字段，所以结果是“保守但可追溯”的

---

## 8. 一段可直接照读的 demo 发言

“我先不直接展示最终结果表，而是先展示项目 workflow。因为这个项目的重点不是模型本身，而是把公告处理流程拆成了可以逐步检查的工程化链路。我的流程是 collect、download、audit、parse、route_sections、extract、validate、report。每一步都有输入输出文件，也有日志，所以出问题时可以单步定位，而不是整条链路重跑。

接下来我用一条固定样本演示证据链。这个样本的 `doc_id` 是 1225290815。先展示原始 PDF，再展示它在 metadata 里的记录，然后展示 MinerU 解析片段、section 检查记录、section 定位结果、LLM 抽取结果、validator 校验结果和最终结构化结果。这里我重点解释监管机关和问题点两个字段的 evidence_text 和 page_no。这个 demo 想证明的不是模型会不会生成，而是最终结果是否可追溯、可解释、可复核。” 

---

## 9. 如果老师追问“为什么不现场一键跑 all”

推荐回答：

“Week 14 强调的是 workflow 的输入输出、日志和可重跑能力，而不是一定要在答辩现场把所有 API 再跑一遍。我的正式项目使用真实的 MinerU 和 LLM API，全量运行会受网络和超时影响，而且会改写正式输出文件。所以答辩中我采用的是更稳妥的展示方式：用已完成的正式日志证明 workflow 已经跑通，再用单样本证据链证明结果真实可靠。如果某一步失败，我也能根据 step 入口做局部重跑。” 

---

## 10. 如果一定要做 live command，正确口径是什么

如果老师坚持看命令，不建议在 `final_repo/` 中直接重跑会改写结果的步骤。

正确说法是：

- `final_repo/` 保存的是正式提交结果
- live rerun 应该在单独复制出的 demo 工作目录里做
- 否则会覆盖正式 `final_results.jsonl` 和 `eval_report_final.md`

所以你可以补一句：

“正式结果我已经固定保存在 `final_repo`。如果需要 live rerun，我会在独立 demo 副本里跑，避免污染最终提交版本。” 
