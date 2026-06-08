from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import requests


def _chat_completions_url(base_url: str) -> str:
    b = (base_url or "").rstrip("/")
    if b.endswith("/v1"):
        return f"{b}/chat/completions"
    return f"{b}/v1/chat/completions"


def chat_completions(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float = 0.0,
    timeout_seconds: int = 60,
    max_retries: int = 0,
    retry_backoff_seconds: float = 3.0,
) -> str:
    if not base_url:
        raise RuntimeError("LLM_BASE_URL is empty")
    if not api_key:
        raise RuntimeError("LLM_API_KEY is empty")
    if not model:
        raise RuntimeError("LLM_MODEL is empty")

    url = _chat_completions_url(base_url)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)
            r.raise_for_status()
            js = r.json()
            break
        except requests.exceptions.Timeout as e:
            last_exc = e
            if attempt >= max_retries:
                raise
            time.sleep(retry_backoff_seconds * (attempt + 1))
        except requests.exceptions.ConnectionError as e:
            last_exc = e
            if attempt >= max_retries:
                raise
            time.sleep(retry_backoff_seconds * (attempt + 1))
        except requests.exceptions.SSLError as e:
            last_exc = e
            if attempt >= max_retries:
                raise
            time.sleep(retry_backoff_seconds * (attempt + 1))
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            last_exc = e
            if status is None or status < 500 or attempt >= max_retries:
                raise
            time.sleep(retry_backoff_seconds * (attempt + 1))
    else:
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("LLM request failed without exception")

    choices = js.get("choices") or []
    if not choices:
        raise RuntimeError(f"LLM returned no choices: {js}")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if not isinstance(content, str):
        raise RuntimeError(f"LLM content is not string: {js}")
    return content


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_BAD_ESCAPE_RE = re.compile(r'\\(?!["\\/bfnrtu])')


def _loads_json_with_repair(text: str) -> dict[str, Any] | None:
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    repaired = _BAD_ESCAPE_RE.sub(r"\\\\", text)
    if repaired != text:
        obj = json.loads(repaired)
        if isinstance(obj, dict):
            return obj
    return None


def parse_json_object(text: str) -> dict[str, Any]:
    """
    Best-effort JSON object extraction from LLM output.
    Strict JSON is preferred, but we try to recover from common wrappers.
    """
    t = (text or "").strip()
    if not t:
        raise ValueError("empty LLM output")

    # strip ```json fences
    m = _FENCE_RE.search(t)
    if m:
        t = m.group(1).strip()

    # direct parse
    obj = _loads_json_with_repair(t)
    if obj is not None:
        return obj

    # recover substring
    start = t.find("{")
    end = t.rfind("}")
    if start >= 0 and end > start:
        sub = t[start : end + 1]
        obj = _loads_json_with_repair(sub)
        if obj is not None:
            return obj

    raise ValueError("failed to parse JSON object from LLM output")
