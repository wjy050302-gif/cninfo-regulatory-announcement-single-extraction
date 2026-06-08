from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import requests


@dataclass(frozen=True)
class MinerUExtractResult:
    task_id: str
    status: str
    full_zip_url: str | None


class MinerUClient:
    """
    MinerU API client (token-based v4).

    This implementation follows the public MinerU docs:
    - POST /api/v4/extract/task
    - GET  /api/v4/extract/task/{task_id}
    """

    def __init__(self, base_url: str, api_key: str, timeout_seconds: int = 120):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()
        self.timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        }

    def create_extract_task(self, *, file_url: str, model_version: str = "vlm") -> str:
        url = f"{self.base_url}/api/v4/extract/task"
        payload = {"url": file_url, "model_version": model_version}
        r = requests.post(url, headers=self._headers(), json=payload, timeout=self.timeout_seconds)
        r.raise_for_status()
        js = r.json()
        data = js.get("data") or {}
        task_id = data.get("task_id") or data.get("taskId") or ""
        if not task_id:
            raise RuntimeError(f"MinerU create task failed: {js}")
        return str(task_id)

    def get_task(self, task_id: str) -> MinerUExtractResult:
        url = f"{self.base_url}/api/v4/extract/task/{task_id}"
        r = requests.get(url, headers=self._headers(), timeout=self.timeout_seconds)
        r.raise_for_status()
        js = r.json()
        data = js.get("data") or {}
        status = (data.get("state") or data.get("status") or "").lower()
        # MinerU docs show "full_zip_url" at top-level of data for single-file extract.
        full_zip_url = data.get("full_zip_url") or data.get("fullZipUrl")
        # Some versions may nest results under extract_result; keep best-effort compatibility.
        if not full_zip_url:
            extract_result = data.get("extract_result") or data.get("extractResult") or []
            if isinstance(extract_result, list) and extract_result:
                item0 = extract_result[0] or {}
                full_zip_url = item0.get("full_zip_url") or item0.get("fullZipUrl")
        return MinerUExtractResult(task_id=str(task_id), status=status, full_zip_url=full_zip_url)

    def wait_for_zip_url(
        self,
        task_id: str,
        *,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: int = 300,
    ) -> str:
        import time

        start = time.time()
        while True:
            res = self.get_task(task_id)
            if res.full_zip_url:
                return res.full_zip_url
            if time.time() - start > max_wait_seconds:
                raise TimeoutError(f"MinerU task timeout after {max_wait_seconds}s: {task_id}")
            time.sleep(poll_interval_seconds)


def download_zip(url: str, dest_path: Path, timeout_seconds: int = 120) -> Path:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, stream=True, timeout=timeout_seconds, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 256):
            if chunk:
                f.write(chunk)
    return dest_path


def extract_full_md_and_content_list(zip_path: Path) -> tuple[str | None, dict[str, Any] | None]:
    """
    Returns (full_md_text, content_list_json).
    We search in the zip for files ending with:
    - 'full.md'
    - 'content_list.json'
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        full_md_name = next((n for n in names if n.lower().endswith("full.md")), None)
        content_list_name = next((n for n in names if n.lower().endswith("content_list.json")), None)

        full_md_text = None
        if full_md_name:
            with zf.open(full_md_name, "r") as f:
                full_md_text = f.read().decode("utf-8", errors="replace")

        content_list = None
        if content_list_name:
            with zf.open(content_list_name, "r") as f:
                content_list = json.loads(f.read().decode("utf-8", errors="replace"))

        return full_md_text, content_list


def build_pages_from_content_list(content_list: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Convert MinerU content_list.json to a list of pages:
    [{page_no: 1, page_idx: 0, text: "..."}]

    The referenced MinerU docs indicate page_idx is 0-based.
    """
    pages: dict[int, list[str]] = {}
    if not isinstance(content_list, list):
        # Some versions wrap it in an object; best-effort.
        items = content_list.get("content_list") if isinstance(content_list, dict) else []
    else:
        items = content_list

    for item in items or []:
        if not isinstance(item, dict):
            continue
        page_idx = item.get("page_idx")
        if page_idx is None:
            continue
        try:
            p = int(page_idx)
        except Exception:
            continue
        text = item.get("text")
        if not isinstance(text, str):
            continue
        pages.setdefault(p, []).append(text.strip())

    out: list[dict[str, Any]] = []
    for page_idx in sorted(pages.keys()):
        joined = "\n".join(t for t in pages[page_idx] if t)
        out.append({"page_idx": page_idx, "page_no": page_idx + 1, "text": joined})
    return out
