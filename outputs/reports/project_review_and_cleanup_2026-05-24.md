# Project Review And Cleanup Report

Date: 2026-05-24

## 审查目标
本次审查的目的有 4 个：

1. 检查当前项目是否符合课程目标与提交要求  
2. 检查工作目录与桌面提交目录是否一致  
3. 删除已经不属于最新版的旧文件、旧副本、旧占位内容  
4. 在清理前对关键数据做备份，避免误覆盖

本次审查**不重新运行 download / parse / extract**，只针对现有项目产物、文档、提交材料和一致性做核查与清理。

---

## 一、备份与防覆盖

为避免后续清理或同步误覆盖现有数据，已先创建两份快照备份：

- 工作目录备份：`/Users/wjy/Documents/Codex project/学术/backups/final_repo_snapshot_20260524_155334.tar.gz`
- 桌面提交目录备份：`/Users/wjy/Desktop/final_repo_submission_2026-05-24_backup_20260524_155334.tar.gz`

备份说明：
- 工作目录备份排除了 `.env`
- 桌面提交目录本身不包含 `.env`
- 备份完成后，才开始执行旧文件删除与目录同步

---

## 二、审查结果总览

### 1. 课程提交要求完整性
按 `submission_checklist/week16_submit_list.md` 对照检查，当前必需材料齐全：

- required_count: `24`
- present: `24`
- missing: `0`

结论：**提交清单层面没有缺件**。

### 2. 当前真实项目产物
- `data/metadata/metadata.csv`: `120` 条
- `data/pdf/`: `120` 份 PDF
- `data/parsed/parsed_docs.jsonl`: `116` 条
- `data/parsed/sections.jsonl`: `116` 条
- `outputs/results/final_results.jsonl`: `110` 条
- `outputs/reports/manual_eval_filled_single_announcement.csv`: `20` 篇样本、`105` 行字段评估

结论：**数据链条完整，且与最终报告口径一致**。

### 3. 工作目录与桌面提交目录一致性
已用带删除同步和 dry-run 复核：

- 工作目录：`/Users/wjy/Documents/Codex project/学术/final_repo`
- 桌面提交目录：`/Users/wjy/Desktop/final_repo_submission_2026-05-24`

一致性检查结果：
- `rsync -ani --delete ...` 无输出
- `final_results.jsonl` 两边均为 `110` 行

结论：**两份目录当前已经同版**。

---

## 三、发现的问题与处理动作

## 1. `final_slides.pdf` 是旧版内容

### 发现的问题
审查 `final_slides.pdf` 文本后发现，它仍然是早期版本，内容中还保留了：

- “评估（全量跑完后填真实数值）”
- 旧的项目标题口径
- 未包含当前 `110` 条结果和字段级人工评估数字

这意味着它不是最新版交付材料，和当前仓库其他内容不一致。

### 处理动作
- 保留最新讲稿源文件 `final_slides_notes.md`
- 基于该讲稿重新生成了新的 `final_slides.pdf`
- 新 PDF 现为 10 页，内容已替换为当前真实结果

### 为什么这样处理
`final_slides.pdf` 是课程明确要求的提交件，不能简单删除。  
因此这里不是“删掉旧文件”，而是“用最新版内容覆盖旧版 PDF”。

### 处理后结果
新的 `final_slides.pdf` 已包含：
- 单公告抽取口径
- `metadata=120 / parsed=116 / final_results=110`
- 字段级人工评估结果
- 当前 demo 样本 `doc_id=1225290815`

---

## 2. 存在早期占位文件 `topic_propsol.md`

### 发现的问题
项目根目录里有一个：

- `topic_propsol.md`

该文件只是一个拼写错误的占位说明，不是正式提交文件。正式版本是：

- `topic_proposal.md`

如果保留它，容易让审阅者误以为目录中存在两份 proposal，或者误判哪个是正式文件。

### 处理动作
- 已从工作目录删除 `topic_propsol.md`
- 已同步从桌面提交目录删除

### 为什么这样处理
它不属于最新版内容，也不属于课程要求的正式交付物，保留只会增加混淆。

---

## 3. 存在旧版代码审查遗留文件 `code_review_issues.md`

### 发现的问题
`outputs/reports/code_review_issues.md` 是 2026-05-12 extract 运行期间的旧审查记录，内容包括：

- `prompt_final` 未作为默认 prompt
- reporter evidence 计数问题
- merge 顺序问题
- section_router 页码边界问题

其中多项问题在后续版本中已经修复。继续保留这个文件，会出现两个问题：

