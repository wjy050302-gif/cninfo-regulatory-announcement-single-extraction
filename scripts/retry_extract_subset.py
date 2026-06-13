#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.extractor import _extract_one
from src.logger import JsonlLogger
from src.utils import ensure_parent_dir, read_yaml, utc_now_iso, write_jsonl_line


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Retry extract for a subset of doc_ids with custom timeout.")
    p.add_argument("--sections-jsonl", default="data/parsed/sections.jsonl")
    p.add_argument("--model-config", default="configs/model_config.yaml")
    p.add_argument("--prompt", default="prompts/prompt_final.md")
    p.add_argument("--doc-id", action="append", dest="doc_ids", default=[], help="doc_id to retry; repeatable")
    p.add_argument("--timeout-seconds", type=int, default=600)
    p.add_argument("--max-retries", type=int, default=2)
    p.add_argument("--retry-backoff-seconds", type=float, default=8.0)
    p.add_argument("--max-inflight-requests", type=int, default=2)
    p.add_argument("--out-dir", default=None, help="output directory; default outputs/tmp/retry_extract_<ts>")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv(override=True)

    repo_root = REPO_ROOT
    sections_jsonl = (repo_root / args.sections_jsonl).resolve()
    model_cfg_path = (repo_root / args.model_config).resolve()
    prompt_path = (repo_root / args.prompt).resolve()

    model_cfg = read_yaml(model_cfg_path)
    llm_cfg = model_cfg.get("llm") or {}
    base_url_env = llm_cfg.get("base_url_env", "LLM_BASE_URL")
    api_key_env = llm_cfg.get("api_key_env", "LLM_API_KEY")
    model_env = llm_cfg.get("model_env", "LLM_MODEL")

    base_url = (os.getenv(base_url_env) or "").strip()
    api_key = (os.getenv(api_key_env) or "").strip()
    model = (os.getenv(model_env) or "").strip()
    if not base_url or not api_key or not model:
        raise RuntimeError(f"LLM config missing. Need env {base_url_env}, {api_key_env}, {model_env}.")

    if not args.doc_ids:
        raise RuntimeError("Need at least one --doc-id")

    input_max_pages = int(llm_cfg.get("input_max_pages", 0) or 0)
    input_max_chars = int(llm_cfg.get("input_max_chars", 0) or 0)
    temperature = float(llm_cfg.get("temperature", 0.0))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir) if args.out_dir else (repo_root / f"outputs/tmp/retry_extract_{ts}")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_extracted = out_dir / "extracted.jsonl"
    out_raw = out_dir / "llm_raw.jsonl"
    out_errors = out_dir / "extract_errors.jsonl"
    out_meta = out_dir / "meta.json"
    log_path = repo_root / "outputs/logs/sample_run_log.jsonl"
    logger = JsonlLogger(log_path)

    ensure_parent_dir(out_extracted)
    ensure_parent_dir(out_raw)
    ensure_parent_dir(out_errors)

    targets = set(str(x).strip() for x in args.doc_ids if str(x).strip())
    sections: list[dict[str, Any]] = []
    with open(sections_jsonl, "r", encoding="utf-8") as f_in:
        for line in f_in:
            if not line.strip():
                continue
            obj = json.loads(line)
            if str(obj.get("doc_id") or "") in targets:
                sections.append(obj)

    found_doc_ids = [str(sec.get("doc_id") or "") for sec in sections]
    missing_doc_ids = sorted(targets - set(found_doc_ids))

    prompt_text = prompt_path.read_text(encoding="utf-8")
    logger.event(
        "extract_retry",
        "info",
        "start",
        total=len(sections),
        requested_doc_ids=sorted(targets),
        missing_doc_ids=missing_doc_ids,
        timeout_seconds=args.timeout_seconds,
    )

    ok = 0
    failed = 0
    with ThreadPoolExecutor(max_workers=max(1, int(args.max_inflight_requests))) as executor:
        future_map = {
            executor.submit(
                _extract_one,
                sec=sec,
                prompt_text=prompt_text,
                base_url=base_url,
                api_key=api_key,
                model=model,
                temperature=temperature,
                timeout_seconds=int(args.timeout_seconds),
                max_retries=int(args.max_retries),
                retry_backoff_seconds=float(args.retry_backoff_seconds),
                input_max_pages=input_max_pages,
                input_max_chars=input_max_chars,
            ): str(sec.get("doc_id") or "")
            for sec in sections
        }

        for future in as_completed(future_map):
            doc_id = future_map[future]
            try:
                result = future.result()
                write_jsonl_line(
                    out_raw,
                    {
                        "ts": utc_now_iso(),
                        "doc_id": result["doc_id"],
                        "raw": result["raw"],
                        "truncation": result["truncation"],
                    },
                )
                write_jsonl_line(out_extracted, result["validated"])
                ok += 1
            except (ValidationError, ValueError) as e:
                failed += 1
                write_jsonl_line(out_errors, {"ts": utc_now_iso(), "doc_id": doc_id, "error": str(e)})
                logger.event("extract_retry", "error", "extract_failed", doc_id=doc_id, error=str(e))
            except Exception as e:
                failed += 1
                write_jsonl_line(out_errors, {"ts": utc_now_iso(), "doc_id": doc_id, "error": str(e)})
                logger.event("extract_retry", "error", "extract_failed", doc_id=doc_id, error=str(e))

    out_meta.write_text(
        json.dumps(
            {
                "requested_doc_ids": sorted(targets),
                "found_doc_ids": found_doc_ids,
                "missing_doc_ids": missing_doc_ids,
                "timeout_seconds": args.timeout_seconds,
                "max_retries": args.max_retries,
                "retry_backoff_seconds": args.retry_backoff_seconds,
                "max_inflight_requests": args.max_inflight_requests,
                "ok": ok,
                "failed": failed,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    logger.event(
        "extract_retry",
        "info",
        "done",
        total=len(sections),
        ok=ok,
        failed=failed,
        out_dir=str(out_dir),
    )
    print(str(out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
