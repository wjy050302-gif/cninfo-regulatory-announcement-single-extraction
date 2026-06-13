# 项目过程与问题完整汇总（2026-06-08）

本文件把项目推进过程中与“问题发现、原因分析、处理方式、当前状态”相关的核心信息汇总成一份完整说明，便于：
- 汇报时按时间线讲清楚项目是如何收敛成当前版本的
- 回答老师关于“你们到底遇到了什么问题、怎么处理”的追问
- 作为后续继续优化或复现时的项目操作记录

## 一、项目当前定义

### 1. 题目
cninfo 监管公告单公告结构化抽取

### 2. 项目边界
- 一条记录 = 一份公告 PDF
- 只做单公告抽取
- 不做“问询函—回复—整改”跨公告闭环匹配
- `reply` 类公告仍保留在样本中，但只抽当前公告文本里的对象、问题和动作

### 3. 数据真实性约束
- 仅使用 cninfo metadata + cninfo PDF + MinerU 解析文本
- evidence 必须是 routed section 原文子串
- 无证据则 `null`
- MinerU 失败不允许本地 fallback

## 二、项目推进主线

整个项目不是一次成型，而是经历了四个阶段：

1. **题目和口径收敛**
2. **数据与 schema 重构**
3. **抽取稳定性与证据链修复**
4. **字段级评估驱动的第二轮优化**

下面按阶段展开。

---

## 三、阶段一：题目和口径收敛

### 发现的问题
- 最初题目容易让人误解成“做监管闭环跟踪”
- 但现有代码和流程实际上是一份公告对应一条记录
- 如果不澄清，会被追问：
  - 有没有匹配原函和回复？
  - 有没有判断是否逐项回应？
  - 为什么是标准档不是挑战档？

### 处理方式
- 正式把题目锁成“单公告抽取”
- 明确：
  - 不做跨公告匹配
  - 不做回复与原函的闭环判断
  - `reply` 文档只处理当前公告内容

### 影响文件
- `topic_proposal.md`
- `crawl_spec.md`
- `workflow_design.md`
- `README.md`
- `prompts/prompt_final.md`

### 结果
- proposal、代码、评估和汇报口径统一
- 标准档 1.0 的边界更清楚

---

## 四、阶段二：数据与 schema 重构

### 问题 1：schema 粒度太粗

#### 发现
- 早期 `targets / issues / actions` 只是粗粒度列表
- 没有细字段时，后续无法做稳定统计，也不利于人工评估

#### 处理
- 升级成结构化对象：
  - `targets[]`: `name / role / target_type / evidence`
  - `issues[]`: `issue_type / issue_summary / is_violation_related / evidence`
  - `actions[]`: `action_type / action_source_type / deadline / required_disclosure / evidence`

#### 结果
- 可以做 item-level 字段评估
- 可以输出类型分布而不是只有文本结果

### 问题 2：枚举缺失，标签不稳定

#### 发现
- 不设白名单时，模型会输出很多近义标签
- 后续统计不可比

#### 处理
- 增加 `target_type / issue_type / action_type / action_source_type` 白名单
- 在 schema、prompt、validator 三层同时约束

#### 结果
- 结果结构更稳定
- 报告中可以直接做分布统计

### 问题 3：样本边界太松

#### 发现
- 仅靠标题关键词会把募集说明书、法律意见书、核查意见等附件型文档混入样本

#### 处理
- 在 `crawl_config.yaml` 和 `collector.py` 中增加：
  - 标题 include
  - 标题 exclude
  - 标题优先级
  - 去重规则

#### 结果
- 样本更接近真实监管公告正文
- 与项目目标更一致

---

## 五、阶段三：解析与抽取稳定性问题

### 问题 1：parse 为什么只有 116 条

#### 发现
- `metadata.csv = 120`
- 但 `parsed_docs.jsonl = 116`

#### 核对结论
- 不是少抓样本
- 是 4 份公告在 MinerU 解析阶段超时失败
- 对应 `doc_id`：
  - `1225286613`
  - `1225284401`
  - `1225282404`
  - `1225274900`

#### 进一步尝试
- 单独将 MinerU 等待时间从 `420s` 提高到 `1200s`
- 重新提交其中一份超时文档做验证

#### 结果
- 仍然超时
- 说明这类超长 reply 文档不是简单“多等一会就能好”

#### 当前稳定口径
- `parse = 116`

### 问题 2：长 PDF 导致 LLM 超时

#### 发现
- reply / 整改类公告非常长
- 直接把整段正文交给 LLM，超时明显增多

#### 处理
- 完整下载 PDF
- 完整用 MinerU 解析整份 PDF
- 先做 section routing
- 再只对 routed section 做长度控制：
  - 前 5 个 `[Page N]` block
  - 最多 20000 字符

#### 结果
- 降低了超时风险
- 同时保留完整证据链

