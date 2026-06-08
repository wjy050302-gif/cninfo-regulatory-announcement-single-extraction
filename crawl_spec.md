# Crawl Spec (cninfo only)

## 数据源
仅使用巨潮资讯网（cninfo）公开接口与公开 PDF：

- 公告检索：`https://www.cninfo.com.cn/new/hisAnnouncement/query`
- PDF 下载：`http://static.cninfo.com.cn/<adjunctUrl>`

## 项目口径
- 单公告抽取
- 一条记录 = 一份公告 PDF
- 不做“问询函—回复”跨公告闭环匹配

## 抓取范围（可复现）
配置写死在 `configs/crawl_config.yaml`：

- 市场：`column in ["szse", "sse"]`
- 时间：`seDate = "2023-01-01~2026-05-11"`
- 目标规模：`max_records = 120`

## 查询关键词（召回）
- 问询/关注函正文：`关注函`、`问询函`、`审核问询`、`年报问询`
- 回复类公告：`回复`、`回函`、`延期回复`
- 监管措施相关：`行政监管措施`、`监管措施决定书`、`警示函`、`责令改正`、`监管谈话`、`整改报告`

## 标题过滤规则（入样本）
保留标题明确命中以下语境的公告：

- `attention_letter`: `关注函`
- `inquiry_letter`: `问询函`、`审核问询`、`年报问询`
- `reply`: `回复`、`回函`、`延期回复`（只作为单篇回复公告抽取，不做跨公告闭环）
- `regulatory_measure`: `行政监管措施`、`监管措施决定书`、`警示函`、`责令改正`、`监管谈话`、`整改报告`

排除词：
- `募集说明书`
- `发行保荐书`
- `上市保荐书`
- `法律意见书`
- `评级报告`
- `摘要`
- `英文版`
- `补充法律意见书`

覆盖规则：
- 若标题既包含排除词，又明显属于 `reply` / `regulatory_measure` 语境，则保留

补充收敛规则（避免偏题附件）：
- 对 `attention_letter / inquiry_letter / reply` 类标题，若同时命中以下词，则排除：
  - `提示性公告`
  - `申请文件更新`
  - `募集说明书`
  - `法律意见书`
  - `专项说明`
  - `核查意见`
  - `律师事务所`
  - `会计师事务所`
- 目的：剔除募集说明书更新提示、律师/会计师单独回复、专项说明等附件型公告，保留更接近公司主体监管正文的文本。

## 去重规则
- 先按 `doc_id` 去重
- 再按 `pdf_url` 去重
- 同一公告若命中多个查询词，则合并为一条 metadata，并写入 `matched_search_keys`

## 合规与限速
- 不绕过登录 / 验证码 / 访问限制
- 接口偶发 5xx / 超时属于正常情况：实现重试与 sleep，失败写日志
- 域名白名单：仅允许下载 `static.cninfo.com.cn` 的 PDF

## 输出
- `data/metadata/metadata.csv`

必备字段：
- `doc_id`
- `stock_code`
- `stock_name`
- `market`
- `publish_date`
- `announcement_title`
- `announcement_type`
- `title_rule_doc_type`
- `pdf_url`
- `search_key`
- `matched_search_keys`
- `download_status`
- `local_pdf_path`
