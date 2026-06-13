# Refactor Change Summary

Date: 2026-05-24

## 文件目的
这份文件用于回答三个问题：

1. 这一轮到底发现了什么问题  
2. 针对每个问题具体改了什么  
3. 为什么要这样改，而不是用别的方式

它不是简单的“改动清单”，而是本轮项目重构的决策说明。后续写汇报、答辩、解释项目边界时，都可以直接引用这份文件。

---

## 一、这轮重构为什么会发生

本轮重构有两个触发原因。

### 1. 老师对 `topic_proposal.md` 提出了 5 条明确修改建议
核心是：
- 题目边界要明确，到底做单公告抽取还是跨公告闭环
- `targets / issues / actions` 不能太粗，必须继续 schema 化
- 标签要白名单化，否则后续统计不可比
- 样本过滤规则要写清楚，不能只靠关键词检索
- 评估必须做到字段级，而不是笼统“人工看过”

### 2. 代码与数据在实际运行中暴露了新的工程问题
虽然原版流程已经“能跑”，但还不够“能交”：
- 文档口径和代码口径并不完全一致
- metadata 中混入了很多附件型文本，偏离项目题目
- section routing 在 reply / regulatory_measure 上存在错分风险
- parse 在全量重跑时效率偏低
- extract 容易因为长文本、坏 item、接口超时而失败
- 最终提交材料里还有旧口径文件引用

所以这次不是“为了多加功能而改代码”，而是把整个项目从“初版可跑”收紧成“口径清楚、样本更准、字段可评估、结果可提交”的版本。

---

## 二、重构后的总体结果

截至当前版本，重构后的真实产物是：

- `metadata.csv`: 120 条
- `data/pdf/`: 120 份 PDF
- `data/parsed/parsed_docs.jsonl`: 116 条成功解析
- `data/parsed/sections.jsonl`: 116 条 section
- `outputs/results/final_results.jsonl`: 110 条最终结构化结果
- `outputs/reports/manual_eval_filled_single_announcement.csv`: 20 篇样本、105 行字段级人工评估
- `outputs/reports/eval_report_final.md`: 已按新版口径刷新

这说明本轮修改不是停留在文档层，而是已经落实到了真实数据、真实运行和最终交付物上。

---

## 三、详细修改说明

下面按“发现的问题 -> 如何修改 -> 为什么这样修改 -> 修改效果”展开。

---

## 1. 项目边界不够清楚：单公告抽取还是跨公告闭环？

### 发现的问题
老师指出的第一个核心问题是：题目写的是“监管问询/关注函与监管措施”，但方案里又是一条记录对应一份公告。  
这会导致两个风险：

- 风险 1：题目表达看起来像是在做“问询函—回复—整改”闭环追踪
- 风险 2：代码实际上只处理单篇文档，和题目口径不一致

如果不明确，答辩时老师很容易追问：
- 你有没有匹配原函和回复？
- 你有没有判断公司是否逐项回应？
- 为什么这是标准档不是挑战档？

### 如何修改
把整个项目统一锁定为：

- **单公告抽取**
- **一条记录 = 一份公告 PDF**
- **不做问询函—回复跨公告闭环匹配**
- `reply` 类公告保留，但只抽当前公告中明确出现的对象、问题、要求

同步修改了以下文件：
- [topic_proposal.md](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/topic_proposal.md:1)
- [crawl_spec.md](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/crawl_spec.md:1)
- [difficulty_declaration.md](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/difficulty_declaration.md:1)
- [workflow_design.md](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/workflow_design.md:1)
- [README.md](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/README.md:1)
- [demo_script.md](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/demo_script.md:1)

### 为什么这样修改
因为老师的建议本质上是在要求“问题定义”和“实现边界”一致。  
这次作业的标准档完全可以做单公告抽取，而且这是一个明确、可复现、可评估的问题。  
如果继续保留闭环措辞，但代码并不做闭环匹配，就会构成项目定义不实。

