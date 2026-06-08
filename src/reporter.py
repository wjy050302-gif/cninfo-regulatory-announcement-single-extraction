from __future__ import annotations

from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
from typing import Any

from .csv_store import read_csv_dicts
from .logger import JsonlLogger
from .self_review import write_self_review
from .utils import ensure_parent_dir, utc_now_iso


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    n = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except Exception:
        return path.as_posix()


def _read_section_check_stats(csv_path: Path) -> dict[str, Any]:
    """Parse section_check_report.csv and return routing stats."""
    stats: dict[str, Any] = {
        "total_rows": 0,
        "unique_docs": set(),
        "found": 0,
        "not_found": 0,
        "too_short": 0,
        "ok": 0,
    }
    if not csv_path.exists():
        return stats
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["total_rows"] += 1
            stats["unique_docs"].add(row.get("doc_id", ""))
            found = row.get("found", "0").strip() == "1"
            qi = row.get("quality_issue", "").strip()
            if found:
                stats["found"] += 1
                if qi == "too_short":
                    stats["too_short"] += 1
                elif not qi:
                    stats["ok"] += 1
            else:
                stats["not_found"] += 1
    stats["unique_doc_count"] = len(stats["unique_docs"])
    # Do not return sets (not JSON-serializable, and noisy in logs/reports).
    stats.pop("unique_docs", None)
    return stats


def _read_final_results_stats(jsonl_path: Path) -> dict[str, Any]:
    """Analyze final_results.jsonl for fill rates, enum distributions, and evidence stats."""
    field_fill: dict[str, int] = {}
    field_total: dict[str, int] = {}
    evidence_with_page: int = 0
    evidence_total: int = 0
    doc_count: int = 0
    doc_type_counts: dict[str, int] = {}
    target_type_counts: dict[str, int] = {}
    issue_type_counts: dict[str, int] = {}
    action_type_counts: dict[str, int] = {}
    action_source_type_counts: dict[str, int] = {}
    item_counts = {"targets": 0, "issues": 0, "actions": 0}
    bool_counts = {
        "issues.true": 0,
        "issues.false": 0,
        "issues.null": 0,
        "actions.true": 0,
        "actions.false": 0,
        "actions.null": 0,
    }

    if not jsonl_path.exists():
        return {"doc_count": 0}

    target_fields = [
        "regulator_name",
        "targets",
        "issues",
        "actions",
    ]

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            doc_count += 1
            obj = json.loads(line)
            dt = obj.get("doc_type", "unknown")
            doc_type_counts[dt] = doc_type_counts.get(dt, 0) + 1

            for field in target_fields:
                field_total[field] = field_total.get(field, 0) + 1
                val = obj.get(field)
                if val is not None and val != [] and val != "":
                    field_fill[field] = field_fill.get(field, 0) + 1

            # Count evidence objects and page_no coverage
            def _count_evidence_in(obj: Any) -> None:
                nonlocal evidence_total, evidence_with_page
                if isinstance(obj, dict):
                    ev = obj.get("evidence")
                    if isinstance(ev, dict) and ev.get("evidence_text"):
                        evidence_total += 1
                        if ev.get("page_no") is not None:
                            evidence_with_page += 1
                if isinstance(obj, list):
                    for item in obj:
                        _count_evidence_in(item)

            for field in target_fields:
                val = obj.get(field)
                if val is None:
                    continue
                if isinstance(val, list):
                    for item in val:
                        _count_evidence_in(item)
                        if field == "targets" and isinstance(item, dict):
                            item_counts["targets"] += 1
                            tt = item.get("target_type")
                            if isinstance(tt, str) and tt:
                                target_type_counts[tt] = target_type_counts.get(tt, 0) + 1
                        elif field == "issues" and isinstance(item, dict):
                            item_counts["issues"] += 1
                            it = item.get("issue_type")
                            if isinstance(it, str) and it:
                                issue_type_counts[it] = issue_type_counts.get(it, 0) + 1
                            ivr = item.get("is_violation_related")
                            if ivr is True:
                                bool_counts["issues.true"] += 1
                            elif ivr is False:
                                bool_counts["issues.false"] += 1
                            else:
                                bool_counts["issues.null"] += 1
                        elif field == "actions" and isinstance(item, dict):
                            item_counts["actions"] += 1
                            at = item.get("action_type")
                            if isinstance(at, str) and at:
                                action_type_counts[at] = action_type_counts.get(at, 0) + 1
                            ast = item.get("action_source_type")
                            if isinstance(ast, str) and ast:
                                action_source_type_counts[ast] = action_source_type_counts.get(ast, 0) + 1
                            rd = item.get("required_disclosure")
                            if rd is True:
                                bool_counts["actions.true"] += 1
                            elif rd is False:
                                bool_counts["actions.false"] += 1
                            else:
                                bool_counts["actions.null"] += 1
                elif isinstance(val, dict):
                    _count_evidence_in(val)

    return {
        "doc_count": doc_count,
        "doc_type_counts": doc_type_counts,
        "field_fill": field_fill,
        "field_total": field_total,
        "evidence_total": evidence_total,
        "evidence_with_page": evidence_with_page,
        "item_counts": item_counts,
        "target_type_counts": target_type_counts,
        "issue_type_counts": issue_type_counts,
        "action_type_counts": action_type_counts,
        "action_source_type_counts": action_source_type_counts,
        "bool_counts": bool_counts,
    }


