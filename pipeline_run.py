#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.auditor import audit_dataset
from src.collector import collect_metadata
from src.downloader import download_pdfs
from src.extractor import run_extraction
from src.logger import JsonlLogger
from src.parser import parse_with_mineru
from src.reporter import write_eval_report
from src.section_router import route_sections
from src.utils import read_yaml
from src.validator import validate_and_repair


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="cninfo regulatory IE pipeline (step-based)")
    p.add_argument("--config", default="configs/workflow.yaml", help="workflow yaml path")
    p.add_argument(
        "--step",
        required=True,
        choices=[
            "collect",
            "download",
            "audit",
            "parse",
            "route_sections",
            "extract",
            "validate",
            "report",
            "all",
        ],
        help="which step to run",
    )
    p.add_argument("--limit", type=int, default=None, help="limit number of docs (debug)")
    p.add_argument("--prompt", default=None, help="prompt file for extract step")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # Load local secrets from .env if present (never commit .env).
    load_dotenv(override=True)

    workflow_cfg = read_yaml(args.config)
    paths = workflow_cfg.get("paths", {})
    cfg_paths = workflow_cfg.get("configs", {})

    repo_root = Path(paths.get("repo_root", ".")).resolve()
    logs_dir = repo_root / paths.get("logs_dir", "outputs/logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "sample_run_log.jsonl"
    logger = JsonlLogger(log_path)

    # Load sub configs
    crawl_cfg = read_yaml(repo_root / cfg_paths.get("crawl_config", "configs/crawl_config.yaml"))
    model_cfg_path = repo_root / cfg_paths.get("model_config", "configs/model_config.yaml")
    section_rules_path = repo_root / cfg_paths.get("section_rules", "configs/section_rules.yaml")

    metadata_csv = repo_root / paths.get("metadata_csv", "data/metadata/metadata.csv")
    pdf_dir = repo_root / paths.get("pdf_dir", "data/pdf")
    parsed_dir = repo_root / paths.get("parsed_dir", "data/parsed")
    reports_dir = repo_root / paths.get("reports_dir", "outputs/reports")
    results_dir = repo_root / paths.get("results_dir", "outputs/results")
    tmp_dir = repo_root / paths.get("tmp_dir", "outputs/tmp")
    logs_dir2 = repo_root / paths.get("logs_dir", "outputs/logs")

    parsed_jsonl = parsed_dir / "parsed_docs.jsonl"
    sections_jsonl = parsed_dir / "sections.jsonl"
    section_check_csv = reports_dir / "section_check_report.csv"

    extracted_jsonl = tmp_dir / "extracted.jsonl"
    llm_raw_jsonl = tmp_dir / "llm_raw.jsonl"
    extract_errors_jsonl = logs_dir2 / "extract_errors.jsonl"

    final_results_jsonl = results_dir / "final_results.jsonl"
    validation_errors_jsonl = logs_dir2 / "validation_errors.jsonl"
    eval_report_md = reports_dir / "eval_report_final.md"

    def step_collect() -> None:
        collect_metadata(crawl_cfg=crawl_cfg, repo_root=repo_root, logger=logger, limit=args.limit)

    def step_download() -> None:
        failed_csv = logs_dir2 / "failed_downloads.csv"
        download_pdfs(
            repo_root=repo_root,
            metadata_csv=metadata_csv,
            pdf_dir=pdf_dir,
            logger=logger,
            limit=args.limit,
            timeout_seconds=int(crawl_cfg.get("rate_limit", {}).get("timeout_seconds", 60)),
            max_retries=int(crawl_cfg.get("rate_limit", {}).get("max_retries", 3)),
            sleep_seconds=float(crawl_cfg.get("rate_limit", {}).get("sleep_seconds", 0.4)),
            throttle_seconds=float(crawl_cfg.get("rate_limit", {}).get("sleep_seconds", 0.4)),
            failed_csv=failed_csv,
        )

    def step_audit() -> None:
        report_path = reports_dir / "dataset_check_report.md"
        audit_dataset(metadata_csv=metadata_csv, report_path=report_path, logger=logger)

    def step_parse() -> None:
        model_cfg = read_yaml(model_cfg_path)
        mineru_cfg = model_cfg.get("mineru") or {}
        parse_with_mineru(
            metadata_csv=metadata_csv,
            parsed_dir=parsed_dir,
            logger=logger,
            limit=args.limit,
            mineru_base_url_env=mineru_cfg.get("base_url_env", "MINERU_BASE_URL"),
            mineru_api_key_env=mineru_cfg.get("api_key_env", "MINERU_API_KEY"),
            timeout_seconds=int(mineru_cfg.get("timeout_seconds", 120)),
            model_version=str(mineru_cfg.get("model_version", "pipeline")),
            poll_interval_seconds=float(mineru_cfg.get("poll_interval_seconds", 2.0)),
            max_wait_seconds=int(mineru_cfg.get("max_wait_seconds", 900)),
            max_failures_per_doc=int(mineru_cfg.get("max_failures_per_doc", 1)),
            max_inflight_tasks=int(mineru_cfg.get("max_inflight_tasks", 4)),
        )

    def step_route_sections() -> None:
        route_sections(
            parsed_jsonl=parsed_jsonl,
            section_rules_path=section_rules_path,
            sections_out_jsonl=sections_jsonl,
            section_check_report_csv=section_check_csv,
            logger=logger,
            limit=args.limit,
        )

    def step_extract() -> None:
        prompt_path = Path(args.prompt) if args.prompt else (repo_root / "prompts/prompt_final.md")
        model_cfg = read_yaml(model_cfg_path)
        llm_cfg = model_cfg.get("llm") or {}
        run_extraction(
            sections_jsonl=sections_jsonl,
            model_cfg_path=model_cfg_path,
            prompt_path=prompt_path,
            out_extracted_jsonl=extracted_jsonl,
            out_raw_jsonl=llm_raw_jsonl,
            out_errors_jsonl=extract_errors_jsonl,
            logger=logger,
            limit=args.limit,
            max_inflight_requests=int(llm_cfg.get("max_inflight_requests", 4)),
        )

    def step_validate() -> None:
        validate_and_repair(
            extracted_jsonl=extracted_jsonl,
            sections_jsonl=sections_jsonl,
            final_results_jsonl=final_results_jsonl,
            validation_errors_jsonl=validation_errors_jsonl,
            logger=logger,
            limit=args.limit,
        )

    def step_report() -> None:
        dataset_audit_md = reports_dir / "dataset_check_report.md"
        write_eval_report(
            metadata_csv=metadata_csv,
            dataset_audit_md=dataset_audit_md,
            parsed_jsonl=parsed_jsonl,
            section_check_csv=section_check_csv,
            extracted_jsonl=extracted_jsonl,
            final_results_jsonl=final_results_jsonl,
            validation_errors_jsonl=validation_errors_jsonl,
            out_report_md=eval_report_md,
            logger=logger,
        )

    if args.step == "collect":
        step_collect()
        return 0
    if args.step == "download":
        step_download()
        return 0
    if args.step == "audit":
        step_audit()
        return 0

    if args.step == "parse":
        step_parse()
        return 0
    if args.step == "route_sections":
        step_route_sections()
        return 0
    if args.step == "extract":
        step_extract()
        return 0
    if args.step == "validate":
        step_validate()
        return 0
    if args.step == "report":
        step_report()
        return 0

    if args.step == "all":
        step_collect()
        step_download()
        step_audit()
        step_parse()
        step_route_sections()
        step_extract()
        step_validate()
        step_report()

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