### 修改效果
- proposal、代码、评估、汇报口径统一
- 难度档位解释更稳：标准档 1.0，而不是隐含挑战档
- 后续所有评估和 demo 都不再需要解释“为什么没做跨文档匹配”

---

## 2. Schema 太粗，抽出来之后不利于统计和评估

### 发现的问题
原始版本里虽然已经有 `targets[] / issues[] / actions[]`，但内部仍然过于粗粒度。  
例如：
- target 只有名字，没有对象类型
- issue 可能只有一句描述，没有标签化类型
- action 没有 deadline / required_disclosure 这类可对比字段

这种结构有两个直接问题：
- 无法按字段做稳定统计
- 人工评估时也很难定义“到底算对还是算错”

### 如何修改
把三类列表都升级成结构化对象：

#### `targets[]`
- `name`
- `role`
- `target_type`
- `evidence`

#### `issues[]`
- `issue_type`
- `issue_summary`
- `is_violation_related`
- `evidence`

#### `actions[]`
- `action_type`
- `deadline`
- `required_disclosure`
- `evidence`

涉及文件：
- [src/schemas.py](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/src/schemas.py:1)
- [output_sample.md](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/output_sample.md:1)
- [prompts/prompt_final.md](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/prompts/prompt_final.md:1)

### 为什么这样修改
因为老师要求的是“结构化抽取项目”，不是“把一段文本换个 JSON 壳子装起来”。  
只有把对象、问题、动作拆成稳定字段，后面才可能做：
- 类型分布统计
- 字段级人工评估
- 错误类型分析

### 修改效果
- 最终报告已经能输出 `target_type / issue_type / action_type` 的真实分布
- 人工评估文件已经按字段级口径落地
- 最终结构不是“可读”，而是“可分析”

---

## 3. 标签不收敛：LLM 容易输出一堆近义标签

### 发现的问题
如果不给 `issue_type / action_type / target_type` 设白名单，模型会出现这些问题：
- 同义标签并存，例如“信息披露不规范 / 信息披露违规 / 披露问题”
- 粒度不一致，有的抽概括词，有的抽细项
- 后续统计完全不可比

这正是老师第 3 条意见里指出的问题。

### 如何修改
把三类标签改成固定枚举。

#### `target_type`
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

#### `issue_type`
- `information_disclosure`
- `internal_control`
- `fund_occupation`
- `related_party_transaction`
- `raised_funds`
- `financial_irregularity`
- `mna_restructuring`
- `other`

#### `action_type`
- `inquiry_reply_required`
- `rectification_required`
- `warning_letter`
- `supervisory_talk`
- `order_correction`
- `disclosure_update_required`
- `written_report_required`
- `other`

并在三个位置同时收紧：
- schema 限定
- prompt 约束
- validator 拒绝枚举外值

涉及文件：
- [src/schemas.py](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/src/schemas.py:1)
- [prompts/prompt_final.md](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/prompts/prompt_final.md:1)
- [src/validator.py](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/src/validator.py:1)
- [src/reporter.py](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/src/reporter.py:1)

### 为什么这样修改
因为这类项目最后是要展示“风险类型分布”“监管动作分布”的。  
如果标签不统一，报告里的统计图和表没有解释力。

### 修改效果
新版报告已经能直接统计：
- `issue_type` 分布
- `action_type` 分布
- `target_type` 分布

这比旧版本只有自由文本描述更符合课程的“结构化信息抽取”目标。

---

## 4. 样本边界不清：metadata 中混入了很多附件型文本

### 发现的问题
在第一次 refactor 之后，虽然关键词已经扩展了，但 `metadata.csv` 里仍然混入很多偏附件/中介文本，例如：
- 募集说明书更新提示
- 法律意见书
- 会计师专项说明
- 核查意见
- 中介机构单独回复

这些文本的问题不在于“是假数据”，而在于它们和项目想做的“监管公告正文抽取”不是同一类对象。  
如果放任这些标题进入样本，会导致：
- 样本边界漂移
- reply 类样本被大量中介附件占据
- 后续 extract 抽不到真正的监管对象和监管动作