def _to_int(value: str) -> int | None:
    try:
        return int(str(value).strip())
    except Exception:
        return None


def _read_manual_eval_stats(csv_path: Path) -> dict[str, Any]:
    if not csv_path.exists():
        return {}

    rows = list(csv.DictReader(open(csv_path, "r", encoding="utf-8")))
    if not rows:
        return {}

    scored_rows = [r for r in rows if str(r.get("is_correct") or "").strip() != ""]
    if not scored_rows:
        return {}

    groups = {
        "doc_type": lambda f: f == "doc_type",
        "regulator_name": lambda f: f.startswith("regulator_name"),
        "targets": lambda f: f.startswith("targets"),
        "issues": lambda f: f.startswith("issues"),
        "actions": lambda f: f.startswith("actions"),
    }

    group_stats: dict[str, dict[str, int]] = {k: {"ok": 0, "total": 0} for k in groups}
    error_counts: Counter[str] = Counter()
    wrong_examples: list[dict[str, str]] = []

    evidence_total = 0
    evidence_ok = 0
    total_ok = 0

    for r in scored_rows:
        field_name = str(r.get("field_name") or "")
        is_correct = _to_int(str(r.get("is_correct") or ""))
        evidence_correct = _to_int(str(r.get("evidence_correct") or ""))
        if is_correct is None:
            continue

        total_ok += is_correct
        if evidence_correct is not None:
            evidence_total += 1
            evidence_ok += evidence_correct

        matched_group = None
        for group_name, fn in groups.items():
            if fn(field_name):
                matched_group = group_name
                break
        if matched_group:
            group_stats[matched_group]["total"] += 1
            group_stats[matched_group]["ok"] += is_correct

        if is_correct == 0:
            err = str(r.get("error_type") or "unknown")
            error_counts[err] += 1
            if len(wrong_examples) < 5:
                wrong_examples.append(
                    {
                        "doc_id": str(r.get("doc_id") or ""),
                        "field_name": field_name,
                        "error_type": err,
                        "notes": str(r.get("notes") or ""),
                    }
                )

    return {
        "row_count": len(rows),
        "sample_doc_count": len({str(r.get("doc_id") or "") for r in rows if str(r.get("doc_id") or "").strip()}),
        "group_stats": group_stats,
        "overall_ok": total_ok,
        "overall_total": len(scored_rows),
        "evidence_ok": evidence_ok,
        "evidence_total": evidence_total,
        "error_counts": dict(error_counts),
        "wrong_examples": wrong_examples,
    }


