# Output Sample

下面展示 `outputs/results/final_results.jsonl` 中单条记录的预期结构（示意，不包含真实抽取值）。

```json
{
  "doc_id": "1222674723",
  "stock_code": "300437",
  "stock_name": "清水源",
  "market": "szse",
  "publish_date": "2025-02-28",
  "announcement_title": "关于对深圳证券交易所关注函涉及事项的进展公告",
  "doc_type": "attention_letter",
  "regulator_name": {
    "value": "深圳证券交易所",
    "evidence": {
      "evidence_text": "深圳证券交易所",
      "page_no": 1
    }
  },
  "targets": [
    {
      "name": "清水源",
      "role": "公司",
      "target_type": "listed_company",
      "evidence": {
        "evidence_text": "清水源",
        "page_no": 1
      }
    }
  ],
  "issues": [
    {
      "issue_type": "information_disclosure",
      "issue_summary": "未按要求及时披露相关事项",
      "is_violation_related": true,
      "evidence": {
        "evidence_text": "未按要求及时披露相关事项",
        "page_no": 2
      }
    }
  ],
  "actions": [
    {
      "action_type": "inquiry_reply_required",
      "action_source_type": "regulator_required",
      "deadline": "2025-03-05",
      "required_disclosure": true,
      "evidence": {
        "evidence_text": "请于2025年3月5日前回复并履行信息披露义务",
        "page_no": 2
      }
    }
  ],
  "source": {
    "url": "http://static.cninfo.com.cn/finalpage/2025-02-28/1222674723.PDF",
    "pdf_url": "http://static.cninfo.com.cn/finalpage/2025-02-28/1222674723.PDF"
  }
}
```

关键约束：
- `evidence_text` 必须是输入 `section_text` 的原文子串
- `page_no` 可得则填（1-based），不可得则 `null`
- `target_type / issue_type / action_type / action_source_type` 必须来自白名单
- 无法确定则输出 `null` 或空列表，不推断补全