### 如何修改
在 [configs/crawl_config.yaml](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/configs/crawl_config.yaml:1) 增加更严格的标题过滤规则，并同步到 [src/collector.py](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/src/collector.py:1)。

新增 `attachment_exclude_keywords`，包括：
- `提示性公告`
- `申请文件更新`
- `募集说明书`
- `法律意见书`
- `专项说明`
- `核查意见`
- `律师事务所`
- `会计师事务所`

同时保留 include / priority / dedupe 规则，并新增 `matched_search_keys`，方便回看一条样本是通过哪些关键词命中的。

### 为什么这样修改
因为真实项目里“检索出来”和“应该纳入样本”是两个不同问题。  
老师要求把过滤规则写清楚，本质上就是要求我们明确“什么算样本，什么不算样本”。

### 修改效果
- metadata 在新的过滤规则下重新生成
- 样本更贴近“监管公告正文”
- 可以明确解释为什么排除某些标题，而不是说“模型没抽好”

补充说明：
- 这轮过滤后样本仍然偏向 `reply + regulatory_measure`
- 这是当前时间范围和标题规则下的真实数据分布
- 这个偏态已在 [outputs/reports/pre_extract_alignment_review.md](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/outputs/reports/pre_extract_alignment_review.md:1) 里记录为“已知残余风险”，不会被掩盖

---

## 5. section routing 容易和文书类型错位

### 发现的问题
原来的路由逻辑更偏向“谁的正文更长、质量更好就选谁”，这会导致一个实际问题：
- 有些 `reply` 文档虽然标题明确是回复，但如果某个候选 section 被判定更长或更完整，就可能被错误路由成 `regulatory_measure_body`

这类错误一旦发生，后面的 extract 就会在错误 section 上工作，最终结果即使“结构正确”，语义也会错。

### 如何修改
在 [src/section_router.py](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/src/section_router.py:1) 中调整选择逻辑：

- 优先遵循标题推断出来的文书类型
- 只有在“首选 section 根本不存在”时，才退回到其他候选

同时在 [configs/section_rules.yaml](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/configs/section_rules.yaml:1) 中补充了与当前项目口径一致的触发词：
- `回复`
- `回函`
- `延期回复`
- `年报问询`
- `监管谈话`
- `整改报告`

### 为什么这样修改
因为“正文质量最好”不等于“正文类型正确”。  
在这个项目里，section routing 的第一目标是**类型一致**，第二目标才是**文本尽可能完整**。

### 修改效果
- reply 文档不再轻易被路由到监管措施正文
- route_sections 与 doc_type 口径更一致
- 新版 `sections.jsonl` 与最终题目定义对齐

---

## 6. Prompt 仍然存在自由发挥空间，不够“工程化”

### 发现的问题
如果 prompt 只写“请抽取这些字段”，会有几个典型风险：
- 模型跨文档联想
- 模型自己补全未出现的值
- 枚举不收敛
- 布尔字段随意输出
- 非 JSON 输出

这在实际 extract 过程中确实表现为：
- JSON 解析错误
- 非法转义字符
- 字段缺失

### 如何修改
在 [prompts/prompt_final.md](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/prompts/prompt_final.md:1) 中明确写死以下规则：

- 只看当前公告，不关联其他文档
- `reply` 文档不回指原问询函
- 只允许使用白名单枚举
- 证据必须来自输入原文
- 无法确定一律 `null`
- 只输出严格 JSON

### 为什么这样修改
因为这个项目的关键不是“模型理解得多聪明”，而是“模型输出能不能稳定进入后处理”。  
如果 prompt 不收紧，后面的 schema / validator 再强，也只能不断兜底，而不能从源头减少错误。

### 修改效果
- prompt 和 schema 现在是一套一致的约束
- 后续很多错误可以更明确地归因为“模型没遵守规则”，而不是“规则没定义”

---

## 7. Validator 太弱会把伪正确结果放进 final results

