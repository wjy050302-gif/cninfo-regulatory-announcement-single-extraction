# Evidence Chain Example (Template)

Use this file only after the current single-announcement rerun has produced
`outputs/results/final_results.jsonl`.

Replace `<doc_id>` below with one real record from the current run.

## 1) Identify the doc in final results
- File: `outputs/results/final_results.jsonl`
- Example doc_id: `<doc_id>`

## 2) Locate the original PDF
- `data/pdf/<doc_id>.pdf`
- Traceability fields come from `data/metadata/metadata.csv` (`doc_id`, `pdf_url`, `publish_date`, etc.).

## 3) MinerU parsed output
- Parsed JSONL: `data/parsed/parsed_docs.jsonl` (record contains `pages[]` and MinerU metadata)
- Parsed markdown: `data/parsed/markdown/<doc_id>.md` (if present)

## 4) Section routing output (with page markers)
- Routed section: `data/parsed/sections.jsonl` (find the line with doc_id `<doc_id>`)
- The router injects `[Page N]` markers into `section_text` for page attribution.

## 5) Extract + Validate artifacts
- Raw model output (for audit): `outputs/tmp/llm_raw.jsonl`
- Pydantic-pass extraction output: `outputs/tmp/extracted.jsonl`
- Evidence validation / repairs: `outputs/logs/validation_errors.jsonl`
- Final structured results: `outputs/results/final_results.jsonl`

## 6) Manual verification recipe
1. Open the PDF and find the sentence fragment used as `evidence_text`.
2. Confirm the evidence snippet supports the extracted value.
3. Confirm the evidence page equals the `page_no` in the result.

## 7) Current status
- This file is a template before `extract -> validate -> report` completes.
- After the final rerun, replace `<doc_id>` with one fixed single-announcement sample.
