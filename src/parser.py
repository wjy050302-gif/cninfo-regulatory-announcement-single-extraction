from __future__ import annotations

import csv
import json
import os
import time
from pathlib import Path
from typing import Any

from .csv_store import read_csv_dicts
from .logger import JsonlLogger
from .mineru_client import (
    MinerUClient,
    build_pages_from_content_list,
    download_zip,
    extract_full_md_and_content_list,
)
from .utils import utc_now_iso, write_jsonl_line


def parse_with_mineru(
    *,
    metadata_csv: Path,
    parsed_dir: Path,
    logger: JsonlLogger,
    limit: int | None = None,
    mineru_base_url_env: str = "MINERU_BASE_URL",
    mineru_api_key_env: str = "MINERU_API_KEY",
    timeout_seconds: int = 120,
    model_version: str = "pipeline",
    poll_interval_seconds: float = 2.0,
    max_wait_seconds: int = 300,
    max_failures_per_doc: int = 1,
    max_inflight_tasks: int = 4,
) -> Path:
    api_key = (os.getenv(mineru_api_key_env) or "").strip()
    base_url = (os.getenv(mineru_base_url_env) or "https://mineru.net").strip()
    if not api_key:
        raise RuntimeError(
            f"MinerU API key missing: env {mineru_api_key_env} is empty. "
            "Create .env from .env.example and fill MINERU_API_KEY."
        )

    rows = read_csv_dicts(metadata_csv)
    if not rows:
        raise FileNotFoundError(f"metadata is empty or missing: {metadata_csv}")

    parsed_dir.mkdir(parents=True, exist_ok=True)
    zip_dir = parsed_dir / "zip"
    md_dir = parsed_dir / "markdown"
    zip_dir.mkdir(parents=True, exist_ok=True)
    md_dir.mkdir(parents=True, exist_ok=True)

    out_jsonl = parsed_dir / "parsed_docs.jsonl"
    parsed_cache: dict[str, dict[str, Any]] = {}
    if out_jsonl.exists():
        with open(out_jsonl, "r", encoding="utf-8") as f_done:
            for line in f_done:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    doc_id = str(obj.get("doc_id") or "")
                    if doc_id:
                        parsed_cache[doc_id] = obj
                except Exception:
                    continue
        out_jsonl.unlink()

    repo_root = parsed_dir.parents[1]
    parse_manifest_csv = repo_root / "outputs/logs/parse_manifest.csv"
    parse_manifest_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(parse_manifest_csv, "w", encoding="utf-8", newline="") as f_manifest:
        csv.DictWriter(
            f_manifest,
            fieldnames=[
                "doc_id",
                "pdf_path",
                "markdown_path",
                "parser",
                "status",
                "error_message",
                "parse_time",
            ],
        ).writeheader()

    failures_jsonl = repo_root / "outputs/logs/parse_failures.jsonl"
    fail_counts: dict[str, int] = {}
    if failures_jsonl.exists():
        with open(failures_jsonl, "r", encoding="utf-8") as f_fail:
            for line in f_fail:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    did = str(obj.get("doc_id") or "")
                    if did:
                        fail_counts[did] = fail_counts.get(did, 0) + 1
                except Exception:
                    continue

    client = MinerUClient(base_url=base_url, api_key=api_key, timeout_seconds=timeout_seconds)
    items = rows[: int(limit)] if limit is not None else rows
    max_inflight_tasks = max(1, int(max_inflight_tasks))

    logger.event(
        "parse",
        "info",
        "start",
        total=len(items),
        mineru_base_url=base_url,
    )

    def append_manifest_row(
        *,
        doc_id: str,
        pdf_path: str,
        markdown_path: str,
        status: str,
        error_message: str,
    ) -> None:
        with open(parse_manifest_csv, "a", encoding="utf-8", newline="") as f_manifest:
            w_manifest = csv.DictWriter(
                f_manifest,
                fieldnames=[
                    "doc_id",
                    "pdf_path",
                    "markdown_path",
                    "parser",
                    "status",
                    "error_message",
                    "parse_time",
                ],
            )
            w_manifest.writerow(
                {
                    "doc_id": doc_id,
                    "pdf_path": pdf_path,
                    "markdown_path": markdown_path,
                    "parser": "mineru",
                    "status": status,
                    "error_message": error_message,
                    "parse_time": utc_now_iso(),
                }
            )

    def handle_failure(item: dict[str, Any], error: Exception) -> None:
        doc_id = item["doc_id"]
        pdf_url = item["pdf_url"]
        pdf_path = item["pdf_path"]
        logger.event("parse", "error", "parse_failed", doc_id=doc_id, error=str(error))
        write_jsonl_line(
            failures_jsonl,
            {"ts": utc_now_iso(), "doc_id": doc_id, "error": str(error), "pdf_url": pdf_url},
        )
        fail_counts[doc_id] = fail_counts.get(doc_id, 0) + 1
        append_manifest_row(
            doc_id=doc_id,
            pdf_path=pdf_path,
            markdown_path="",
            status="failed",
            error_message=str(error),
        )

    pending_rows: list[dict[str, Any]] = []
    for row in items:
        doc_id = (row.get("doc_id") or "").strip()
        pdf_url = (row.get("pdf_url") or "").strip()
        pdf_path = (row.get("local_pdf_path") or "").strip()
        if not doc_id or not pdf_url:
            logger.event("parse", "error", "missing doc_id or pdf_url", doc_id=doc_id, pdf_url=pdf_url)
            continue

        if fail_counts.get(doc_id, 0) >= max_failures_per_doc:
            logger.event(
                "parse",
                "warn",
                "skip_due_to_previous_failures",
                doc_id=doc_id,
                failures=fail_counts.get(doc_id, 0),
            )
            append_manifest_row(
                doc_id=doc_id,
                pdf_path=pdf_path,
                markdown_path="",
                status="skipped_failed",
                error_message=f"previous failures >= {max_failures_per_doc}",
            )
            continue

        zip_path = zip_dir / f"{doc_id}.zip"
        md_path = md_dir / f"{doc_id}.md"

        if doc_id in parsed_cache:
            cached = dict(parsed_cache[doc_id])
            cached.update(
                {
                    "doc_id": doc_id,
                    "stock_code": (row.get("stock_code") or "").strip(),
                    "stock_name": (row.get("stock_name") or "").strip(),
                    "market": (row.get("market") or "").strip(),
                    "publish_date": (row.get("publish_date") or "").strip(),
                    "title": (row.get("announcement_title") or "").strip(),
                    "pdf_path": pdf_path,
                    "pdf_url": pdf_url,
                }
            )
            write_jsonl_line(out_jsonl, cached)
            append_manifest_row(
                doc_id=doc_id,
                pdf_path=pdf_path,
                markdown_path=str(md_path.relative_to(repo_root).as_posix()) if md_path.exists() else "",
                status="cached",
                error_message="",
            )
            continue

        pending_rows.append(
            {
                "row": row,
                "doc_id": doc_id,
                "pdf_url": pdf_url,
                "pdf_path": pdf_path,
                "zip_path": zip_path,
                "md_path": md_path,
            }
        )

    inflight: list[dict[str, Any]] = []
    while pending_rows or inflight:
        while pending_rows and len(inflight) < max_inflight_tasks:
            item = pending_rows.pop(0)
            try:
                logger.event("parse", "info", "mineru_task_create", doc_id=item["doc_id"])
                task_id = client.create_extract_task(
                    file_url=item["pdf_url"],
                    model_version=model_version,
                )
                item["task_id"] = task_id
                item["started_at"] = time.time()
                inflight.append(item)
                logger.event("parse", "info", "mineru_task_created", doc_id=item["doc_id"], task_id=task_id)
            except Exception as e:
                handle_failure(item, e)

        if not inflight:
            continue

        time.sleep(max(0.2, float(poll_interval_seconds)))
        for item in list(inflight):
            doc_id = item["doc_id"]
            pdf_path = item["pdf_path"]
            md_path = item["md_path"]
            zip_path = item["zip_path"]
            task_id = item["task_id"]
            try:
                if time.time() - float(item["started_at"]) > max_wait_seconds:
                    raise TimeoutError(f"MinerU task timeout after {max_wait_seconds}s: {task_id}")

                res = client.get_task(task_id)
                if not res.full_zip_url:
                    continue

                zip_url = res.full_zip_url
                logger.event("parse", "info", "mineru_task_done", doc_id=doc_id, task_id=task_id, zip_url=zip_url)
                download_zip(zip_url, zip_path, timeout_seconds=timeout_seconds)
                full_md_text, content_list = extract_full_md_and_content_list(zip_path)
                if full_md_text:
                    md_path.write_text(full_md_text, encoding="utf-8")

                pages = []
                if content_list is not None:
                    pages = build_pages_from_content_list(content_list)

                row = item["row"]
                record: dict[str, Any] = {
                    "doc_id": doc_id,
                    "stock_code": (row.get("stock_code") or "").strip(),
                    "stock_name": (row.get("stock_name") or "").strip(),
                    "market": (row.get("market") or "").strip(),
                    "publish_date": (row.get("publish_date") or "").strip(),
                    "title": (row.get("announcement_title") or "").strip(),
                    "pdf_path": pdf_path,
                    "pdf_url": item["pdf_url"],
                    "parsed_at": utc_now_iso(),
                    "mineru": {
                        "base_url": base_url,
                        "task_id": task_id,
                        "zip_path": str(zip_path.as_posix()),
                        "markdown_path": str(md_path.as_posix()) if md_path.exists() else "",
                    },
                    "pages": pages,
                }
                write_jsonl_line(out_jsonl, record)
                logger.event("parse", "info", "parsed_ok", doc_id=doc_id, pages=len(pages))
                append_manifest_row(
                    doc_id=doc_id,
                    pdf_path=pdf_path,
                    markdown_path=str(md_path.relative_to(repo_root).as_posix()) if md_path.exists() else "",
                    status="success",
                    error_message="",
                )
                inflight.remove(item)
            except Exception as e:
                inflight.remove(item)
                handle_failure(item, e)

    logger.event("parse", "info", "done", parsed_jsonl=str(out_jsonl))
    return out_jsonl
