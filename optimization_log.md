# Optimization Log

本文件用于对应课程第 15 页中“prompt / schema / section rules / workflow 优化记录”的要求。

## Round 1: 题目边界与结构化重构（2026-05-24）

### 发现的问题
- 项目边界容易被误解为“问询函—回复闭环”
- schema 过粗，不利于统计和字段级评估
- metadata 里混入附件型文本
- section routing 在 reply 文档上容易受目录页干扰

### 优化动作
- 锁定为单公告抽取
- 升级 `targets / issues / actions` schema
- 增加 `target_type / issue_type / action_type` 白名单
- 收紧标题过滤与去重
- 引入字段级人工评估口径

### 结果
- 项目口径、代码和评估一致
- 可以稳定输出结构化统计

## Round 2: `action_source_type` 与 reply 口径增强（2026-06-01）

### 发现的问题
- `actions[]` 无法区分“监管要求”与“公司承诺”
- reply 文档容易被误解为在做闭环匹配

### 优化动作
- 增加 `action_source_type`
- 在 prompt 中明确：reply 只抽当前公告，不回指原函

### 结果
- actions 的解释性增强
- reply 文档边界更清楚

## Round 3: 错误驱动优化（2026-06-08）

### 触发依据
- 人工评估主要错误集中在：
  - `target_missing`
  - `doc_type_wrong`
  - `action_requirement_confused`
  - `action_type_misclassified`

### 具体优化
#### 1. Section routing
- inquiry/reply 路由时跳过 `目录 / 声明 / 摘要` 页，不再让目录页参与 anchor 匹配
- `inquiry_attention_body.page_expansion.before` 从 `1` 调整为 `2`

目的：
- 减少 reply 文档第一页目录/问题目录对路由的干扰
- 同时保留正文前面的公司/监管对象说明页

#### 2. Prompt 优化
- 强化规则：reply 文档中只要明确出现上市公司/发行人/上市公司，就应保留 `listed_company` target
- 强化规则：`deadline` 只能来自明确期限表达，不能把签字日期当 deadline
- 强化规则：`警示函 / 监管谈话 / 责令改正 / 书面报告 / 补充披露 / 整改` 对应固定 action_type
- 强化规则：不把延期回复的泛化原因当成“主要监管问题”

#### 3. Validator 优化
- 基于 evidence 关键词修正明显错误的 `action_type`
- 对 evidence 不支持的 `deadline` 直接清空

### 为什么这样改
- 这些修改都属于“证据可验证、规则可解释、不会编造新信息”的保守优化
- 不需要重跑 MinerU，只需重跑 `route_sections -> extract -> validate -> report`

### 当前判断
- 这轮优化尚未重新跑全量 extract，因此还不能宣称准确率已经提高
- 但从错误类型分布看，这几项优化直接针对了当前最主要的错误来源

## 详细过程记录
- 详细决策说明：`outputs/reports/refactor_change_summary_2026-05-24.md`
- 本轮问题与处理：`outputs/reports/conversation_and_issue_summary_2026-06-04.md`
