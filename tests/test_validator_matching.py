from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.logger import JsonlLogger
from src.utils import aligned_substring, is_substring
from src.validator import validate_and_repair


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


class MatchingRepairTests(unittest.TestCase):
    def test_aligned_substring_ignores_whitespace_only_differences(self) -> None:
        self.assertEqual(
            aligned_substring("你们应当于收到本决定书之日起10 个工作日内报送", "10个工作日"),
            "10 个工作日",
        )
        self.assertEqual(
            aligned_substring("公司\n未按规定及时履行信息披露义务", "公司未按规定及时履行信息披露义务"),
            "公司\n未按规定及时履行信息披露义务",
        )
        self.assertIsNone(aligned_substring("10 个工作日", "15个工作日"))
        self.assertFalse(
            is_substring(
                "公司时任董事长、总经理周文彬及时任董事会秘书曹晔未能勤勉地履行职责",
                "公司时任董事长、总经理周文彬未能勤勉地履行职责",
            )
        )

    def test_validate_repairs_whitespace_only_differences_but_keeps_real_mismatch_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sections_jsonl = root / "sections.jsonl"
            extracted_jsonl = root / "extracted.jsonl"
            final_results_jsonl = root / "final_results.jsonl"
            validation_errors_jsonl = root / "validation_errors.jsonl"
            log_path = root / "run_log.jsonl"

            _write_jsonl(
                sections_jsonl,
                [
                    {
                        "doc_id": "demo-1",
                        "section_text": (
                            "[Page 1]\n"
                            "公司时任董事长、总经理周文彬及时任董事会秘书曹晔未能勤勉地履行职责。\n"
                            "你们应当于收到本决定书之日起10 个工作日内向我局报送书面报告。"
                        ),
                    }
                ],
            )
            _write_jsonl(
                extracted_jsonl,
                [
                    {
                        "doc_id": "demo-1",
                        "stock_code": "000001",
                        "stock_name": "示例公司",
                        "market": "szse",
                        "publish_date": "2026-01-01",
                        "announcement_title": "关于收到监管措施决定书的公告",
                        "doc_type": "regulatory_measure",
                        "regulator_name": None,
                        "targets": [
                            {
                                "name": "周文彬",
                                "role": None,
                                "target_type": "executive",
                                "evidence": {
                                    "evidence_text": "公司时任董事长、总经理周文彬未能勤勉地履行职责",
                                    "page_no": 1,
                                },
                            }
                        ],
                        "issues": [],
                        "actions": [
                            {
                                "action_type": "written_report_required",
                                "action_source_type": "regulator_required",
                                "deadline": "10个工作日",
                                "required_disclosure": True,
                                "evidence": {
                                    "evidence_text": "你们应当于收到本决定书之日起10个工作日内向我局报送书面报告。",
                                    "page_no": 1,
                                },
                            }
                        ],
                        "source": {
                            "url": "http://example.com/demo.pdf",
                            "pdf_url": "http://example.com/demo.pdf",
                        },
                    }
                ],
            )

            validate_and_repair(
                extracted_jsonl=extracted_jsonl,
                sections_jsonl=sections_jsonl,
                final_results_jsonl=final_results_jsonl,
                validation_errors_jsonl=validation_errors_jsonl,
                logger=JsonlLogger(log_path),
            )

            final_rows = _read_jsonl(final_results_jsonl)
            self.assertEqual(len(final_rows), 1)
            final_row = final_rows[0]

            self.assertEqual(final_row["targets"], [])
            self.assertEqual(len(final_row["actions"]), 1)
            self.assertEqual(final_row["actions"][0]["deadline"], "10 个工作日")
            self.assertEqual(
                final_row["actions"][0]["evidence"]["evidence_text"],
                "你们应当于收到本决定书之日起10 个工作日内向我局报送书面报告。",
            )
            self.assertEqual(final_row["actions"][0]["evidence"]["page_no"], 1)

    def test_company_rectification_is_not_repaired_to_warning_letter_by_background_phrase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sections_jsonl = root / "sections.jsonl"
            extracted_jsonl = root / "extracted.jsonl"
            final_results_jsonl = root / "final_results.jsonl"
            validation_errors_jsonl = root / "validation_errors.jsonl"
            log_path = root / "run_log.jsonl"
            evidence = "公司及相关责任人高度重视《警示函》中所指出的问题，将认真吸取教训并引以为戒，积极进行整改。"

            _write_jsonl(
                sections_jsonl,
                [
                    {
                        "doc_id": "demo-2",
                        "section_text": f"[Page 2]\n{evidence}",
                    }
                ],
            )
            _write_jsonl(
                extracted_jsonl,
                [
                    {
                        "doc_id": "demo-2",
                        "stock_code": "000001",
                        "stock_name": "示例公司",
                        "market": "szse",
                        "publish_date": "2026-01-01",
                        "announcement_title": "关于收到警示函的公告",
                        "doc_type": "regulatory_measure",
                        "regulator_name": None,
                        "targets": [],
                        "issues": [],
                        "actions": [
                            {
                                "action_type": "rectification_required",
                                "action_source_type": "company_committed",
                                "deadline": None,
                                "required_disclosure": None,
                                "evidence": {
                                    "evidence_text": evidence,
                                    "page_no": 2,
                                },
                            }
                        ],
                        "source": {
                            "url": "http://example.com/demo.pdf",
                            "pdf_url": "http://example.com/demo.pdf",
                        },
                    }
                ],
            )

            validate_and_repair(
                extracted_jsonl=extracted_jsonl,
                sections_jsonl=sections_jsonl,
                final_results_jsonl=final_results_jsonl,
                validation_errors_jsonl=validation_errors_jsonl,
                logger=JsonlLogger(log_path),
            )

            final_rows = _read_jsonl(final_results_jsonl)
            self.assertEqual(final_rows[0]["actions"][0]["action_type"], "rectification_required")


if __name__ == "__main__":
    unittest.main()
