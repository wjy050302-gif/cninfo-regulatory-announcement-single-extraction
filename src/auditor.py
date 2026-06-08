from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .csv_store import read_csv_dicts
from .logger import JsonlLogger
from .utils import ensure_parent_dir, utc_now_iso


def audit_dataset(
    *,
    metadata_csv: Path,
    report_path: Path,
    logger: JsonlLogger,
) -> dict[str, Any]:
    rows = read_csv_dicts(metadata_csv)
    if not rows:
        raise FileNotFoundError(f"metadata is empty or missing: {metadata_csv}")

    total = len(rows)
    doc_ids = [r.get("doc_id", "") for r in rows]
    dup_doc_ids = [doc_id for doc_id, c in Counter(doc_ids).items() if doc_id and c > 1]

    status_counts = Counter((r.get("download_status") or "").strip() for r in rows)
    markets = Counter((r.get("market") or "").strip() for r in rows)
    keys = Counter((r.get("search_key") or "").strip() for r in rows)

    missing_pdf_url = sum(1 for r in rows if not (r.get("pdf_url") or "").strip())

    # Local file existence check (best-effort; path may be empty).
    repo_root = Path.cwd().resolve()
    missing_local_pdf = 0
    local_pdf_checked = 0
    for r in rows:
        p = (r.get("local_pdf_path") or "").strip()
        if not p:
            continue
        local_pdf_checked += 1
        lp = Path(p)
        if not lp.is_absolute():
            lp = repo_root / lp
        if not lp.exists():
            missing_local_pdf += 1

    ensure_parent_dir(report_path)
    lines: list[str] = []
    lines.append(f"# Dataset Audit Report ({utc_now_iso()})")
    lines.append("")
    try:
        meta_rel = metadata_csv.resolve().relative_to(repo_root).as_posix()
    except Exception:
        meta_rel = str(metadata_csv)
    lines.append(f"- metadata: `{meta_rel}`")
    lines.append(f"- total records: **{total}**")
    lines.append(f"- missing pdf_url: **{missing_pdf_url}**")
    lines.append(f"- duplicate doc_id count: **{len(dup_doc_ids)}**")
    lines.append(f"- local_pdf_path checked: **{local_pdf_checked}**")
    lines.append(f"- missing local pdf files: **{missing_local_pdf}**")
    lines.append("")

    lines.append("## Download Status")
    for k, v in status_counts.most_common():
        lines.append(f"- `{k or '(empty)'}`: {v}")
    lines.append("")

    lines.append("## Markets")
    for k, v in markets.most_common():
        lines.append(f"- `{k or '(empty)'}`: {v}")
    lines.append("")

    lines.append("## Search Keys")
    for k, v in keys.most_common():
        lines.append(f"- `{k or '(empty)'}`: {v}")
    lines.append("")

    if dup_doc_ids:
        lines.append("## Duplicate doc_id Examples")
        for doc_id in dup_doc_ids[:20]:
            lines.append(f"- `{doc_id}`")
        lines.append("")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.event(
        "audit",
        "info",
        "done",
        report=str(report_path),
        total=total,
        missing_pdf_url=missing_pdf_url,
        dup_doc_ids=len(dup_doc_ids),
        missing_local_pdf=missing_local_pdf,
    )
    return {
        "total": total,
        "missing_pdf_url": missing_pdf_url,
        "dup_doc_ids": len(dup_doc_ids),
        "missing_local_pdf": missing_local_pdf,
        "status_counts": dict(status_counts),
    }
