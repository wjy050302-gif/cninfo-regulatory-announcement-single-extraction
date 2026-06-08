from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from tqdm import tqdm

from .csv_store import read_csv_dicts, write_csv_dicts
from .logger import JsonlLogger
from .utils import ensure_parent_dir


def _is_allowed_pdf_url(url: str) -> bool:
    try:
        u = urlparse(url)
    except Exception:
        return False
    if u.scheme not in ("http", "https"):
        return False
    # Strict whitelist: only static.cninfo.com.cn
    return u.netloc.lower() == "static.cninfo.com.cn"


def download_pdfs(
    *,
    repo_root: Path,
    metadata_csv: Path,
    pdf_dir: Path,
    logger: JsonlLogger,
    limit: int | None = None,
    timeout_seconds: int = 60,
    max_retries: int = 3,
    sleep_seconds: float = 0.4,
    throttle_seconds: float = 0.1,
    failed_csv: Path | None = None,
) -> dict[str, Any]:
    rows = read_csv_dicts(metadata_csv)
    if not rows:
        raise FileNotFoundError(f"metadata is empty or missing: {metadata_csv}")

    pdf_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    ok = 0
    skipped = 0
    failed = 0

    logger.event("download", "info", "start", metadata_csv=str(metadata_csv))

    it = rows
    if limit is not None:
        it = rows[: int(limit)]

    for row in tqdm(it, desc="download", unit="pdf"):
        total += 1
        doc_id = (row.get("doc_id") or "").strip()
        pdf_url = (row.get("pdf_url") or "").strip()
        if not doc_id or not pdf_url:
            row["download_status"] = "failed"
            row["error_message"] = "missing doc_id or pdf_url"
            failed += 1
            continue

        if not _is_allowed_pdf_url(pdf_url):
            row["download_status"] = "failed"
            row["error_message"] = f"pdf_url not allowed (whitelist): {pdf_url}"
            failed += 1
            continue

        local_path = pdf_dir / f"{doc_id}.pdf"
        try:
            row["local_pdf_path"] = str(local_path.relative_to(repo_root).as_posix())
        except Exception:
            row["local_pdf_path"] = str(local_path.as_posix())

        if local_path.exists() and local_path.stat().st_size > 0:
            row["download_status"] = "skipped"
            row["error_message"] = ""
            skipped += 1
            continue

        ensure_parent_dir(local_path)
        tmp_path = local_path.with_suffix(".pdf.part")

        last_err: str | None = None
        for attempt in range(1, max_retries + 1):
            try:
                with requests.get(
                    pdf_url,
                    stream=True,
                    timeout=timeout_seconds,
                    headers={"User-Agent": "Mozilla/5.0"},
                ) as r:
                    if r.status_code in (429, 500, 502, 503, 504):
                        raise RuntimeError(f"http {r.status_code}")
                    r.raise_for_status()
                    with open(tmp_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024 * 256):
                            if chunk:
                                f.write(chunk)
                os.replace(tmp_path, local_path)
                row["download_status"] = "success"
                row["error_message"] = ""
                ok += 1
                last_err = None
                break
            except Exception as e:
                last_err = str(e)
                if attempt >= max_retries:
                    break
                import time

                time.sleep(sleep_seconds * attempt)

        if last_err is not None:
            row["download_status"] = "failed"
            row["error_message"] = last_err
            failed += 1

        if throttle_seconds:
            import time

            time.sleep(throttle_seconds)

    # Preserve original field order if present, else write all keys.
    fieldnames = list(rows[0].keys()) if rows else []
    write_csv_dicts(metadata_csv, rows, fieldnames)

    if failed_csv is not None:
        failed_rows = [r for r in rows if (r.get("download_status") or "").strip() == "failed"]
        if failed_rows:
            failed_csv.parent.mkdir(parents=True, exist_ok=True)
            write_csv_dicts(failed_csv, failed_rows, fieldnames)

    summary = {"total": total, "ok": ok, "skipped": skipped, "failed": failed}
    logger.event("download", "info", "done", **summary)
    return summary