### 发现的问题
仅靠 Pydantic 校验 JSON 结构是不够的。  
即使 JSON 结构合法，仍然可能出现：
- `evidence_text` 根本不在原文里
- `page_no` 和正文页码不匹配
- 枚举值不在白名单内
- 布尔字段写成字符串
- list item 缺少关键字段

这类错误如果进入最终结果，会让答辩现场出现最危险的问题：  
“看起来是结构化结果，但证据根本对不上。”

### 如何修改
升级 [src/validator.py](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/src/validator.py:1)，增加强校验：

- `evidence_text` 必须是 `section_text` 的原文子串
- `page_no` 必须能落在 `[Page N]` 范围内
- `target_type / issue_type / action_type` 必须属于白名单
- `is_violation_related / required_disclosure` 必须是布尔或 `null`
- 坏 item 丢弃并写入日志，而不是静默混入最终结果

### 为什么这样修改
因为课程要求的不是“模型说得像”，而是“关键字段有证据可回溯”。  
Validator 在这里承担的是“防编造闸门”的角色。

### 修改效果
当前 `validate` 结果是：
- `110` 条进入最终结果
- `42` 处被修复
- `0` 条在 validate 阶段被整条丢弃

说明校验不是摆设，而是真正参与了结果清洗。

---

## 8. Reporter 原来只能做粗粒度汇总，不满足老师的评估要求

### 发现的问题
原始报告能做一些总量统计，但无法回答老师真正关心的问题：
- 哪类字段更容易错？
- 错误主要集中在 target 还是 action？
- 哪种 issue_type 最多？
- 人工评估到底按什么口径做？

### 如何修改
升级 [src/reporter.py](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/src/reporter.py:1)：

- 增加 `target_type / issue_type / action_type` 分布
- 增加 item 数量统计
- 支持读取 `manual_eval_filled_single_announcement.csv`
- 自动汇总字段级准确率
- 自动汇总错误类型分布和 Top-5 错误样例

同时调整人工评估模板：
- [outputs/reports/manual_eval_template.csv](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/outputs/reports/manual_eval_template.csv:1)

### 为什么这样修改
因为老师第 5 条意见本质上是在要求：  
评估必须从“我觉得差不多对”升级到“按字段、按错误类型有证据地评价”。

### 修改效果
当前最终报告已经包含：
- `doc_type / regulator_name / targets / issues / actions` 字段级准确率
- evidence_correct
- 错误类型分布
- Top-5 代表样例

这部分已经从“叙述型总结”变成“指标型评估”。

---

## 9. 长 PDF 导致 extract 速度慢、超时、非 JSON

### 发现的问题
这是本轮最典型的实际工程问题之一。  
监管回复、整改报告、并购问询回复经常很长。即使已经做了 section routing，section_text 仍然可能非常大。  
在实际运行中出现了：
- `Read timed out (300s)`
- `Invalid \\escape`
- JSON 截断

这些错误都说明 LLM 输入过长、上下文过噪，稳定性不足。

### 如何修改
在 [src/extractor.py](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/src/extractor.py:1) 中加入输入长度控制：

- 先按 `[Page N]` 做页级切片
- 最多保留前 5 个 page block
- 再增加最大字符上限

并在 [configs/model_config.yaml](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/configs/model_config.yaml:1) 中同步相关控制参数。

### 为什么这样修改
因为在这类公告里，监管对象、问题点、要求通常集中在前几页正文。  
项目目标不是“把整份文档喂给模型”，而是“让模型在最相关的正文中稳定抽取结构化字段”。

### 修改效果
这一轮 extract 最终完成到：
- `116 -> ok 110 / failed 6`

相较于早期版本，长文本导致的超时和异常已经明显收敛，没有因为长度问题让整轮流程失控。

---

## 10. Extract 里“坏 item 导致整条失败”的问题

### 发现的问题
实际运行中出现过这种错误：

```text
targets.0.name = None
```

这说明模型虽然大体输出了正确结构，但某一个数组项缺了关键字段。  
如果不处理，Pydantic 会让整条公告直接失败，代价很高：
- 一条坏 target
- 导致整份公告丢掉

