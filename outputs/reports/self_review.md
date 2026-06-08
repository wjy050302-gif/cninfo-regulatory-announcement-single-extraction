# Self Review (2026-06-08T07:04:30Z)

## Required Files (existence)
- OK: `README.md`
- OK: `requirements.txt`
- OK: `.env.example`
- OK: `pipeline_run.py`
- OK: `configs/crawl_config.yaml`
- OK: `configs/workflow.yaml`
- OK: `configs/model_config.yaml`
- OK: `configs/section_rules.yaml`
- OK: `src/schemas.py`
- OK: `prompts/prompt_v1.md`
- OK: `prompts/prompt_final.md`
- OK: `data/metadata/metadata.csv`
- OK: `outputs/logs/sample_run_log.jsonl`
- OK: `outputs/results/final_results.jsonl`
- OK: `outputs/reports/eval_report_final.md`
- OK: `outputs/reports/section_check_report.csv`
- OK: `outputs/reports/parse_check.md`
- OK: `demo_script.md`
- OK: `final_slides.pdf`
- OK: `ai_usage_statement.md`
- OK: `ai_worklog_all.md`

## Runtime Preconditions
- `.env` present (should NOT be submitted): YES
- Steps `parse/extract` require real keys in `.env` or shell env vars.

## Pipeline Artifacts (may be empty until keys are configured)
- `data/parsed/parsed_docs.jsonl`: exists (4149870 bytes)
- `data/parsed/sections.jsonl`: exists (497132 bytes)
- `outputs/reports/section_check_report.csv`: exists (43449 bytes)
- `outputs/tmp/extracted.jsonl`: exists (371929 bytes)
- `outputs/results/final_results.jsonl`: exists (295488 bytes)
- `outputs/logs/validation_errors.jsonl`: exists (20828 bytes)
- `outputs/logs/parse_manifest.csv`: exists (13101 bytes)

## Action Items
- Configure MinerU + LLM keys, then run steps `parse/route_sections/extract/validate/report` to populate final results.