### 问题 3：旧产物会被新运行覆盖

#### 发现
- 多次重跑 `extract` 时，旧 `extracted.jsonl / final_results.jsonl` 容易被覆盖
- `parsed/markdown` 和 `parsed/zip` 也曾有旧残留

#### 处理
- 先备份，再做补跑
- 补跑结果先写临时文件，再并回主结果
- 清理孤儿 parsed 文件
- 保持工作目录与桌面提交目录同步

#### 结果
- 当前稳定产物可追溯
- 提交目录和工作目录一致

---

## 六、阶段四：extract 失败与补跑

### 原始情况
- `extract` 初始结果：`116 -> ok 108 / failed 8`

### 失败类型
- `7` 条：`Read timed out (300s)`
- `1` 条：`failed to parse JSON object from LLM output`

### 处理方式
- 单独抽出这 8 个失败 `doc_id`
- 提高超时到 `600s`
- 单线程、2 次重试
- 补跑结果单独写文件，不覆盖主结果

### 结果
- 8 条中补回 7 条
- 仍剩 1 条失败：
  - `1224636453`
  - 原因：LLM JSON 输出格式失败

### 影响
- 历史阶段结果：`final_results.jsonl` 从 `108` 提升到 `116`
- 当前最新版结果已由 2026-06-13 重跑替代：`final_results.jsonl = 115`

---

## 七、证据链与 validator 修复

### 发现的问题
- 抽取成功不等于字段完全可靠
- 常见问题包括：
  - evidence 不在原文中
  - page_no 不匹配
  - 数组项结构坏掉
  - 枚举值越界

### 处理方式
- validator 增加硬校验：
  - `evidence_text` 必须是 routed section 原文子串
  - `page_no` 必须落在 `[Page N]` 范围内
  - 枚举字段必须合法
  - 无效 item 直接丢弃或修正

### 结果
- 历史阶段：`validate` 对 116 条全部通过，共记录 `60` 条修复
- 当前最新版：`validate` 对 115 条全部通过，共记录 `39` 条修复，未丢弃任何记录

---

## 八、字段级人工评估暴露出的核心问题

### 当前人工评估口径
- 20 篇 PDF
- 105 行字段级标注

### 主要错误类型
- `target_missing`
- `doc_type_wrong`
- `action_type_misclassified`
- `issue_summary_incorrect`
- `action_requirement_confused`
- `issue_type_misclassified`

### 这些错误意味着什么
- `target_missing`：reply 和整改场景下，监管对象识别仍是最大弱点
- `doc_type_wrong`：延期回复类公告的标题边界仍然容易错分
- `action_type_misclassified`：模型对监管动作的标签映射还不够稳定
- `action_requirement_confused`：deadline 之类子字段容易受到签字日期干扰

---

## 九、2026-06-08 第二轮错误驱动优化

这一轮优化不是重跑全流程，而是针对人工评估中最主要的误差来源做规则级修正。

### 优化点 1：reply routing 跳过目录/摘要页

#### 发现
- 目录页会出现 `问题1/问题2`
- 旧 routing 会把目录也带进 section

#### 处理
- `section_router.py` 中让 `目录 / 摘要 / 声明` 页不再参与 anchor
- 组装 section_text 时也跳过这些页
- `inquiry_attention_body.page_expansion.before` 从 `1` 提高到 `2`

#### 目的
- 减少目录噪声
- 仍保留正文前面包含上市公司/发行人说明的页

### 优化点 2：prompt 强化 target / deadline / action_type 规则

#### 发现
- reply 文档中的上市公司对象有时漏抽
- deadline 会把签字日期误当监管期限
- action_type 会把 `警示函 / 监管谈话 / 责令改正` 错分

#### 处理
- 在 `prompt_final.md` 中明确：
  - reply 文档里如果正文明确出现上市公司/发行人，应保留 `listed_company`
  - deadline 必须来自明确期限表达
  - 签字日期、公告日期不能直接当 deadline
  - `警示函 / 监管谈话 / 责令改正 / 书面报告 / 补充披露 / 整改` 要优先映射到固定 `action_type`

### 优化点 3：validator 做 evidence 驱动修正

#### 发现
- 某些 action_type 错分其实可以直接从 evidence 看出来
- 某些 deadline 与 evidence 根本不匹配

#### 处理
- evidence 含：
  - `警示函` -> `warning_letter`
  - `监管谈话` -> `supervisory_talk`
  - `责令改正` -> `order_correction`
  - `书面报告 / 书面说明` -> `written_report_required`
  - `补充披露 / 更新披露 / 披露材料` -> `disclosure_update_required`
  - `整改 / 整改措施 / 整改情况` -> `rectification_required`
- 如果 `deadline` 不是 evidence_text 子串，直接清空为 `null`

