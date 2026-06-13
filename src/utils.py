from __future__ import annotations

import datetime as _dt
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Iterable


def utc_now_iso() -> str:
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def ensure_parent_dir(path: str | Path) -> None:
    Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def write_jsonl_line(path: str | Path, obj: dict[str, Any]) -> None:
    ensure_parent_dir(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def read_yaml(path: str | Path) -> dict[str, Any]:
    import yaml

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def strip_em_tags(s: str) -> str:
    # cninfo returns <em> highlights in titles; keep plain text for downstream use.
    s = re.sub(r"</?em>", "", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def sleep_with_jitter(seconds: float, jitter: float = 0.2) -> None:
    # Small jitter helps reduce accidental burst patterns.
    if seconds <= 0:
        return
    time.sleep(seconds + (jitter * (0.5 - os.urandom(1)[0] / 255.0)))


_MATCH_WHITESPACE_RE = re.compile(r"[\s\u00A0\u3000]+")


def normalize_for_match(s: str) -> str:
    # For evidence matching, ignore whitespace-only OCR / formatting differences
    # but keep all non-whitespace characters strict.
    return _MATCH_WHITESPACE_RE.sub("", s or "")


def aligned_substring(haystack: str, needle: str) -> str | None:
    if not haystack or not needle:
        return None
    idx = haystack.find(needle)
    if idx >= 0:
        return haystack[idx : idx + len(needle)]

    norm_h_chars: list[str] = []
    norm_h_pos: list[int] = []
    for i, ch in enumerate(haystack):
        if ch.isspace() or ch in {"\u00A0", "\u3000"}:
            continue
        norm_h_chars.append(ch)
        norm_h_pos.append(i)

    norm_n_chars: list[str] = []
    for ch in needle:
        if ch.isspace() or ch in {"\u00A0", "\u3000"}:
            continue
        norm_n_chars.append(ch)

    norm_h = "".join(norm_h_chars)
    norm_n = "".join(norm_n_chars)
    if not norm_h or not norm_n:
        return None

    idx2 = norm_h.find(norm_n)
    if idx2 < 0:
        return None
    start = norm_h_pos[idx2]
    end = norm_h_pos[idx2 + len(norm_n) - 1] + 1
    return haystack[start:end]


def is_substring(haystack: str, needle: str) -> bool:
    if not haystack or not needle:
        return False
    return aligned_substring(haystack, needle) is not None


def chunked(iterable: Iterable[Any], n: int) -> Iterable[list[Any]]:
    buf: list[Any] = []
    for x in iterable:
        buf.append(x)
        if len(buf) >= n:
            yield buf
            buf = []
    if buf:
        yield buf
