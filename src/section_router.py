from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

from .logger import JsonlLogger
from .utils import ensure_parent_dir, read_yaml, utc_now_iso, write_jsonl_line


def _compile_any(patterns: list[str]) -> re.Pattern | None:
    if not patterns:
        return None
    joined = "|".join(f"(?:{p})" for p in patterns if p)
    if not joined:
        return None
    return re.compile(joined)


def _doc_type_from_title(title: str) -> str:
    title = title or ""
    if any(
        k in title
        for k in ("行政监管措施", "监管措施", "决定书", "警示函", "责令改正", "监管谈话", "整改报告")
    ):
        return "regulatory_measure"
    if any(k in title for k in ("回复", "回函", "延期回复")):
        return "reply"
    if "关注函" in title:
        return "attention_letter"
    if any(k in title for k in ("问询函", "审核问询", "年报问询")):
        return "inquiry_letter"
    return "other"


def route_sections(
    *,
    parsed_jsonl: Path,
    section_rules_path: Path,
    sections_out_jsonl: Path,
    section_check_report_csv: Path,
    logger: JsonlLogger,
    limit: int | None = None,
) -> dict[str, Any]:
    rules = read_yaml(section_rules_path)
    common = rules.get("common", {})
    exclude_re = _compile_any(common.get("exclude_regex") or [])

    # Only these two section types are used in standard 1.0.
    # Important: one record = one PDF. So we route each doc to ONE best section
    # (based on title hint + found quality), instead of emitting multiple rows per doc.
    section_names = ["inquiry_attention_body", "regulatory_measure_body"]

    def _doc_kind_from_title(t: str) -> str:
        t = t or ""
        if any(
            k in t
            for k in ("行政监管措施", "监管措施", "决定书", "警示函", "责令改正", "监管谈话", "整改报告")
        ):
            return "regulatory_measure_body"
        if any(k in t for k in ("关注函", "问询函", "审核问询", "年报问询", "回复", "回函", "延期回复")):
            return "inquiry_attention_body"
        # default to inquiry/attention for standard 1.0 (most common)
        return "inquiry_attention_body"

    if sections_out_jsonl.exists():
        sections_out_jsonl.unlink()

    ensure_parent_dir(section_check_report_csv)
    with open(section_check_report_csv, "w", encoding="utf-8", newline="") as f_csv:
        fieldnames = [
            "ts",
            "doc_id",
            "announcement_title",
            "section_name",
            "match_strategy",
            "found",
            "page_start",
            "page_end",
            "char_len",
            "quality_issue",
        ]
        w = csv.DictWriter(f_csv, fieldnames=fieldnames)
        w.writeheader()

        count = 0
        ok = 0
        with open(parsed_jsonl, "r", encoding="utf-8") as f_in:
            for line in f_in:
                if not line.strip():
                    continue
                count += 1
                if limit is not None and count > int(limit):
                    break

                doc = json.loads(line)
                doc_id = str(doc.get("doc_id") or "")
                title = str(doc.get("title") or doc.get("announcement_title") or "")
                pages = doc.get("pages") or []
                max_page_no = max((int(p.get("page_no") or 0) for p in pages), default=0)
                # Evaluate both candidate section types first (for checking/reporting),
                # then emit exactly one best section record for downstream extraction.
                candidates: dict[str, dict[str, Any]] = {}

                for section_name in section_names:
                    section_rule = rules.get(section_name) or {}
                    include_re = _compile_any(section_rule.get("include_regex") or [])
                    anchor_re = _compile_any(section_rule.get("anchor_regex") or [])
                    min_chars = int(section_rule.get("min_chars") or 0)
                    max_span_pages = int(section_rule.get("max_span_pages") or 0)
                    max_pages = int(section_rule.get("max_pages") or 0)
                    expansion = section_rule.get("page_expansion") or {}
                    before = int(expansion.get("before") or 0)
                    after = int(expansion.get("after") or 0)

                    include_pages: list[int] = []
                    anchor_pages: list[int] = []
                    for p in pages:
                        text = p.get("text") or ""
                        if not isinstance(text, str) or not text.strip():
                            continue
                        if exclude_re and exclude_re.search(text):
                            # Directory / declaration pages often contain repeated
                            # "问题1/问题2" anchors but are not the real body.
                            continue
                        has_anchor = bool(anchor_re and anchor_re.search(text))
                        has_include = bool(include_re and include_re.search(text))
                        try:
                            page_no = int(p.get("page_no"))
                        except Exception:
                            continue
                        if has_include:
                            include_pages.append(page_no)
                        if has_anchor:
                            anchor_pages.append(page_no)

                    match_strategy = ""
                    if anchor_pages:
                        match_pages = sorted(set(anchor_pages))
                        match_strategy = "anchor_regex"
                    elif include_pages:
                        match_pages = sorted(set(include_pages))
                        match_strategy = "include_regex"
                    else:
                        match_pages = []

                    found = bool(match_pages)
                    quality_issue = ""
                    page_start_i: int | None = None
                    page_end_i: int | None = None
                    section_text = ""

                    if not found:
                        quality_issue = "not_found"
                    else:
                        p_min = min(match_pages)
                        p_max = max(match_pages)
                        # If matches span too many pages, it's likely caused by repetitive headers/footers.
                        # In that case, anchor on the first match only.
                        if max_span_pages and (p_max - p_min + 1) > max_span_pages:
                            p_max = p_min
                        page_start_i = max(1, p_min - before)
                        # Do NOT use len(pages) as an upper bound: MinerU may drop empty pages,
                        # so len(pages) can be smaller than the maximum page number.
                        page_end_i = min(max_page_no, p_max + after) if max_page_no else (p_max + after)
                        # Absolute cap on pages included (avoid gigantic sections).
                        if max_pages and page_start_i is not None:
                            page_end_i = min(page_end_i, page_start_i + max_pages - 1)

                        parts: list[str] = []
                        for p in pages:
                            pno = int(p.get("page_no") or 0)
                            if page_start_i is None or page_end_i is None:
                                continue
                            if pno < page_start_i or pno > page_end_i:
                                continue
                            txt = p.get("text") or ""
                            if not isinstance(txt, str):
                                continue
                            if exclude_re and exclude_re.search(txt):
                                continue
                            parts.append(f"[Page {pno}]\n{txt}".strip())
                        section_text = "\n\n".join(parts).strip()

                        if min_chars and len(section_text) < min_chars:
                            quality_issue = "too_short"

                    candidates[section_name] = {
                        "found": found,
                        "page_start": page_start_i,
                        "page_end": page_end_i,
                        "section_text": section_text,
                        "char_len": len(section_text),
                        "quality_issue": quality_issue,
                    }

                    w.writerow(
                        {
                            "ts": utc_now_iso(),
                            "doc_id": doc_id,
                            "announcement_title": title,
                            "section_name": section_name,
                            "match_strategy": match_strategy,
                            "found": "1" if found else "0",
                            "page_start": str(page_start_i) if page_start_i else "",
                            "page_end": str(page_end_i) if page_end_i else "",
                            "char_len": str(len(section_text)),
                            "quality_issue": quality_issue,
                        }
                    )

                preferred = _doc_kind_from_title(title)
                other = "regulatory_measure_body" if preferred == "inquiry_attention_body" else "inquiry_attention_body"

                # Title-derived section type has higher priority than raw length/quality.
                # For reply/inquiry docs, the preferred body may be shorter than some
                # later false-positive pages of another section type; if the preferred
                # section is found at all, we keep it. Only fall back when it is absent.
                chosen_name = preferred if candidates.get(preferred, {}).get("found") else ""
                if not chosen_name and candidates.get(other, {}).get("found"):
                    chosen_name = other

                if chosen_name:
                    c = candidates[chosen_name]
                    rec = {
                        "doc_id": doc_id,
                        "section_name": chosen_name,
                        "doc_type": _doc_type_from_title(title),
                        "announcement_title": title,
                        "page_start": c.get("page_start"),
                        "page_end": c.get("page_end"),
                        "section_text": c.get("section_text"),
                        "source": {
                            "pdf_url": doc.get("pdf_url"),
                            "publish_date": doc.get("publish_date"),
                            "stock_code": doc.get("stock_code"),
                            "stock_name": doc.get("stock_name"),
                            "market": doc.get("market"),
                        },
                    }
                    write_jsonl_line(sections_out_jsonl, rec)
                    ok += 1

    logger.event(
        "route_sections",
        "info",
        "done",
        parsed_jsonl=str(parsed_jsonl),
        sections_out=str(sections_out_jsonl),
        report_csv=str(section_check_report_csv),
        docs_processed=count,
        sections_written=ok,
    )
    return {"docs_processed": count, "sections_written": ok}