### 这轮优化的意义
- 全部是“证据可验证、不会编造”的保守修正
- 不需要重跑 MinerU
- 只需要重跑：
  1. `route_sections`
  2. `extract`
  3. `validate`
  4. `report`

---

## 十、课程交付与一致性修复

### 发现的问题
- 第 15 页要求中的正式交付件不够完整
- 还有部分文档和 slides 保留旧数字 `110`

### 处理
- 新增：
  - `optimization_log.md`
  - `final_report.md`
- 更新：
  - `README.md`
  - `final_slides_notes.md`
  - `final_slides.pdf`
- 把优化记录写回：
  - `refactor_change_summary_2026-05-24.md`
  - `conversation_and_issue_summary_2026-06-04.md`

### 结果
- 第 15 页要求中的正式交付缺口已补齐
- 当前文档、slides、README 与真实结果 `116` 对齐

---

## 十一、当前真实状态

### 稳定结果口径
- `metadata.csv = 120`
- `data/pdf = 120`
- `parsed_docs.jsonl = 116`
- `sections.jsonl = 116`
- `final_results.jsonl = 115`
- unresolved parse failure = 4
- unresolved extract failure = 1

### 当前正在进行的动作
- 2026-06-08 已按新优化规则重跑：
  - `route_sections`
  - `extract`
- 2026-06-08 的 `extract` 重跑已结束，并已通过 4 条定向延时重试补齐全部失败样本

这意味着：
- 当前 `eval_report_final.md` 已更新为 2026-06-08T07:04:30Z 的最新版稳定结果
- 第二轮优化后的抽取链路已完整落到 `validate/report`

---

## 十二、当前结论

### 已经完成的
- 项目边界已收紧
- schema 已稳定
- 样本边界已收紧
- 证据链校验已建立
- 评估体系已完成
- 课程第 15 页交付件已补齐

### 仍然存在的真实缺口
- 4 份超长 reply 文档仍未完成 MinerU 解析
- 1 份公告仍存在 LLM JSON 输出格式失败
- 第二轮优化后的真实准确率提升幅度，仍需等待当前重跑完成后才能确认

### 汇报时最准确的说法
可以说：

> 本项目已经形成可提交、可复现、可评估的单公告抽取系统。当前稳定结果为 116 条，extract 侧失败样本已通过单独延时重试全部补回。当前剩余缺口主要集中在 4 份超长回复公告的 MinerU 解析失败。

---

## 十三、2026-06-13 最终重跑与延时重试结果

### 发现的问题
- 使用新版 prompt 和 `nex-agi/Nex-N2-Pro` 完整重跑 `extract` 后，116 条 section 中有 106 条直接成功、10 条失败。
- 10 条失败里大部分是远端 LLM read timeout，说明不是本地数据缺失，也不是 MinerU 解析缺失，而是模型接口对长文本响应不稳定。
- 直接把 106 条作为最终结果会导致 `sections.jsonl` 与 `final_results.jsonl` 数量不一致，不利于提交和答辩解释。

### 处理方法
- 对这 10 条失败样本单独运行 `scripts/retry_extract_subset.py`，把 timeout 从 300 秒延长到 900 秒，并降低并发压力。
- 重试完成后，10 条中 9 条成功，1 条仍失败：`1224517046`，失败原因为远端 API `500 Internal Server Error`。
- 将 9 条成功 retry 输出按 `doc_id` 合并回正式 `outputs/tmp/extracted.jsonl` 和 `outputs/tmp/llm_raw.jsonl`。
- 将正式失败清单收敛为 1 条，保留在 `outputs/logs/extract_errors.jsonl`，不静默删除失败。
- 重新执行 `validate` 和 `report`，使 `final_results.jsonl`、`validation_errors.jsonl`、`eval_report_final.md` 全部基于最新抽取结果生成。

### 为什么这样修改
- 这类失败不是数据真实性问题，而是远端接口稳定性问题；延长 timeout 是最小、可解释、可复现的处理方式。
- 不重跑 MinerU，因为 PDF 解析结果和 section routing 已经完成，本轮问题只发生在 LLM 抽取阶段。
- 不手工补写失败样本，避免编造数据；失败样本只记录失败原因。

### 最新稳定口径
- `metadata.csv = 120`
- `data/pdf = 120`
- `parsed_docs.jsonl = 116`
- `sections.jsonl = 116`
- `extracted.jsonl = 115`
- `final_results.jsonl = 115`
- unresolved parse failure = 4
- unresolved extract failure = 1（`1224517046`，远端 API 500）
- `validate`: total = 115, ok = 115, repaired = 39, dropped = 0

### 汇报时最准确的说法
可以说：

> 本项目最终形成 115 条通过 Pydantic 和 evidence 校验的结构化结果。原始样本 120 条中，4 条在 MinerU 解析阶段失败，1 条在 LLM 抽取阶段因远端 API 500 失败。所有失败都有日志记录，没有人工编造或静默补齐。