### 如何修改
在 [src/extractor.py](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/src/extractor.py:1) 里增加 normalize / clean 逻辑：

- 对 `targets / issues / actions` 逐项清洗
- 缺关键字段的 item 直接丢弃
- 保留其余合法 item
- 再进入 Pydantic 校验

### 为什么这样修改
因为项目的目标是尽量保留真实可用的信息，而不是用最严格的结构要求把整条记录一起打掉。  
这里更合理的策略是：
- 坏 item 丢掉
- 好 item 保留
- 错误留下日志

### 修改效果
后续 extract 没再因为这类单个 item 的问题大面积报废文档，最终能稳定产出 110 条结果。

---

## 11. LLM 接口超时和网络抖动需要显式重试

### 发现的问题
在这轮 extract 中真实出现过：
- `Read timed out`
- `Max retries exceeded`
- 代理连接中断

这不是数据问题，而是远端接口和网络层问题。  
如果完全不重试，就会把“暂时性故障”直接记成“样本失败”。

### 如何修改
在 [src/llm_client.py](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/src/llm_client.py:1) 中加入：

- `max_retries`
- `retry_backoff_seconds`
- 对 `Timeout / ConnectionError / 5xx` 的有限重试

同时在 [configs/model_config.yaml](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/configs/model_config.yaml:1) 中显式配置：
- `max_inflight_requests`
- `max_retries`
- `retry_backoff_seconds`

### 为什么这样修改
因为这类故障是短暂的、可恢复的。  
完全不重试会让结果对网络状态过于敏感；重试过多又会拖死总时长。  
因此这里采用的是**有限重试**，而不是无限兜底。

### 修改效果
新版 extract 在保留错误日志的同时，提高了整轮完成率，没有把所有网络抖动都转换成最终失败。

---

## 12. parse 旧逻辑虽然正确，但在全量重跑时效率太低

### 发现的问题
原来的 parse 逻辑是严格串行：
- 提交一篇
- 原地等待
- 完成后再提下一篇

对于本项目这种 100+ PDF 的情况，这个逻辑虽然不“错”，但会明显拖慢全量重跑。  
尤其在老师要求“规则修改后从 collect 开始全量重建”的前提下，parse 成为了明显瓶颈。

### 如何修改
重写 [src/parser.py](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/src/parser.py:1)：

- 每次都按当前 metadata 重建 `parsed_docs.jsonl`
- 优先复用现有 cache
- 对 uncached 文档启用小并发轮询
- 同时挂最多 4 个 MinerU 任务
- 回收成功任务并持续写回相同格式输出

并在：
- [configs/model_config.yaml](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/configs/model_config.yaml:1)
- [pipeline_run.py](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/pipeline_run.py:1)

中接入 `max_inflight_tasks`。

### 为什么这样修改
因为这里的问题不是业务逻辑，而是工程吞吐。  
在不改变数据口径、不引入 fallback 的前提下，小并发轮询是最稳妥的优化方式。

### 修改效果
最终 parse 实际结果：
- `cached=61`
- `success=55`
- `failed=4`
- `parsed_docs.jsonl=116`

说明这次优化既保留了 cache 复用，又顺利完成了大部分新解析任务。

---

## 13. 提交材料和样例检查文件还停留在旧口径

### 发现的问题
在进入新版 extract 之前做仓库审查时，发现有几类文档已经和新版方案不一致：

#### 问题 1：提交清单还指向旧的人工评估文件
- 仍引用 `manual_eval_filled_evidence_chain.csv`

#### 问题 2：样例检查文件绑定了旧 doc_id
- 一旦全量重跑，旧 doc_id 很可能失效

#### 问题 3：demo_script 没有固定最终样本
- 容易造成答辩现场“讲稿和最终结果不是同一条公告”

### 如何修改
- 更新：
  - [submission_checklist/week16_submit_list.md](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/submission_checklist/week16_submit_list.md:1)
  - [submission_checklist/manifest.csv](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/submission_checklist/manifest.csv:1)
- 将主评估文件统一为：
  - `outputs/reports/manual_eval_filled_single_announcement.csv`
