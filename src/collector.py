from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .cninfo_client import CninfoClient
from .csv_store import write_csv_dicts
from .logger import JsonlLogger
from .utils import utc_now_iso


METADATA_FIELDS: list[str] = [
    "doc_id",
    "stock_code",
    "stock_name",
    "market",
    "publish_date",
    "announcement_title",
    "announcement_type",
    "title_rule_doc_type",
    "url",
    "pdf_url",
    "adjunct_url",
    "search_key",
    "matched_search_keys",
    "source",
    "crawl_time",
    "download_status",
    "local_pdf_path",
    "error_message",
    "notes",
]


def _get_title_filters(scope: dict[str, Any]) -> dict[str, list[str]]:
    tf = scope.get("title_filters") or {}
    return {
        "attention_keywords": list(tf.get("attention_keywords") or []),
        "inquiry_keywords": list(tf.get("inquiry_keywords") or []),
        "reply_keywords": list(tf.get("reply_keywords") or []),
        "regulatory_measure_keywords": list(tf.get("regulatory_measure_keywords") or []),
        "exclude_keywords": list(tf.get("exclude_keywords") or []),
        "attachment_exclude_keywords": list(tf.get("attachment_exclude_keywords") or []),
        "exclude_override_keywords": list(tf.get("exclude_override_keywords") or []),
    }


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(k and k in text for k in keywords)


def _infer_title_rule_doc_type(title: str, scope: dict[str, Any]) -> str:
    title = title or ""
    tf = _get_title_filters(scope)
    if _contains_any(title, tf["regulatory_measure_keywords"]):
        return "regulatory_measure"
    if _contains_any(title, tf["reply_keywords"]) and (
        _contains_any(title, tf["attention_keywords"]) or _contains_any(title, tf["inquiry_keywords"])
    ):
        return "reply"
    if _contains_any(title, tf["attention_keywords"]):
        return "attention_letter"
    if _contains_any(title, tf["inquiry_keywords"]):
        return "inquiry_letter"
    return "other"


def _is_title_allowed(title: str, scope: dict[str, Any]) -> bool:
    title = title or ""
    tf = _get_title_filters(scope)
    inferred_doc_type = _infer_title_rule_doc_type(title, scope)
    has_include = inferred_doc_type != "other"
    if not has_include:
        return False
    if inferred_doc_type in {"attention_letter", "inquiry_letter", "reply"} and _contains_any(
        title, tf["attachment_exclude_keywords"]
    ):
        return False
    has_exclude = _contains_any(title, tf["exclude_keywords"])
    has_override = _contains_any(title, tf["exclude_override_keywords"])
    if has_exclude and not has_override:
        return False
    return True


def _doc_type_priority(doc_type: str, scope: dict[str, Any]) -> int:
    ordered = list(scope.get("doc_type_priority") or [])
    try:
        return ordered.index(doc_type)
    except ValueError:
        return len(ordered)