- 它会给人一种“这些问题仍然未修”的错觉
- 它与当前真实代码状态不一致

### 处理动作
- 已从工作目录删除 `outputs/reports/code_review_issues.md`
- 已同步从桌面提交目录删除

### 为什么这样处理
这是旧状态文件，不属于最新版内容。  
当前应以新的：
- `refactor_change_summary_2026-05-24.md`
- `project_review_and_cleanup_2026-05-24.md`

作为最新审查说明。

---

## 4. 桌面存在旧提交副本

### 发现的问题
桌面原先同时存在：

- `final_repo_submission_2026-05-13`
- `final_repo_submission_2026-05-13.zip`
- `final_repo_submission_2026-05-24`

这会带来非常直接的风险：
- 提交时拿错版本
- 审阅时误看旧版
- 把 104 条结果版本和 110 条结果版本混淆

### 处理动作
已删除桌面旧副本：

- `/Users/wjy/Desktop/final_repo_submission_2026-05-13`
- `/Users/wjy/Desktop/final_repo_submission_2026-05-13.zip`

保留：

- `/Users/wjy/Desktop/final_repo_submission_2026-05-24`
- `/Users/wjy/Desktop/final_repo_submission_2026-05-24_backup_20260524_155334.tar.gz`

### 为什么这样处理
桌面用于“提交和审阅”的目录应该只有一个最新版主目录。  
旧版目录继续留着，只会制造版本错拿风险。

---

## 5. 运行缓存文件不应进入最终提交口径

### 发现的问题
工作目录里存在：

- `__pycache__/`
- `src/__pycache__/`

虽然这类文件不影响运行，但它们不属于项目正式内容，也不应作为提交材料的一部分。

### 处理动作
- 已从工作目录删除 `__pycache__`
- 同步后桌面提交目录中也没有相关缓存目录

### 为什么这样处理
它们是运行时产物，不属于最新版项目内容，也没有审阅价值。

---

## 四、当前保留但未删除的内容说明

有些文件虽然不是课程“必交件”，但仍然保留，因为它们属于**当前版本的有效辅助材料**，不是旧内容：

- `outputs/reports/pre_extract_alignment_review.md`
- `outputs/reports/refactor_change_summary_2026-05-24.md`
- `outputs/reports/manual_eval_review_packet.md`
- `outputs/reports/manual_eval_sample_ids.txt`
- `outputs/reports/self_review.md`
- `final_slides_notes.md`

保留理由：
- 它们都与当前版本一致
- 它们服务于复核、答辩或解释项目修改过程
- 不会和正式提交件冲突

---

## 五、安全与提交状态

### 桌面提交目录
- `.env`: **不存在**
- `topic_propsol.md`: **不存在**
- `code_review_issues.md`: **不存在**
- `final_results.jsonl`: `110` 行

结论：**桌面提交目录已经是干净的最新版提交副本**。

### 工作目录
- `.env`: **仍然存在**

说明：
- 这是本地运行用密钥文件
- 它没有被同步到桌面提交目录
- 如果最终你决定直接打包工作目录而不是桌面提交目录，提交前仍然必须手动删除 `.env`

---

## 六、审查结论

本轮审查后的结论是：

### 1. 符合目标与要求
当前项目已经满足：
- 单公告抽取口径
- cninfo 真实数据约束
- 结构化 schema + evidence 校验
- 字段级人工评估
- Week16 提交清单完整性

### 2. 已清理掉明确不是最新版的内容
已删除：
- `topic_propsol.md`
- `outputs/reports/code_review_issues.md`
- 旧桌面副本 `final_repo_submission_2026-05-13`
- 旧桌面压缩包 `final_repo_submission_2026-05-13.zip`
- `__pycache__` 缓存目录

### 3. 已修正必须更新而不能删除的内容
已更新：
- `final_slides.pdf`

### 4. 项目目录与桌面提交目录已经同步一致
当前：
- 工作目录是最新版
- 桌面提交目录也是最新版
- 两者除 `.env` 外保持同版

---

## 七、建议的最终使用方式

如果你接下来要提交或自己审阅，优先使用：

- `/Users/wjy/Desktop/final_repo_submission_2026-05-24`

原因：
- 它不含 `.env`
- 已删掉旧版副本
- 已同步最新版 `final_slides.pdf`
- 已与当前工作目录对齐

如果后续你还要继续本地运行 pipeline，继续使用工作目录：

- `/Users/wjy/Documents/Codex project/学术/final_repo`

但要注意：
- 工作目录仍保留 `.env`
- 不应直接把工作目录原样打包提交
