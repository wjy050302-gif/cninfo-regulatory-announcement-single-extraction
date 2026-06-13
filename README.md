# cninfo 监管公告单公告结构化抽取（标准档 1.0）

本项目实现一个可复现、可检查的端到端流水线：

1. 从巨潮资讯网公开接口抓取监管类公告 metadata
2. 下载公开 PDF（仅允许 `static.cninfo.com.cn`）
3. 用 MinerU API 解析 PDF 并保留页码
4. 做 section routing + section checking
5. 用 LLM 按固定 schema 抽取 `regulator_name / targets / issues / actions`
6. 用 validator 做 evidence 子串与 page_no 校验
7. 输出 `final_results.jsonl` 与 `eval_report_final.md`

## 项目边界
- 单公告抽取
- 一条记录 = 一份公告
- 不做“问询函—回复”跨公告闭环匹配
- `reply` 公告只抽取当前回复文本中出现的问题、要求和整改动作

## 目录结构
- `pipeline_run.py`：统一入口
- `configs/`：抓取、模型、section、workflow 配置
- `src/`：实现代码
- `prompts/`：抽取 prompt
- `data/metadata/metadata.csv`：可追溯 metadata
- `data/pdf/`：下载的 PDF
- `data/parsed/`：MinerU 解析结果
- `outputs/results/final_results.jsonl`：最终结构化结果
- `outputs/reports/eval_report_final.md`：最终报告

## 环境准备
推荐 Python 3.11：

```bash
pip install -r requirements.txt
```

需要真实密钥时：

```bash
cp .env.example .env
```

填写：
- `MINERU_API_KEY`
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`

## 快速开始
先跑不依赖密钥的步骤：

```bash
python pipeline_run.py --step collect --limit 10
python pipeline_run.py --step download --limit 10
python pipeline_run.py --step audit
```

全量流程：

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

## 当前全量结果摘要
- `metadata.csv`: 120 条
- `data/pdf/`: 120 份 PDF
- `data/parsed/parsed_docs.jsonl`: 116 条解析成功
- `data/parsed/sections.jsonl`: 116 条 section
- `outputs/results/final_results.jsonl`: 115 条通过证据校验的最终结果
- `outputs/logs/extract_errors.jsonl`: 1 条远端 LLM API 500 失败记录
- `outputs/reports/manual_eval_filled_single_announcement.csv`: 20 篇样本、105 行字段级人工评估
- `outputs/reports/eval_report_final.md`: 最终五类指标 + 错误分析报告
- `optimization_log.md`: prompt / routing / validator 的优化记录
- `final_report.md`: 最终报告（整合项目目标、方法、结果、评估与限制）

## 数据真实性规则
- 仅使用 cninfo metadata + cninfo PDF + MinerU 解析文本
- 无证据时输出 `null` 或空列表
- `evidence_text` 必须来自输入 section 原文
- `target_type / issue_type / action_type / action_source_type` 必须落在白名单内
- 不提交 `.env`，只保留 `.env.example`
