from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import ensure_parent_dir, utc_now_iso


def write_self_review(*, repo_root: Path, out_md: Path) -> Path:
    """
    Lightweight submission self-review checklist.
    This does NOT claim the pipeline is fully complete; it reports what exists on disk.
    """
    required_files = [
        "README.md",
        "requirements.txt",
        ".env.example",
        "pipeline_run.py",
        "configs/crawl_config.yaml",
        "configs/workflow.yaml",
        "configs/model_config.yaml",
        "configs/section_rules.yaml",
        "src/schemas.py",
        "prompts/prompt_v1.md",
        "prompts/prompt_final.md",
        "data/metadata/metadata.csv",
        "outputs/logs/sample_run_log.jsonl",
        "outputs/results/final_results.jsonl",
        "outputs/reports/eval_report_final.md",
        "outputs/reports/section_check_report.csv",
        "outputs/reports/parse_check.md",
        "demo_script.md",
        "final_slides.pdf",
        "ai_usage_statement.md",
        "ai_worklog_all.md",
    ]

    ensure_parent_dir(out_md)
    lines: list[str] = []
    lines.append(f"# Self Review ({utc_now_iso()})")
    lines.append("")
    lines.append("## Required Files (existence)")
    missing: list[str] = []
    for rel in required_files:
        p = repo_root / rel
        ok = p.exists()
        lines.append(f"- {'OK' if ok else 'MISSING'}: `{rel}`")
        if not ok:
            missing.append(rel)
    lines.append("")

    lines.append("## Runtime Preconditions")
    env_present = (repo_root / ".env").exists()
    lines.append(f"- `.env` present (should NOT be submitted): {'YES' if env_present else 'NO'}")
    lines.append("- Steps `parse/extract` require real keys in `.env` or shell env vars.")
    lines.append("")

    lines.append("## Pipeline Artifacts (may be empty until keys are configured)")
    artifacts = [
        "data/parsed/parsed_docs.jsonl",
        "data/parsed/sections.jsonl",
        "outputs/reports/section_check_report.csv",
        "outputs/tmp/extracted.jsonl",
        "outputs/results/final_results.jsonl",
        "outputs/logs/validation_errors.jsonl",
        "outputs/logs/parse_manifest.csv",
    ]
    for rel in artifacts:
        p = repo_root / rel
        if p.exists():
            size = p.stat().st_size
            lines.append(f"- `{rel}`: exists ({size} bytes)")
        else:
            lines.append(f"- `{rel}`: missing")
    lines.append("")

    if missing:
        lines.append("## Action Items")
        lines.append("- Fill missing required files above before final packaging.")
    else:
        lines.append("## Action Items")
        lines.append("- Configure MinerU + LLM keys, then run steps `parse/route_sections/extract/validate/report` to populate final results.")

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_md