def _read_pipeline_stability(log_path: Path) -> dict[str, Any]:
    """Read sample_run_log.jsonl and compute per-step success/failure rates."""
    step_stats: dict[str, dict[str, int]] = {}
    if not log_path.exists():
        return step_stats
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            step = obj.get("step", "")
            level = obj.get("level", "")
            if not step:
                continue
            if step not in step_stats:
                step_stats[step] = {"info": 0, "error": 0, "warn": 0}
            if level in step_stats[step]:
                step_stats[step][level] += 1
    return step_stats


def write_eval_report(
    *,
    metadata_csv: Path,
    dataset_audit_md: Path,
    parsed_jsonl: Path,
    section_check_csv: Path,
    extracted_jsonl: Path,
    final_results_jsonl: Path,
    validation_errors_jsonl: Path,
    out_report_md: Path,
    logger: JsonlLogger,
) -> Path:
    rows = read_csv_dicts(metadata_csv)
    total_meta = len(rows)

    parsed_n = _count_jsonl(parsed_jsonl)
    extracted_n = _count_jsonl(extracted_jsonl)
    final_n = _count_jsonl(final_results_jsonl)
    val_err_n = _count_jsonl(validation_errors_jsonl)

    section_stats = _read_section_check_stats(section_check_csv)
    result_stats = _read_final_results_stats(final_results_jsonl)
    manual_eval_csv = out_report_md.parent / "manual_eval_filled_single_announcement.csv"
    manual_eval_stats = _read_manual_eval_stats(manual_eval_csv)

    # Read run log for pipeline stability
    log_path = out_report_md.parent.parent / "logs" / "sample_run_log.jsonl"
    pipeline_stats = _read_pipeline_stability(log_path)

    ensure_parent_dir(out_report_md)

    lines: list[str] = []
    lines.append(f"# Eval Report (Final) ({utc_now_iso()})")
    lines.append("")
    lines.append("本报告覆盖课程要求五类指标：数据质量、Section 质量、抽取质量、证据质量、Pipeline 稳定性。")
    lines.append("")

    # --- 1. Dataset Quality ---
    lines.append("## 1. 数据质量 (Data Quality)")
    lines.append(f"- `metadata.csv` 记录数: **{total_meta}**")
    lines.append(f"- 数据来源: cninfo 巨潮资讯网公开公告查询接口")
    lines.append(f"- 时间范围: 2023-01-01 ~ 2026-05-11")
    lines.append(f"- 市场: 沪深两市（sse + szse）")
    lines.append(f"- 项目口径: 单公告抽取（不做问询函—回复跨公告闭环匹配）")
    lines.append(f"- 查询关键词按标题规则扩展到问询/关注函、回复、监管措施、整改报告等")
    lines.append(f"- 难度档位: 标准档 1.0（目标 120 份 PDF）")
    lines.append(f"- audit report: `{_rel(dataset_audit_md)}`")
    lines.append("")

    # --- 2. Parsing (MinerU) ---
    lines.append("## 2. PDF 解析 (MinerU)")
    lines.append(f"- parsed docs (jsonl): **{parsed_n}** (`{_rel(parsed_jsonl)}`)")
    lines.append(f"- parse 抽查: 见 `outputs/reports/parse_check.md`（至少 5 份样本）")
    lines.append("- 强约束: 无真实 `MINERU_API_KEY` 或解析为空时直接退出，不允许 fallback")
    lines.append("")
    parse_rate = f"{parsed_n / total_meta * 100:.1f}%" if total_meta else "N/A"
    lines.append(f"- 解析成功率: {parse_rate}（{parsed_n}/{total_meta}）")
    lines.append("")

    # --- 3. Section Routing & Checking ---
    lines.append("## 3. Section Routing & Checking")
    lines.append(f"- section check report: `{_rel(section_check_csv)}`")
    sec_total = section_stats.get("total_rows", 0)
    sec_docs = section_stats.get("unique_doc_count", 0)
    sec_found = section_stats.get("found", 0)
    sec_not_found = section_stats.get("not_found", 0)
    sec_too_short = section_stats.get("too_short", 0)
    sec_ok = section_stats.get("ok", 0)
    lines.append(f"- 处理文档数: **{sec_docs}**（共 {sec_total} 行 routing 记录）")
    if sec_total > 0:
        lines.append(f"- found rate: {sec_found / sec_total * 100:.1f}%（{sec_found}/{sec_total}）")
        lines.append(f"- not_found rate: {sec_not_found / sec_total * 100:.1f}%（{sec_not_found}/{sec_total}）")
        lines.append(f"- too_short rate: {sec_too_short / sec_total * 100:.1f}%（{sec_too_short}/{sec_total}）")
        lines.append(f"- ok rate: {sec_ok / sec_total * 100:.1f}%（{sec_ok}/{sec_total}）")
    lines.append("")

    # --- 4. Extraction (LLM + Pydantic) ---
    lines.append("## 4. 抽取质量 (Extraction Quality)")
    lines.append(f"- extracted (Pydantic 通过) 记录: **{extracted_n}** (`{_rel(extracted_jsonl)}`)")
    lines.append(f"- final results (经证据校验): **{final_n}** (`{_rel(final_results_jsonl)}`)")
    lines.append(f"- validation errors/repairs: **{val_err_n}** (`{_rel(validation_errors_jsonl)}`)")
    lines.append("")

    # Doc type distribution
    doc_type_counts = result_stats.get("doc_type_counts", {})
    if doc_type_counts:
        lines.append("### doc_type 分布")
        for dt, cnt in sorted(doc_type_counts.items(), key=lambda x: -x[1]):
            lines.append(f"- `{dt}`: {cnt}")
        lines.append("")

    # Field fill rates
    field_fill = result_stats.get("field_fill", {})
    field_total = result_stats.get("field_total", {})
    if field_total:
        lines.append("### 文档级字段填充率")
        lines.append("| 字段 | 填充数 | 总数 | 填充率 |")
        lines.append("|---|---|---|---|")
        for field in ["regulator_name", "targets", "issues", "actions"]:
            f_count = field_fill.get(field, 0)
            f_total = field_total.get(field, 0)
            rate = f"{f_count / f_total * 100:.1f}%" if f_total else "N/A"
            lines.append(f"| `{field}` | {f_count} | {f_total} | {rate} |")
        lines.append("")

    lines.append("### 结构化列表项统计")
    item_counts = result_stats.get("item_counts", {})
    lines.append(f"- targets item 总数: **{item_counts.get('targets', 0)}**")
    lines.append(f"- issues item 总数: **{item_counts.get('issues', 0)}**")
    lines.append(f"- actions item 总数: **{item_counts.get('actions', 0)}**")
    lines.append("")

    for label, key in [
        ("target_type 分布", "target_type_counts"),
        ("issue_type 分布", "issue_type_counts"),
        ("action_type 分布", "action_type_counts"),
        ("action_source_type 分布", "action_source_type_counts"),
    ]:
        counts = result_stats.get(key, {})
        if counts:
            lines.append(f"### {label}")
            for name, cnt in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
                lines.append(f"- `{name}`: {cnt}")
            lines.append("")

    # --- 5. Evidence Quality ---
    lines.append("## 5. 证据质量 (Evidence Quality)")
    ev_total = result_stats.get("evidence_total", 0)
    ev_with_page = result_stats.get("evidence_with_page", 0)
    lines.append(f"- evidence 总数: **{ev_total}**")
    if ev_total > 0:
        lines.append(f"- page_no 覆盖率: {ev_with_page / ev_total * 100:.1f}%（{ev_with_page}/{ev_total}）")
    lines.append("- 硬校验: evidence_text 必须是输入 section_text 的子串，否则置 null 或丢弃")
    lines.append("")

    # --- 6. Pipeline Stability ---
    lines.append("## 6. Pipeline 稳定性")
    if pipeline_stats:
        lines.append("| Step | Info | Error | Warn |")
        lines.append("|---|---|---|---|")
        for step, counts in sorted(pipeline_stats.items()):
            lines.append(f"| `{step}` | {counts.get('info', 0)} | {counts.get('error', 0)} | {counts.get('warn', 0)} |")
    else:
        lines.append("- 日志数据待全量跑完后填充")
    lines.append("")

    # --- 7. Manual Evaluation Plan ---
    lines.append("## 7. 人工评估 (Manual Evaluation)")
    lines.append("- 主评估口径: 字段级人工评估（单公告抽取）")
    lines.append("- 标注模板: `outputs/reports/manual_eval_template.csv`")
    lines.append("- 标量字段 `doc_type / regulator_name` 按 exact-match accuracy 评估")
    lines.append("- 列表字段 `targets / issues / actions` 按 item-level 人工核对，重点统计漏抽、误抽、类型错分与 evidence/page_no 错误")
    if manual_eval_stats:
        lines.append(f"- 已填写评估表: `{_rel(manual_eval_csv)}`")
        lines.append(f"- 样本数: **{manual_eval_stats.get('sample_doc_count', 0)}** 篇 PDF")
        lines.append(f"- 字段评估总行数: **{manual_eval_stats.get('overall_total', 0)}**")
        lines.append("")
        lines.append("| 评估维度 | 正确数 | 总数 | 准确率 |")
        lines.append("|---|---|---|---|")
        for group_name, label in [
            ("doc_type", "doc_type"),
            ("regulator_name", "regulator_name"),
            ("targets", "targets"),
            ("issues", "issues"),
            ("actions", "actions"),
        ]:
            st = manual_eval_stats.get("group_stats", {}).get(group_name, {"ok": 0, "total": 0})
            total = st.get("total", 0)
            ok = st.get("ok", 0)
            rate = f"{ok / total * 100:.1f}%" if total else "N/A"
            lines.append(f"| `{label}` | {ok} | {total} | {rate} |")
        lines.append("")
        ev_total_eval = manual_eval_stats.get("evidence_total", 0)
        ev_ok_eval = manual_eval_stats.get("evidence_ok", 0)
        if ev_total_eval:
            lines.append(
                f"- evidence_correct: {ev_ok_eval}/{ev_total_eval} = {ev_ok_eval / ev_total_eval * 100:.1f}%"
            )
        lines.append(
            "- 评估字段: doc_type / regulator_name / targets[i].name / targets[i].target_type / issues[i].issue_type / issues[i].issue_summary / actions[i].action_type / actions[i].action_source_type / actions[i].deadline"
        )
    else:
        lines.append("- 标注样本: 固定 20 篇（按 doc_type 分层抽样）")
        lines.append("- 标注字段: doc_type / regulator_name / targets[i].name / targets[i].target_type / issues[i].issue_type / issues[i].issue_summary / actions[i].action_type / actions[i].action_source_type / actions[i].deadline")
        lines.append("- error_type 枚举: target_missing / issue_type_misclassified / issue_summary_incorrect / action_type_misclassified / action_source_type_wrong / action_requirement_confused / evidence_not_in_text / page_no_incorrect / doc_type_wrong")
    lines.append("")

    # --- 8. Error Analysis ---
    lines.append("## 8. 错误分析 (Error Analysis)")
    if manual_eval_stats:
        lines.append("### 错误类型分布")
        for err, cnt in sorted(manual_eval_stats.get("error_counts", {}).items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"- `{err}`: {cnt}")
        lines.append("")
        lines.append("### Top-5 代表性错误")
        for ex in manual_eval_stats.get("wrong_examples", []):
            lines.append(
                f"- `{ex.get('doc_id', '')}` {ex.get('field_name', '')} -> `{ex.get('error_type', '')}` ({ex.get('notes', '')})"
            )
    else:
        lines.append("- Top-5 错误样例、错误类型分布与代表样例将在人工评估完成后补充")
    lines.append("- prompt v1 → prompt final 的关键修改点已记录在 `prompts/prompt_final.md`")
    lines.append("")

    out_report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.event("report", "info", "done", report=str(out_report_md))

    # Also write a lightweight self-review checklist for submission.
    try:
        self_review_md = out_report_md.parent / "self_review.md"
        write_self_review(repo_root=Path.cwd().resolve(), out_md=self_review_md)
        logger.event("report", "info", "self_review_written", report=str(self_review_md))
    except Exception as e:
        logger.event("report", "error", "self_review_failed", error=str(e))

    return out_report_md