- 把：
  - [sample_checks/evidence_chain_example.md](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/sample_checks/evidence_chain_example.md:1)
  改成模板
- 把：
  - [demo_script.md](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/demo_script.md:1)
  固定到真实样本 `doc_id=1225290815`
- 新增：
  - [outputs/reports/pre_extract_alignment_review.md](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/outputs/reports/pre_extract_alignment_review.md:1)
  记录进入 extract 前的口径审查结果

### 为什么这样修改
因为项目提交时，老师看的不只是代码和结果，还会看：
- 你交的文件是不是自洽
- 你的 demo 能不能现场复现
- 你的评估文件和报告是不是同一套口径

### 修改效果
最终提交材料的引用关系已经统一，避免了“结果是新的，但提交清单还是旧的”这种典型收尾错误。

---

## 14. 人工评估原来只是模板，不能支撑最终报告

### 发现的问题
在新版 report 生成后，虽然自动部分已经对齐，但人工评估部分仍然只是模板。  
如果不补这一步，最终报告会停留在：
- “计划做 20 篇”
- “错误分析待补充”

这不满足课程最终提交要求。

### 如何修改
补全了：
- [outputs/reports/manual_eval_filled_single_announcement.csv](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/outputs/reports/manual_eval_filled_single_announcement.csv:1)

具体做法：
- 固定 20 篇样本
- 按字段级口径填写 105 行
- 标出 16 个真实错项
- 归类为：
  - `target_missing`
  - `doc_type_wrong`
  - `action_type_misclassified`
  - `issue_summary_incorrect`
  - `action_requirement_confused`
  - `issue_type_misclassified`

然后重新运行 report，刷新：
- [outputs/reports/eval_report_final.md](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/outputs/reports/eval_report_final.md:1)

### 为什么这样修改
因为老师要求的是“字段级人工评估”，而不是“自动报告 + 人工口头解释”。  
人工评估必须成为项目交付物的一部分，而不是附带说明。

### 修改效果
最终报告已经包含真实字段级准确率：
- `doc_type`: `16/20 = 80.0%`
- `regulator_name`: `14/14 = 100.0%`
- `targets`: `21/27 = 77.8%`
- `issues`: `17/20 = 85.0%`
- `actions`: `21/24 = 87.5%`

这部分已经能直接用于 slides 和答辩。

---

## 四、这轮修改后，项目质量具体提升在哪里

从结果上看，这轮修改带来了 5 个层面的提升。

### 1. 题目边界更清楚
现在任何人看 proposal、README、demo script，都会知道这是一个**单公告抽取**项目，不会再误解成闭环跟踪项目。

### 2. 样本边界更清楚
metadata 不再只是“关键词抓到什么算什么”，而是有明确 include / exclude / priority / dedupe 规则。

### 3. 结果结构更可分析
从自由文本列表升级成结构化对象 + 白名单标签，后续才能真正做统计。

### 4. 运行流程更稳定
parse 有并发和 cache，extract 有截断、清洗、重试，validate 有硬校验，整轮流程已经能稳定落到最终结果。

### 5. 交付材料更自洽
proposal、代码、报告、人工评估、demo、提交清单现在是同一套口径，不再彼此打架。

---

## 五、这轮重构仍然暴露出的剩余问题

这轮修改已经把项目收紧到可提交状态，但还有一些真实问题需要在汇报时诚实说明。

### 1. `doc_type` 仍然有边界错分
在人工评估中，`doc_type` 只有 `80.0%`。  
主要问题集中在“延期回复关注函/问询函”这类公告：
- 标题里同时包含 `关注函/问询函` 和 `延期回复`
- 目前规则有时仍会把它们分到 `attention_letter / inquiry_letter / other`
- 按当前项目口径，更合理的归类应是 `reply`

### 2. `target_missing` 仍然是最大错误类型
特别是在中介机构回复、专项整改报告里，模型有时会抓不到真正应当保留的 target。

### 3. `final_slides.pdf` 还是旧版
目前最新讲稿已经写在：
- [final_slides_notes.md](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/final_slides_notes.md:1)

