# Coding Rules (Final Repo)

This repository follows the course constraints and reproducibility rules.

## Reproducibility
- Fixed data scope: cninfo public disclosures, date range `2023-01-01~2026-05-11`, markets `sse/szse`.
- One record = one PDF announcement (`doc_id = announcementId`).
- Step-based pipeline entry: `pipeline_run.py --step ...`.

## Data Authenticity (No Fabrication)
- The only data source is cninfo public metadata + cninfo public PDFs.
- If a field cannot be supported by the parsed text, output `null` / `[]`.
- `evidence_text` must be an exact substring from routed `section_text`.
- `page_no` must match the `[Page N]` markers injected by the section router; otherwise it must be `null`.

## Secrets / Submission Safety
- Never commit or submit `.env`. Only keep `.env.example`.
- No API keys in code, docs, logs, or reports.

## Operational Discipline
- Run steps sequentially for a consistent artifact set:
  - `route_sections -> extract -> validate -> report`
- Do not run multiple `pipeline_run.py` processes concurrently (can overwrite JSONL outputs).

