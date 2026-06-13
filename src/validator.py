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
from .utils import aligned_substring, ensure_parent_dir, utc_now_iso, write_jsonl_line


# Section router injects markers like "[Page 12]".
_PAGE_MARK_RE = re.compile(r"\[Page\s+(\d+)\]")
_ACTION_TYPE_HINTS: list[tuple[tuple[str, ...], str]] = [
    (("采取出具警示函", "出具警示函", "警示函措施"), "warning_letter"),
    (("监管谈话",), "supervisory_talk"),
    (("责令改正",), "order_correction"),
    (("整改报告", "书面整改", "整改措施", "整改情况", "积极进行整改", "进行整改", "整改"), "rectification_required"),
    (("书面报告", "书面说明", "报送书面报告"), "written_report_required"),
    (("补充披露", "更新披露", "披露材料"), "disclosure_update_required"),
]


def _available_pages(section_text: str) -> set[int]:
    pages = set()
    for m in _PAGE_MARK_RE.finditer(section_text or ""):
        try:
            pages.add(int(m.group(1)))
        except Exception:
            pass
    return pages


def _page_blocks(section_text: str) -> list[tuple[int | None, str]]:
    text = section_text or ""
    matches = list(_PAGE_MARK_RE.finditer(text))
    if not matches:
        return [(None, text)]
    blocks: list[tuple[int | None, str]] = []
    for i, m in enumerate(matches):
        try:
            page_no = int(m.group(1))
        except Exception:
            page_no = None
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        blocks.append((page_no, text[start:end]))
    return blocks


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
    matched: list[str] = []
    for needles, action_type in _ACTION_TYPE_HINTS:
        if any(needle in raw for needle in needles):
            matched.append(action_type)
    unique = list(dict.fromkeys(matched))
    # A single evidence sentence can mention multiple actions. In that case the
    # validator should not overwrite the model's more specific item-level label.
    return unique[0] if len(unique) == 1 else None


def _locate_evidence(
    section_text: str, evidence_text: str, claimed_page_no: int | None
) -> tuple[str, int | None] | None:
    if not section_text or not evidence_text:
        return None

    blocks = _page_blocks(section_text)

    def _match_in_block(text: str) -> str | None:
        return aligned_substring(text, evidence_text)

    if claimed_page_no is not None:
        for page_no, block_text in blocks:
            if page_no != claimed_page_no:
                continue
            matched = _match_in_block(block_text)
            if matched is not None:
                return matched, claimed_page_no

    matches: list[tuple[str, int | None]] = []
    for page_no, block_text in blocks:
        matched = _match_in_block(block_text)
        if matched is not None:
            matches.append((matched, page_no))

    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]

    first_text = matches[0][0]
    if all(text == first_text for text, _ in matches):
        return first_text, None

    return first_text, None


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
                claimed_page_no = _sanitize_page_no(e.get("page_no"), available_pages)
                located = _locate_evidence(section_text, et, claimed_page_no)
                if located is None:
                    errors.append(f"{path}: evidence_text not substring")
                    return None
                matched_text, matched_page_no = located
                if e.get("evidence_text") != matched_text:
                    e["evidence_text"] = matched_text
                    changed = True
                if e.get("page_no") != matched_page_no:
                    e["page_no"] = matched_page_no
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
                            matched_deadline = aligned_substring(str(ev.get("evidence_text") or ""), deadline)
                            if matched_deadline is None:
                                errors.append(f"actions[{i}]: deadline cleared because evidence does not support it")
                                it["deadline"] = None
                                changed = True
                            elif matched_deadline != deadline:
                                it["deadline"] = matched_deadline
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