但 PDF 本身还需要用这份讲稿更新。

### 4. 工作目录里仍然有 `.env`
桌面提交副本已经排除了 `.env`，但工作目录：
- `/Users/wjy/Documents/Codex project/学术/final_repo/.env`

仍然存在。若直接打包工作目录，提交前必须删掉。

---

## 六、总结

这轮 refactor 的本质不是“又写了一些代码”，而是把项目从三个维度收紧：

- **题目定义收紧**：从模糊的监管文本项目，收紧为单公告结构化抽取
- **数据边界收紧**：从关键词召回结果，收紧为有过滤规则的有效样本集
- **结果约束收紧**：从“能输出 JSON”收紧为“字段可验证、证据可回溯、评估可量化”

因此，本轮修改的价值不在于代码量，而在于把这个项目变成一个：

- 口径明确
- 数据真实
- 过程可复现
- 结果可检查
- 提交时不容易被问倒

的课程项目。

---

## 七、2026-06-08 错误驱动优化（本轮新增）

这一节记录的是在人工评估与第 15 页自检完成之后，针对“会直接影响下一轮 extract 准确率”的问题做的优化。

### 1. 这轮优化是如何触发的

在查看 `manual_eval_filled_single_announcement.csv` 后，最突出的错误类型集中在：

- `target_missing`
- `doc_type_wrong`
- `action_type_misclassified`
- `action_requirement_confused`

这些错误说明：
- 数据本身并不是错的
- routed section 里通常已经有证据
- 问题主要出在 routing 噪声、prompt 约束不足、以及 validator 对细粒度子字段的修复不够

因此这次没有去动数据源，也没有重做 MinerU，而是直接针对“错误来源”做规则级优化。

### 2. 发现了什么问题

#### 问题 A：reply 文档容易把目录页也带进 section

目录页里经常会出现：
- `问题1`
- `问题2`

旧逻辑会把这些页也当成 anchor 命中页，导致送进 LLM 的正文 section 含有目录噪声。

#### 问题 B：reply 文档里的上市公司 target 容易漏抽

有些 reply 文档虽然是中介机构、控股股东或实控人发出的回复，但正文里已经明确写出上市公司/发行人名称。  
旧 prompt 对这一点约束不够，容易只保留中介或个人 target，而漏掉 `listed_company`。

#### 问题 C：deadline 会把签字日期误当成监管期限

人工评估里的典型例子是：
- 文末签字页有日期
- 模型把它误填成 `actions[].deadline`
- 但 action evidence 本身并不支持这个截止时间

#### 问题 D：某些 action_type 其实有明确关键词，却仍被错分

例如：
- evidence 明确含 `警示函`，却被抽成 `order_correction`
- evidence 明确含 `监管谈话`，却被抽成 `order_correction`

这类错误不需要“更聪明的推理”，只需要更严格的 evidence 驱动映射。

### 3. 如何修改

#### 修改 1：reply routing 跳过目录/摘要等噪声页

改动：
- [configs/section_rules.yaml](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/configs/section_rules.yaml:1)
- [src/section_router.py](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/src/section_router.py:1)

具体做法：
- `目录 / 声明 / 摘要` 页不再参与 anchor 匹配
- 组装 `section_text` 时也直接跳过这些页
- `inquiry_attention_body.page_expansion.before` 从 `1` 提到 `2`

为什么这样改：
- 如果只去掉目录页，但不扩大前向页数，就可能丢掉 reply 文档第一页里关于监管对象和公司名称的说明
- 所以这次不是简单删页，而是：
  - 去掉目录页干扰
  - 保留更完整的正文前导页

#### 修改 2：prompt 强化 target / deadline / action_type 规则

改动：
- [prompts/prompt_final.md](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/prompts/prompt_final.md:1)

