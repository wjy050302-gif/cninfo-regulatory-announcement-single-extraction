from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .logger import JsonlLogger
from .schemas import (
    ACTION_TYPE_VALUES,
    ACTION_SOURCE_TYPE_VALUES,
    ISSUE_TYPE_VALUES,
    TARGET_TYPE_VALUES,
    RegulatoryDocExtract,
)
from .utils import ensure_parent_dir, is_substring, utc_now_iso, write_jsonl_line


# Section router injects markers like "[Page 12]".
_PAGE_MARK_RE = re.compile(r"\[Page\s+(\d+)\]")
_ACTION_TYPE_HINTS: list[tuple[str, str]] = [
    ("警示函", "warning_letter"),
    ("监管谈话", "supervisory_talk"),
    ("责令改正", "order_correction"),
    ("书面报告", "written_report_required"),
    ("书面说明", "written_report_required"),
    ("报送书面报告", "written_report_required"),
    ("补充披露", "disclosure_update_required"),
    ("更新披露", "disclosure_update_required"),
    ("披露材料", "disclosure_update_required"),
    ("整改措施", "rectification_required"),
    ("整改情况", "rectification_required"),
    ("整改", "rectification_required"),
]


def _available_pages(section_text: str) -> set[int]:
    pages = set()
    for m in _PAGE_MARK_RE.finditer(section_text or ""):
        try:
            pages.add(int(m.group(1)))
        except Exception:
            pass
    return pages


def _sanitize_page_no(page_no: int | None, available: set[int]) -> int | None:
    if page_no is None:
        return None
    try:
        p = int(page_no)
    except Exception:
        return None
    return p if p in available else None


def _is_optional_str(v: Any) -> bool:
    return v is None or isinstance(v, str)


def _is_optional_bool(v: Any) -> bool:
    return v is None or isinstance(v, bool)


def _infer_action_type_from_evidence(text: str) -> str | None:
    raw = text or ""
    for needle, action_type in _ACTION_TYPE_HINTS:
        if needle in raw:
            return action_type
    return None


