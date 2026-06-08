from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import utc_now_iso, write_jsonl_line


class JsonlLogger:
    def __init__(self, log_path: str | Path):
        self.log_path = Path(log_path)

    def event(self, step: str, level: str, message: str, **fields: Any) -> None:
        obj: dict[str, Any] = {
            "ts": utc_now_iso(),
            "step": step,
            "level": level,
            "message": message,
            **fields,
        }
        write_jsonl_line(self.log_path, obj)

