from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .llm_client import chat_completions, parse_json_object
from .logger import JsonlLogger
from .schemas import (
    ACTION_TYPE_VALUES,
    ACTION_SOURCE_TYPE_VALUES,
    DOC_TYPE_VALUES,
    ISSUE_TYPE_VALUES,
    TARGET_TYPE_VALUES,
    RegulatoryDocExtract,
)
from .utils import ensure_parent_dir, read_yaml, utc_now_iso, write_jsonl_line


_PAGE_SPLIT_RE = re.compile(r"(?=\[Page\s+\d+\])")


def _truncate_section_text(section_text: str, max_pages: int, max_chars: int) -> tuple[str, dict[str, Any]]:
    raw = (section_text or "").strip()
    if not raw:
        return "", {"input_page_blocks": 0, "used_page_blocks": 0, "truncated": False}

    blocks = [b.strip() for b in _PAGE_SPLIT_RE.split(raw) if b.strip()]
    original_block_count = len(blocks)
    used_blocks = blocks
    truncated = False

    if max_pages > 0 and len(used_blocks) > max_pages:
        used_blocks = used_blocks[:max_pages]
        truncated = True

    text = "\n\n".join(used_blocks).strip()
    if max_chars > 0 and len(text) > max_chars:
        text = text[:max_chars].rstrip()
        truncated = True

    return text, {
        "input_page_blocks": original_block_count,
        "used_page_blocks": len(used_blocks),
        "truncated": truncated,
        "input_chars": len(raw),
        "used_chars": len(text),
    }


def _normalize_evidence(ev: Any) -> dict[str, Any] | None:
    if not isinstance(ev, dict):
        return None
    evidence_text = ev.get("evidence_text")
    if not isinstance(evidence_text, str) or not evidence_text.strip():
        return None
    page_no = ev.get("page_no")
    if not isinstance(page_no, int):
        page_no = None
    return {"evidence_text": evidence_text, "page_no": page_no}