def validate_and_repair(
    *,
    extracted_jsonl: Path,
    sections_jsonl: Path,
    final_results_jsonl: Path,
    validation_errors_jsonl: Path,
    logger: JsonlLogger,
    limit: int | None = None,
) -> dict[str, Any]:
    # Build doc_id -> section_text
    section_map: dict[str, str] = {}
    with open(sections_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            doc_id = str(obj.get("doc_id") or "")
            if doc_id:
                section_map[doc_id] = str(obj.get("section_text") or "")

    for p in (final_results_jsonl, validation_errors_jsonl):
        if p.exists():
            p.unlink()
    ensure_parent_dir(final_results_jsonl)
    ensure_parent_dir(validation_errors_jsonl)

    total = 0
    ok = 0
    repaired = 0
    dropped = 0
    deduped = 0

    logger.event("validate", "info", "start", extracted=str(extracted_jsonl))

    # If `extract` was accidentally run multiple times in parallel, `extracted.jsonl`
    # can contain duplicate doc_id entries. Keep the first one for determinism.
    seen_doc_ids: set[str] = set()

    with open(extracted_jsonl, "r", encoding="utf-8") as f_in:
        for line in f_in:
            if not line.strip():
                continue
            total += 1
            if limit is not None and total > int(limit):
                break

            obj = json.loads(line)
            doc_id = str(obj.get("doc_id") or "")
            if doc_id and doc_id in seen_doc_ids:
                deduped += 1
                continue
            if doc_id:
                seen_doc_ids.add(doc_id)
            section_text = section_map.get(doc_id, "")
            available_pages = _available_pages(section_text)

            errors: list[str] = []
            changed = False

            # Validate evidence substrings and page ranges
            def check_evidence(e: dict[str, Any], path: str) -> dict[str, Any] | None:
                nonlocal changed
                if not isinstance(e, dict):
                    errors.append(f"{path}: evidence not object")
                    return None
                et = e.get("evidence_text")
                if not isinstance(et, str) or not et.strip():
                    errors.append(f"{path}: missing evidence_text")
                    return None
                if not is_substring(section_text, et):
                    errors.append(f"{path}: evidence_text not substring")
                    return None
                pn = e.get("page_no")
                pn2 = _sanitize_page_no(pn, available_pages)
                if pn != pn2:
                    e["page_no"] = pn2
                    changed = True
                return e

            # regulator_name
            reg = obj.get("regulator_name")
            if reg is not None:
                if not isinstance(reg, dict) or not isinstance(reg.get("value"), str):
                    errors.append("regulator_name: invalid structure")
                    obj["regulator_name"] = None
                    changed = True
                else:
                    ev = check_evidence(reg.get("evidence"), "regulator_name.evidence")
                    if ev is None:
                        obj["regulator_name"] = None
                        changed = True
                    else:
                        reg["evidence"] = ev

            # targets
            targets = obj.get("targets")
            if targets is not None:
                if not isinstance(targets, list):
                    errors.append("targets: not a list")
                    obj["targets"] = []
                    changed = True
                else:
                    kept_targets: list[Any] = []
                    for i, it in enumerate(targets):
                        if not isinstance(it, dict):
                            errors.append(f"targets[{i}]: item not object")
                            changed = True
                            continue
                        if not isinstance(it.get("name"), str) or not str(it.get("name")).strip():
                            errors.append(f"targets[{i}]: missing name")
                            changed = True
                            continue
                        target_type = it.get("target_type")
                        if not isinstance(target_type, str) or target_type not in TARGET_TYPE_VALUES:
                            errors.append(f"targets[{i}]: invalid target_type={target_type!r}")
                            changed = True
                            continue
                        if not _is_optional_str(it.get("role")):
                            errors.append(f"targets[{i}]: invalid role")
                            it["role"] = None
                            changed = True
                        ev = check_evidence(it.get("evidence"), f"targets[{i}].evidence")
                        if ev is None:
                            changed = True
                            continue
                        it["evidence"] = ev
                        kept_targets.append(it)
                    if len(kept_targets) != len(targets):
                        obj["targets"] = kept_targets
                        changed = True

            # issues
            issues = obj.get("issues")
            if issues is not None:
                if not isinstance(issues, list):
                    errors.append("issues: not a list")
                    obj["issues"] = []
                    changed = True
                else:
                    kept_issues: list[Any] = []
                    for i, it in enumerate(issues):
                        if not isinstance(it, dict):
                            errors.append(f"issues[{i}]: item not object")
                            changed = True
                            continue
                        issue_type = it.get("issue_type")
                        if not isinstance(issue_type, str) or issue_type not in ISSUE_TYPE_VALUES:
                            errors.append(f"issues[{i}]: invalid issue_type={issue_type!r}")
                            changed = True
                            continue
                        if not isinstance(it.get("issue_summary"), str) or not str(it.get("issue_summary")).strip():
                            errors.append(f"issues[{i}]: missing issue_summary")
                            changed = True
                            continue
                        if not _is_optional_bool(it.get("is_violation_related")):
                            errors.append(f"issues[{i}]: invalid is_violation_related")
                            it["is_violation_related"] = None
                            changed = True
                        ev = check_evidence(it.get("evidence"), f"issues[{i}].evidence")
                        if ev is None:
                            changed = True
                            continue
                        it["evidence"] = ev
                        kept_issues.append(it)
                    if len(kept_issues) != len(issues):
                        obj["issues"] = kept_issues
                        changed = True

            # actions
            actions = obj.get("actions")
            if actions is not None:
                if not isinstance(actions, list):
                    errors.append("actions: not a list")
                    obj["actions"] = []
                    changed = True
                else:
                    kept_actions: list[Any] = []
                    for i, it in enumerate(actions):
                        if not isinstance(it, dict):
                            errors.append(f"actions[{i}]: item not object")
                            changed = True
                            continue
                        action_type = it.get("action_type")
                        if not isinstance(action_type, str) or action_type not in ACTION_TYPE_VALUES:
                            errors.append(f"actions[{i}]: invalid action_type={action_type!r}")
                            changed = True
                            continue
                        action_source_type = it.get("action_source_type")
                        if not isinstance(action_source_type, str) or action_source_type not in ACTION_SOURCE_TYPE_VALUES:
                            errors.append(
                                f"actions[{i}]: invalid action_source_type={action_source_type!r}"
                            )
                            it["action_source_type"] = "unclear"
                            changed = True
                        if not _is_optional_str(it.get("deadline")):
                            errors.append(f"actions[{i}]: invalid deadline")
                            it["deadline"] = None
                            changed = True
                        if not _is_optional_bool(it.get("required_disclosure")):
                            errors.append(f"actions[{i}]: invalid required_disclosure")
                            it["required_disclosure"] = None
                            changed = True
                        ev = check_evidence(it.get("evidence"), f"actions[{i}].evidence")
                        if ev is None:
                            changed = True
                            continue
                        it["evidence"] = ev
                        inferred_action_type = _infer_action_type_from_evidence(ev.get("evidence_text") or "")
                        if inferred_action_type and it.get("action_type") != inferred_action_type:
                            errors.append(
                                f"actions[{i}]: action_type repaired from {it.get('action_type')!r} to {inferred_action_type!r}"
                            )
                            it["action_type"] = inferred_action_type
                            changed = True
                        deadline = it.get("deadline")
                        if isinstance(deadline, str) and deadline.strip():
                            if deadline not in str(ev.get("evidence_text") or ""):
                                errors.append(f"actions[{i}]: deadline cleared because evidence does not support it")
                                it["deadline"] = None
                                changed = True
                        kept_actions.append(it)
                    if len(kept_actions) != len(actions):
                        obj["actions"] = kept_actions
                        changed = True

            try:
                validated = RegulatoryDocExtract.model_validate(obj)
            except ValidationError as e:
                dropped += 1
                write_jsonl_line(
                    validation_errors_jsonl,
                    {"ts": utc_now_iso(), "doc_id": doc_id, "error": str(e), "evidence_errors": errors},
                )
                logger.event("validate", "error", "pydantic_failed", doc_id=doc_id, error=str(e))
                continue

            if errors:
                repaired += 1
                write_jsonl_line(
                    validation_errors_jsonl,
                    {"ts": utc_now_iso(), "doc_id": doc_id, "error": "evidence_repaired", "details": errors},
                )

            write_jsonl_line(final_results_jsonl, validated.model_dump())
            ok += 1

    logger.event(
        "validate",
        "info",
        "done",
        total=total,
        ok=ok,
        repaired=repaired,
        dropped=dropped,
        deduped=deduped,
    )
    return {"total": total, "ok": ok, "repaired": repaired, "dropped": dropped, "deduped": deduped}