def collect_metadata(
    *,
    crawl_cfg: dict[str, Any],
    repo_root: Path,
    logger: JsonlLogger,
    limit: int | None = None,
) -> Path:
    cn = crawl_cfg["cninfo"]
    scope = crawl_cfg["scope"]
    limits = crawl_cfg["limits"]
    rate = crawl_cfg["rate_limit"]
    paths = crawl_cfg["paths"]

    max_records = int(limits.get("max_records", 120))
    if limit is not None:
        max_records = min(max_records, int(limit))

    metadata_csv = repo_root / paths["metadata_csv"]
    metadata_csv.parent.mkdir(parents=True, exist_ok=True)

    client = CninfoClient(
        endpoint=cn["endpoint"],
        referer=cn["referer"],
        user_agent=cn.get("user_agent", "Mozilla/5.0"),
        timeout_seconds=int(rate.get("timeout_seconds", 30)),
    )

    seen: set[str] = set()
    seen_pdf_urls: set[str] = set()
    rows: list[dict[str, Any]] = []
    row_index_by_doc_id: dict[str, int] = {}
    row_index_by_pdf_url: dict[str, int] = {}
    crawl_time = utc_now_iso()

    logger.event("collect", "info", "start", max_records=max_records)

    columns = list(scope["columns"])
    search_keys = list(scope["search_keys"])
    pair_count: dict[tuple[str, str], int] = {(c, k): 0 for c in columns for k in search_keys}
    pair_quota = max(1, max_records // max(1, (len(columns) * len(search_keys))))

    def add_ann(ann) -> None:
        d = asdict(ann)
        title = d["announcement_title"]
        if not _is_title_allowed(title, scope):
            return
        title_rule_doc_type = _infer_title_rule_doc_type(title, scope)
        row = {
            "doc_id": d["doc_id"],
            "stock_code": d["stock_code"],
            "stock_name": d["stock_name"],
            "market": d["market"],
            "publish_date": d["publish_date"],
            "announcement_title": d["announcement_title"],
            "announcement_type": d.get("announcement_type") or "",
            "title_rule_doc_type": title_rule_doc_type,
            # For reproducibility, we use the public PDF link as the traceable URL.
            "url": d["pdf_url"] or "",
            "pdf_url": d["pdf_url"] or "",
            "adjunct_url": d["adjunct_url"] or "",
            "search_key": d["search_key"],
            "matched_search_keys": d["search_key"],
            "source": "cninfo",
            "crawl_time": crawl_time,
            "download_status": "",
            "local_pdf_path": "",
            "error_message": "",
            "notes": "",
        }
        doc_id = row["doc_id"]
        pdf_url = row["pdf_url"]

        existing_idx = row_index_by_doc_id.get(doc_id)
        if existing_idx is None and pdf_url:
            existing_idx = row_index_by_pdf_url.get(pdf_url)
        if existing_idx is not None:
            existing = rows[existing_idx]
            merged_keys = {
                x.strip()
                for x in (existing.get("matched_search_keys") or "").split("|")
                if x.strip()
            }
            merged_keys.add(d["search_key"])
            existing["matched_search_keys"] = "|".join(sorted(merged_keys))
            return

        rows.append(row)
        idx = len(rows) - 1
        row_index_by_doc_id[doc_id] = idx
        if pdf_url:
            row_index_by_pdf_url[pdf_url] = idx

    # Pass 1: enforce a small quota per (column, search_key) pair for coverage.
    for column in columns:
        for search_key in search_keys:
            if len(rows) >= max_records:
                break
            target = pair_quota
            for ann in client.iter_announcements(
                column=column,
                tabName=cn.get("tabName", "fulltext"),
                searchkey=search_key,
                seDate=scope["seDate"],
                page_size=int(limits.get("page_size", 30)),
                max_retries=int(rate.get("max_retries", 3)),
                sleep_seconds=float(rate.get("sleep_seconds", 0.6)),
            ):
                if len(rows) >= max_records or pair_count[(column, search_key)] >= target:
                    break
                if ann.doc_id in seen:
                    add_ann(ann)
                    continue
                if ann.pdf_url and ann.pdf_url in seen_pdf_urls:
                    add_ann(ann)
                    continue
                title = ann.announcement_title
                if not _is_title_allowed(title, scope):
                    continue
                add_ann(ann)
                if ann.doc_id not in row_index_by_doc_id:
                    continue
                seen.add(ann.doc_id)
                if ann.pdf_url:
                    seen_pdf_urls.add(ann.pdf_url)
                pair_count[(column, search_key)] += 1

    # Pass 2: fill remaining slots without per-pair quota (dedupe still applies).
    if len(rows) < max_records:
        for column in columns:
            for search_key in search_keys:
                if len(rows) >= max_records:
                    break
                for ann in client.iter_announcements(
                    column=column,
                    tabName=cn.get("tabName", "fulltext"),
                    searchkey=search_key,
                    seDate=scope["seDate"],
                    page_size=int(limits.get("page_size", 30)),
                    max_retries=int(rate.get("max_retries", 3)),
                    sleep_seconds=float(rate.get("sleep_seconds", 0.6)),
                ):
                    if len(rows) >= max_records:
                        break
                    if ann.doc_id in seen:
                        add_ann(ann)
                        continue
                    if ann.pdf_url and ann.pdf_url in seen_pdf_urls:
                        add_ann(ann)
                        continue
                    if not _is_title_allowed(ann.announcement_title, scope):
                        continue
                    add_ann(ann)
                    if ann.doc_id not in row_index_by_doc_id:
                        continue
                    seen.add(ann.doc_id)
                    if ann.pdf_url:
                        seen_pdf_urls.add(ann.pdf_url)

    # Sort by publish date (desc), then title-priority, then doc_id for stable order.
    rows.sort(
        key=lambda r: (
            r.get("publish_date", ""),
            -_doc_type_priority(str(r.get("title_rule_doc_type") or "other"), scope),
            r.get("doc_id", ""),
        ),
        reverse=True,
    )
    rows = rows[:max_records]
    write_csv_dicts(metadata_csv, rows, METADATA_FIELDS)

    logger.event(
        "collect",
        "info",
        "done",
        metadata_csv=str(metadata_csv),
        total=len(rows),
    )
    return metadata_csv
