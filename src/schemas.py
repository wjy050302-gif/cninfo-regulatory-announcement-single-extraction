from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, StrictBool


DOC_TYPE_VALUES = (
    "attention_letter",
    "inquiry_letter",
    "regulatory_measure",
    "reply",
    "other",
)

TARGET_TYPE_VALUES = (
    "listed_company",
    "controlling_shareholder",
    "actual_controller",
    "director",
    "supervisor",
    "executive",
    "intermediary",
    "subsidiary",
    "shareholder_other",
    "other",
)

ISSUE_TYPE_VALUES = (
    "information_disclosure",
    "internal_control",
    "fund_occupation",
    "related_party_transaction",
    "raised_funds",
    "financial_irregularity",
    "mna_restructuring",
    "other",
)

ACTION_TYPE_VALUES = (
    "inquiry_reply_required",
    "rectification_required",
    "warning_letter",
    "supervisory_talk",
    "order_correction",
    "disclosure_update_required",
    "written_report_required",
    "other",
)

ACTION_SOURCE_TYPE_VALUES = (
    "regulator_required",
    "company_committed",
    "unclear",
)


class Evidence(BaseModel):
    evidence_text: str = Field(..., description="Exact quote snippet from the input section text.")
    page_no: Optional[int] = Field(
        default=None, description="1-based page number if known; otherwise null."
    )


class TextWithEvidence(BaseModel):
    value: str
    evidence: Evidence


TargetType = Literal[
    "listed_company",
    "controlling_shareholder",
    "actual_controller",
    "director",
    "supervisor",
    "executive",
    "intermediary",
    "subsidiary",
    "shareholder_other",
    "other",
]


class TargetItem(BaseModel):
    name: str
    role: Optional[str] = None
    target_type: TargetType
    evidence: Evidence


IssueType = Literal[
    "information_disclosure",
    "internal_control",
    "fund_occupation",
    "related_party_transaction",
    "raised_funds",
    "financial_irregularity",
    "mna_restructuring",
    "other",
]


class IssueItem(BaseModel):
    issue_type: IssueType
    issue_summary: str
    is_violation_related: Optional[StrictBool] = None
    evidence: Evidence


ActionType = Literal[
    "inquiry_reply_required",
    "rectification_required",
    "warning_letter",
    "supervisory_talk",
    "order_correction",
    "disclosure_update_required",
    "written_report_required",
    "other",
]

ActionSourceType = Literal[
    "regulator_required",
    "company_committed",
    "unclear",
]


class ActionItem(BaseModel):
    action_type: ActionType
    action_source_type: ActionSourceType
    deadline: Optional[str] = None
    required_disclosure: Optional[StrictBool] = None
    evidence: Evidence


class SourceInfo(BaseModel):
    url: str
    pdf_url: str


DocType = Literal["attention_letter", "inquiry_letter", "regulatory_measure", "reply", "other"]


class RegulatoryDocExtract(BaseModel):
    doc_id: str
    stock_code: str
    stock_name: str
    market: str
    publish_date: str  # YYYY-MM-DD
    announcement_title: str
    doc_type: DocType

    regulator_name: Optional[TextWithEvidence] = None
    targets: list[TargetItem] = Field(default_factory=list)
    issues: list[IssueItem] = Field(default_factory=list)
    actions: list[ActionItem] = Field(default_factory=list)

    source: SourceInfo
