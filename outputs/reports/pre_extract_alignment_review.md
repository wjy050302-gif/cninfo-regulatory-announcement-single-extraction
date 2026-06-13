# Pre-Extract Alignment Review

Date: 2026-05-24

## Scope Checked
- `topic_proposal.md`
- `crawl_spec.md`
- `difficulty_declaration.md`
- `workflow_design.md`
- `README.md`
- `demo_script.md`
- `submission_checklist/`
- `sample_checks/`
- `configs/crawl_config.yaml`
- `src/collector.py`
- `data/metadata/metadata.csv`

## Goal
Confirm that the project is aligned with the teacher-reviewed target before running `extract`:

- single-announcement extraction only
- no inquiry-reply cross-document closure
- structured schema with whitelist enums
- cninfo-only real data
- sample set focused on substantive regulatory announcement text rather than attachment-like notices

## Findings

### 1) Submission checklist still pointed to the old manual-eval file
- Problem:
  - `submission_checklist/week16_submit_list.md`
  - `submission_checklist/manifest.csv`
  still referenced `manual_eval_filled_evidence_chain.csv`
- Why it mattered:
  - the main evaluation design had already shifted to field-level single-announcement evaluation
- Action taken:
  - updated both files to point to `outputs/reports/manual_eval_filled_single_announcement.csv`

### 2) Evidence-chain sample was stale
- Problem:
  - `sample_checks/evidence_chain_example.md` hard-coded an old `doc_id`
  - after the new rerun started, that example no longer matched the current outputs
- Why it mattered:
  - it could mislead final checking and demo preparation
- Action taken:
  - converted it into a template that must be filled with one real `doc_id` from the final rerun

### 3) Main metadata sample initially drifted away from the intended target
- Problem:
  - after the first refactor pass, `metadata.csv` still contained many titles such as:
    - reply + prospectus update notices
    - law-firm legal opinions
    - accounting-firm standalone replies
    - special explanations / verification opinions
- Why it mattered:
  - these are often attachment-like or intermediary-only documents
  - they weaken the project claim that the unit is a substantive regulatory single-announcement text
- Action taken:
  - added `attachment_exclude_keywords` in `configs/crawl_config.yaml`
  - updated `src/collector.py` to exclude attachment-like titles for `attention_letter / inquiry_letter / reply`
  - updated `topic_proposal.md` and `crawl_spec.md` to document the rule

## Current Status After Fixes
- scope documents are now consistent with single-announcement extraction
- submission checklist is consistent with the new evaluation design
- sample-check artifact is no longer tied to stale outputs
- metadata was regenerated under the tighter filter before resuming downstream steps

## Remaining Non-Blocking Item
- `demo_script.md` still does not contain a fixed `doc_id`
- this is expected before `final_results.jsonl` is regenerated
- it should be finalized after `validate`

## Known Residual Risk
- current sample distribution is still skewed toward `reply` and `regulatory_measure`
- this is a real data distribution outcome under the current time range + keyword rules
- it should be explained explicitly in the final report and slides rather than hidden