def _normalize_regulator_name(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    regulator = value.get("value")
    evidence = _normalize_evidence(value.get("evidence"))
    if not isinstance(regulator, str) or not regulator.strip() or evidence is None:
        return None
    return {"value": regulator, "evidence": evidence}


def _normalize_targets(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        target_type = item.get("target_type")
        evidence = _normalize_evidence(item.get("evidence"))
        if not isinstance(name, str) or not name.strip():
            continue
        if not isinstance(target_type, str) or target_type not in TARGET_TYPE_VALUES:
            continue
        role = item.get("role")
        if not isinstance(role, str) or not role.strip():
            role = None
        if evidence is None:
            continue
        out.append(
            {
                "name": name,
                "role": role,
                "target_type": target_type,
                "evidence": evidence,
            }
        )
    return out


def _normalize_issues(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        issue_type = item.get("issue_type")
        issue_summary = item.get("issue_summary")
        evidence = _normalize_evidence(item.get("evidence"))
        if not isinstance(issue_type, str) or issue_type not in ISSUE_TYPE_VALUES:
            continue
        if not isinstance(issue_summary, str) or not issue_summary.strip():
            continue
        is_violation_related = item.get("is_violation_related")
        if not isinstance(is_violation_related, bool):
            is_violation_related = None
        if evidence is None:
            continue
        out.append(
            {
                "issue_type": issue_type,
                "issue_summary": issue_summary,
                "is_violation_related": is_violation_related,
                "evidence": evidence,
            }
        )
    return out


def _normalize_actions(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        action_type = item.get("action_type")
        action_source_type = item.get("action_source_type")
        evidence = _normalize_evidence(item.get("evidence"))
        if not isinstance(action_type, str) or action_type not in ACTION_TYPE_VALUES:
            continue
        if not isinstance(action_source_type, str) or action_source_type not in ACTION_SOURCE_TYPE_VALUES:
            action_source_type = "unclear"
        deadline = item.get("deadline")
        if not isinstance(deadline, str) or not deadline.strip():
            deadline = None
        required_disclosure = item.get("required_disclosure")
        if not isinstance(required_disclosure, bool):
            required_disclosure = None
        if evidence is None:
            continue
        out.append(
            {
                "action_type": action_type,
                "action_source_type": action_source_type,
                "deadline": deadline,
                "required_disclosure": required_disclosure,
                "evidence": evidence,
            }
        )
    return out


def _normalize_doc_type(value: Any, section_name: str, title: str) -> str:
    if isinstance(value, str) and value in DOC_TYPE_VALUES:
        return value
    if section_name == "regulatory_measure_body":
        return "regulatory_measure"
    if any(k in title for k in ("回复", "回函", "延期回复")):
        return "reply"
    if "关注函" in title:
        return "attention_letter"
    if any(k in title for k in ("问询函", "审核问询", "年报问询")):
        return "inquiry_letter"
    return "other"


def _normalize_for_schema(obj: dict[str, Any], sec: dict[str, Any]) -> dict[str, Any]:
    section_name = str(sec.get("section_name") or "")
    title = str(sec.get("announcement_title") or "")
    normalized = dict(obj)
    normalized["doc_type"] = _normalize_doc_type(obj.get("doc_type"), section_name, title)
    normalized["regulator_name"] = _normalize_regulator_name(obj.get("regulator_name"))
    normalized["targets"] = _normalize_targets(obj.get("targets"))
    normalized["issues"] = _normalize_issues(obj.get("issues"))
    normalized["actions"] = _normalize_actions(obj.get("actions"))
    return normalized


def _extract_one(
    *,
    sec: dict[str, Any],
    prompt_text: str,
    base_url: str,
    api_key: str,
    model: str,
    temperature: float,
    timeout_seconds: int,
    max_retries: int,
    retry_backoff_seconds: float,
    input_max_pages: int,
    input_max_chars: int,
) -> dict[str, Any]:
    doc_id = str(sec.get("doc_id") or "")
    section_text = str(sec.get("section_text") or "")
    llm_input_text, trunc_info = _truncate_section_text(
        section_text=section_text,
        max_pages=input_max_pages,
        max_chars=input_max_chars,
    )
    source = sec.get("source") or {}
    pdf_url = str(source.get("pdf_url") or sec.get("pdf_url") or "")

    base_record = {
        "doc_id": doc_id,
        "stock_code": str(source.get("stock_code") or ""),
        "stock_name": str(source.get("stock_name") or ""),
        "market": str(source.get("market") or ""),
        "publish_date": str(source.get("publish_date") or ""),
        "announcement_title": str(sec.get("announcement_title") or ""),
        "source": {"url": pdf_url, "pdf_url": pdf_url},
    }

    messages = [
        {"role": "system", "content": prompt_text},
        {
            "role": "user",
            "content": (
                "Metadata (must be preserved):\n"
                + json.dumps(base_record, ensure_ascii=False)
                + "\n\nInput text:\n"
                + llm_input_text
            ),
        },
    ]

    content = chat_completions(
        base_url=base_url,
        api_key=api_key,
        model=model,
        messages=messages,
        temperature=temperature,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff_seconds,
    )
    obj = parse_json_object(content)
    merged = {**_normalize_for_schema(obj, sec), **base_record}
    validated = RegulatoryDocExtract.model_validate(merged)
    return {
        "doc_id": doc_id,
        "validated": validated.model_dump(),
        "raw": content,
        "truncation": trunc_info,
    }


def run_extraction(
    *,
    sections_jsonl: Path,
    model_cfg_path: Path,
    prompt_path: Path,
    out_extracted_jsonl: Path,
    out_raw_jsonl: Path,
    out_errors_jsonl: Path,
    logger: JsonlLogger,
    limit: int | None = None,
    max_inflight_requests: int = 4,
) -> dict[str, Any]:
    model_cfg = read_yaml(model_cfg_path)
    llm_cfg = model_cfg.get("llm") or {}

    base_url_env = llm_cfg.get("base_url_env", "LLM_BASE_URL")
    api_key_env = llm_cfg.get("api_key_env", "LLM_API_KEY")
    model_env = llm_cfg.get("model_env", "LLM_MODEL")

    base_url = (os.getenv(base_url_env) or "").strip()
    api_key = (os.getenv(api_key_env) or "").strip()
    model = (os.getenv(model_env) or "").strip()

    temperature = float(llm_cfg.get("temperature", 0.0))
    timeout_seconds = int(llm_cfg.get("timeout_seconds", 60))
    max_retries = int(llm_cfg.get("max_retries", 1))
    retry_backoff_seconds = float(llm_cfg.get("retry_backoff_seconds", 5.0))
    input_max_pages = int(llm_cfg.get("input_max_pages", 0) or 0)
    input_max_chars = int(llm_cfg.get("input_max_chars", 0) or 0)

    if not base_url or not api_key or not model:
        raise RuntimeError(
            f"LLM config missing. Need env {base_url_env}, {api_key_env}, {model_env}."
        )

    prompt_text = prompt_path.read_text(encoding="utf-8")

    # rewrite output files for deterministic runs
    for p in (out_extracted_jsonl, out_raw_jsonl, out_errors_jsonl):
        if p.exists():
            p.unlink()

    ensure_parent_dir(out_extracted_jsonl)
    ensure_parent_dir(out_raw_jsonl)
    ensure_parent_dir(out_errors_jsonl)

    total = 0
    ok = 0
    failed = 0
    max_inflight_requests = max(1, int(max_inflight_requests))

    logger.event("extract", "info", "start", prompt=str(prompt_path))

    tasks: list[dict[str, Any]] = []
    with open(sections_jsonl, "r", encoding="utf-8") as f_in:
        for line in f_in:
            if not line.strip():
                continue
            total += 1
            if limit is not None and total > int(limit):
                break
            tasks.append(json.loads(line))

    with ThreadPoolExecutor(max_workers=max_inflight_requests) as executor:
        future_map = {
            executor.submit(
                _extract_one,
                sec=sec,
                prompt_text=prompt_text,
                base_url=base_url,
                api_key=api_key,
                model=model,
                temperature=temperature,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                retry_backoff_seconds=retry_backoff_seconds,
                input_max_pages=input_max_pages,
                input_max_chars=input_max_chars,
            ): str(sec.get("doc_id") or "")
            for sec in tasks
        }

        for future in as_completed(future_map):
            doc_id = future_map[future]
            try:
                result = future.result()
                write_jsonl_line(
                    out_raw_jsonl,
                    {
                        "ts": utc_now_iso(),
                        "doc_id": result["doc_id"],
                        "raw": result["raw"],
                        "truncation": result["truncation"],
                    },
                )
                write_jsonl_line(out_extracted_jsonl, result["validated"])
                if result["truncation"].get("truncated"):
                    logger.event("extract", "info", "llm_input_truncated", doc_id=result["doc_id"], **result["truncation"])
                ok += 1
            except (ValidationError, ValueError) as e:
                failed += 1
                write_jsonl_line(
                    out_errors_jsonl,
                    {"ts": utc_now_iso(), "doc_id": doc_id, "error": str(e)},
                )
                logger.event("extract", "error", "extract_failed", doc_id=doc_id, error=str(e))
            except Exception as e:
                failed += 1
                write_jsonl_line(
                    out_errors_jsonl,
                    {"ts": utc_now_iso(), "doc_id": doc_id, "error": str(e)},
                )
                logger.event("extract", "error", "extract_failed", doc_id=doc_id, error=str(e))

    logger.event("extract", "info", "done", total=total, ok=ok, failed=failed)
    return {"total": total, "ok": ok, "failed": failed}