新增规则：
- 名称尽量保持中文原文，不做英文翻译标签化
- reply 文档里只要当前文本明确写出上市公司/发行人/上市公司，就应抽 `listed_company`
- 延期回复公告如果只说“延期原因”，不要把泛化的延期原因当成监管问题
- `deadline` 只能来自明确期限表达，不能把签字日期、公告日期填成 deadline
- evidence 若明确含 `警示函 / 监管谈话 / 责令改正 / 书面报告 / 补充披露 / 整改`，要优先映射到固定 `action_type`

为什么这样改：
- 这些错误都已经在人工评估里反复出现
- 仅靠“再跑一次”不会自动变好，必须把边界规则写进 prompt

#### 修改 3：validator 增加 evidence 驱动的修正

改动：
- [src/validator.py](/Users/wjy/Documents/Codex%20project/%E5%AD%A6%E6%9C%AF/final_repo/src/validator.py:1)

新增修正规则：
- evidence 含 `警示函` -> `warning_letter`
- evidence 含 `监管谈话` -> `supervisory_talk`
- evidence 含 `责令改正` -> `order_correction`
- evidence 含 `书面报告 / 书面说明 / 报送书面报告` -> `written_report_required`
- evidence 含 `补充披露 / 更新披露 / 披露材料` -> `disclosure_update_required`
- evidence 含 `整改 / 整改措施 / 整改情况` -> `rectification_required`

同时新增 deadline 修正：
- 如果 `deadline` 不是 `evidence_text` 的子串，就直接清空为 `null`

为什么这样改：
- 这类标签如果 evidence 已经足够明确，就不应该继续完全依赖模型自由判断
- `deadline` 属于高风险字段，宁可保守清空，也不要错误填写

### 4. 为什么这轮优化不需要重跑 MinerU

这轮改动只影响：
- `route_sections`
- `extract`
- `validate`
- `report`

没有改动：
- 原始 PDF
- MinerU 解析结果 `parsed_docs.jsonl`

所以如果要验证这轮优化效果，最小重跑路径是：

1. `route_sections`
2. `extract`
3. `validate`
4. `report`

不需要重跑：
- `collect`
- `download`
- `parse`

除非你还想继续单独攻克那 4 份 MinerU 仍超时的超长回复公告。

### 5. 当前状态

截至这份文档更新时：
- 这轮优化已经完成实现
- 相关改动已经落到配置、prompt、validator 和文档中
- 但还没有用新规则重新全量跑一轮 extract

因此当前最准确的表述是：
- **优化已完成**
- **准确率提升方向明确**
- **真实提升幅度仍需通过下一轮 `route_sections -> extract -> validate -> report` 再验证**

---

## 2026-06-13 补充：新版 prompt 重跑后的验证结果

### 发现的问题
- 新版 prompt 和模型 `nex-agi/Nex-N2-Pro` 全量重跑后，`extract` 首轮结果为 106 成功、10 失败。
- 失败主要来自远端 LLM timeout；这说明 prompt 优化不能完全解决接口稳定性问题。
- 如果不处理这些失败，最终结果数量会从 section 的 116 条下降到 106 条，影响样本覆盖率。

### 修改和处理
- 对失败的 10 个 `doc_id` 使用 `scripts/retry_extract_subset.py` 单独重试。
- 将 timeout 从默认 300 秒延长到 900 秒。
- retry 成功 9 条，失败 1 条：`1224517046`，原因是远端 API 500。
- 将 retry 成功结果合并回正式输出，并重新运行 `validate` 和 `report`。

### 为什么这样处理
- timeout 属于运行环境和远端服务稳定性问题，不应通过手工改结果解决。
- 延长 timeout 可以在不改变数据、不降低 validator 标准的情况下提高完成率。
- API 500 无法通过本地规则修复，因此保留为真实失败并写入日志。

### 实际效果
- `final_results.jsonl`: 115 条
- `extract_errors.jsonl`: 1 条
- `validation_errors.jsonl`: 39 条
- `validate` 日志：total = 115, ok = 115, repaired = 39, dropped = 0
- 相比优化前 `repaired=70`，本轮 validator 修复量下降到 39，说明 evidence 复制规则、whitespace-tolerant 修复和 action_type 优先级修正对减少无效错误有效。
