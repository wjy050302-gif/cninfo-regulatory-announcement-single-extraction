# Final Report

## 1. 项目题目
cninfo 监管公告单公告结构化抽取（标准档 1.0）

## 2. 项目目标
本项目针对巨潮资讯网公开披露的监管类公告，构建一个可复现、可检查的端到端结构化抽取流程。目标是从单篇公告中抽取：
- 监管对象
- 问题点
- 监管动作与要求
- 对应 evidence/page_no 证据链

项目边界为：
- 单公告抽取
- 一条记录 = 一份公告
- 不做问询函—回复跨公告闭环匹配
- `reply` 类公告只处理当前公告文本本身

## 3. 数据来源与范围
- 数据源：cninfo 公开公告接口 + cninfo 公告 PDF
- 时间范围：2023-01-01 ~ 2026-05-11
- 市场：沪深两市
- 标题过滤：问询/关注函、回复、监管措施、警示函、整改报告
- 附件排除：募集说明书、法律意见书、核查意见等附件型文档

## 4. 方法
完整流程为：
1. `collect`：抓取 metadata
2. `download`：下载 PDF
3. `parse`：通过 MinerU API 解析整份 PDF
4. `route_sections`：定位目标正文 section
5. `extract`：LLM 按 schema 抽取结构化字段
6. `validate`：做 evidence/page_no 与枚举合法性校验
7. `report`：生成评估报告

### 关键真实性约束
- 仅使用 cninfo metadata、cninfo PDF 和 MinerU 解析文本
- 无证据则输出 `null` 或空列表
- `evidence_text` 必须是 routed section 原文子串
- 不允许用本地 PDF fallback 替代 MinerU

## 5. Schema
顶层字段：
- `doc_id / stock_code / stock_name / market / publish_date / announcement_title / doc_type / source`

嵌套字段：
- `targets[]`: `name / role / target_type / evidence`
- `issues[]`: `issue_type / issue_summary / is_violation_related / evidence`
- `actions[]`: `action_type / action_source_type / deadline / required_disclosure / evidence`

## 6. 当前真实结果
- `metadata.csv`: 120
- `data/pdf/`: 120
- `data/parsed/parsed_docs.jsonl`: 116
- `data/parsed/sections.jsonl`: 116
- `outputs/results/final_results.jsonl`: 115

说明：
- MinerU `parse` 仍有 4 份超时失败
- `extract` 首轮新版重跑为 106 条成功，之后对 10 条失败样本做 900 秒延时重试
- 延时重试补回 9 条，剩余 1 条 `1224517046` 为远端 LLM API 500 失败
- 最终 115 条进入 `validate`，全部通过 Pydantic、evidence 和 page_no 校验

## 7. 评估结果
人工评估样本：20 篇 PDF，105 行字段级标注

准确率：
- `doc_type`: 80.0%
- `regulator_name`: 100.0%
- `targets`: 77.8%
- `issues`: 85.0%
- `actions`: 87.5%
- `evidence_correct`: 87.1%

主要错误类型：
- `target_missing`
- `doc_type_wrong`
- `action_type_misclassified`
- `action_requirement_confused`

详细报告见：
- `outputs/reports/eval_report_final.md`

## 8. 优化过程
本项目经历了三轮主要优化：
- 2026-05-24：重构项目边界、schema、样本过滤与评估口径
- 2026-06-01：处理 `extract` 超时与 `action_source_type`
- 2026-06-08：针对人工评估中的主要误差做错误驱动优化

本轮（2026-06-08）优化重点：
- reply 路由跳过目录页
- prompt 强化 listed_company / deadline / action_type 规则
- validator 基于 evidence 修正明显错误的 action_type，并清除无证据支持的 deadline

详见：
- `optimization_log.md`
- `outputs/reports/refactor_change_summary_2026-05-24.md`

## 9. 限制
- 4 份超长回复公告仍未完成 MinerU 解析
- 1 份公告仍存在 LLM JSON 输出格式失败
- 当前项目不做跨公告闭环匹配，因此不回答“是否逐项回应原函”

## 10. 可复现性
统一入口：

```bash
python pipeline_run.py --step collect
python pipeline_run.py --step download
python pipeline_run.py --step audit
python pipeline_run.py --step parse
python pipeline_run.py --step route_sections
python pipeline_run.py --step extract
python pipeline_run.py --step validate
python pipeline_run.py --step report
```

如果只应用本轮优化后的重新抽取，不需要重跑 MinerU；只需：

```bash
python pipeline_run.py --step route_sections
python pipeline_run.py --step extract
python pipeline_run.py --step validate
python pipeline_run.py --step report
```
