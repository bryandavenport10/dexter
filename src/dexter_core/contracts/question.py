"""Governed operational questions and their traceable answers."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping
from uuid import UUID

from ..enums import StringEnum
from ..serialization import contract_to_dict, contract_to_json
from ..validation import ValidationIssue, ValidationReport
from .observation import utc_timestamp

QUESTION_CONTRACT_TYPE = "dexter.question"
QUESTION_VERSION = "1.0"
ANSWER_CONTRACT_TYPE = "dexter.answer"
ANSWER_VERSION = "1.0"


class QuestionType(StringEnum):
    WHAT = "WHAT"
    WHY = "WHY"
    WHEN = "WHEN"
    WHERE = "WHERE"
    WHICH = "WHICH"
    STATUS = "STATUS"
    UNKNOWN = "UNKNOWN"


class AnswerConfidence(StringEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CERTAIN = "CERTAIN"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class Question:
    question_id: str
    question_type: QuestionType
    question_text: str
    asked_at: datetime
    authority_reference: str
    revision: int = 1
    version: str = QUESTION_VERSION
    contract_type: str = field(default=QUESTION_CONTRACT_TYPE, init=False)

    def __post_init__(self) -> None:
        for name in ("question_id", "question_text", "authority_reference", "version"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string")
            object.__setattr__(self, name, value.strip())
        object.__setattr__(self, "asked_at", utc_timestamp(self.asked_at, "asked_at"))

    def validate(self) -> ValidationReport:
        issues: list[ValidationIssue] = []
        if not _valid_identity(self.question_id, "question"):
            issues.append(ValidationIssue("invalid_question_identity", "question_id must be dexter:question:<uuid>", "$.question_id"))
        if not isinstance(self.question_type, QuestionType) or self.question_type is QuestionType.UNKNOWN:
            issues.append(ValidationIssue("invalid_question_type", "question_type must be recognized and cannot be UNKNOWN", "$.question_type"))
        if not self.question_text:
            issues.append(ValidationIssue("missing_question_text", "question_text is required", "$.question_text"))
        if not self.authority_reference:
            issues.append(ValidationIssue("missing_authority_reference", "authority_reference is required", "$.authority_reference"))
        _validate_revision_version(issues, self.revision, self.version, QUESTION_VERSION)
        return ValidationReport(tuple(issues))


@dataclass(frozen=True, slots=True)
class Answer:
    answer_id: str
    question_reference: str
    primary_assessment_reference: str
    supporting_assessment_references: tuple[str, ...]
    answer_text: str
    confidence: AnswerConfidence
    answered_at: datetime
    authority_reference: str
    evidence_references: tuple[str, ...]
    relationship_references: tuple[str, ...]
    revision: int = 1
    version: str = ANSWER_VERSION
    contract_type: str = field(default=ANSWER_CONTRACT_TYPE, init=False)

    def __post_init__(self) -> None:
        for name in ("answer_id", "question_reference", "primary_assessment_reference", "answer_text", "authority_reference", "version"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string")
            object.__setattr__(self, name, value.strip())
        for name in ("supporting_assessment_references", "evidence_references", "relationship_references"):
            value = getattr(self, name)
            if isinstance(value, (str, bytes, bytearray)):
                raise TypeError(f"{name} must be a sequence of strings")
            object.__setattr__(self, name, tuple(str(item).strip() for item in value))
        object.__setattr__(self, "answered_at", utc_timestamp(self.answered_at, "answered_at"))

    def validate(self) -> ValidationReport:
        issues: list[ValidationIssue] = []
        if not _valid_identity(self.answer_id, "answer"):
            issues.append(ValidationIssue("invalid_answer_identity", "answer_id must be dexter:answer:<uuid>", "$.answer_id"))
        if not self.question_reference:
            issues.append(ValidationIssue("missing_question_reference", "question_reference is required", "$.question_reference"))
        if not self.primary_assessment_reference:
            issues.append(ValidationIssue("missing_primary_assessment", "primary assessment is required", "$.primary_assessment_reference"))
        if (any(not item for item in self.supporting_assessment_references)
                or len(set(self.supporting_assessment_references)) != len(self.supporting_assessment_references)
                or self.primary_assessment_reference in self.supporting_assessment_references):
            issues.append(ValidationIssue("invalid_supporting_assessments", "supporting assessments must be non-empty, unique, and exclude the primary", "$.supporting_assessment_references"))
        if not self.answer_text:
            issues.append(ValidationIssue("missing_answer_text", "answer_text is required", "$.answer_text"))
        if not isinstance(self.confidence, AnswerConfidence) or self.confidence is AnswerConfidence.UNKNOWN:
            issues.append(ValidationIssue("invalid_confidence", "confidence must be recognized and cannot be UNKNOWN", "$.confidence"))
        if not self.authority_reference:
            issues.append(ValidationIssue("missing_authority_reference", "authority_reference is required", "$.authority_reference"))
        if not self.evidence_references or any(not item for item in self.evidence_references) or len(set(self.evidence_references)) != len(self.evidence_references):
            issues.append(ValidationIssue("invalid_evidence_references", "evidence references must be non-empty and unique", "$.evidence_references"))
        if any(not item for item in self.relationship_references) or len(set(self.relationship_references)) != len(self.relationship_references):
            issues.append(ValidationIssue("invalid_relationship_references", "relationship references must be non-empty and unique", "$.relationship_references"))
        _validate_revision_version(issues, self.revision, self.version, ANSWER_VERSION)
        return ValidationReport(tuple(issues))


def _valid_identity(value: str, kind: str) -> bool:
    prefix = f"dexter:{kind}:"
    if not isinstance(value, str) or not value.startswith(prefix):
        return False
    try:
        UUID(value.removeprefix(prefix))
    except ValueError:
        return False
    return True


def _validate_revision_version(issues: list[ValidationIssue], revision: int, version: str, expected: str) -> None:
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        issues.append(ValidationIssue("invalid_revision", "revision must be a positive integer", "$.revision"))
    if version != expected:
        issues.append(ValidationIssue("unsupported_version", f"expected {expected}", "$.version"))


def question_to_dict(value: Question) -> dict[str, Any]:
    return contract_to_dict(value)


def question_to_json(value: Question, *, indent: int | None = None) -> str:
    return contract_to_json(value, indent=indent)


def answer_to_dict(value: Answer) -> dict[str, Any]:
    return contract_to_dict(value)


def answer_to_json(value: Answer, *, indent: int | None = None) -> str:
    return contract_to_json(value, indent=indent)


def _strict_fields(data: Mapping[str, Any], fields: set[str]) -> None:
    unknown = set(data).difference(fields)
    if unknown:
        raise ValueError(f"unknown fields: {', '.join(sorted(unknown))}")
    missing = fields.difference(data)
    if missing:
        raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")


def _datetime(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a timestamp string")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO 8601 timestamp") from exc


def question_from_dict(data: Mapping[str, Any]) -> Question:
    fields = {"contract_type", "question_id", "question_type", "question_text", "asked_at", "authority_reference", "revision", "version"}
    _strict_fields(data, fields)
    if data["contract_type"] != QUESTION_CONTRACT_TYPE:
        raise ValueError(f"contract_type must be {QUESTION_CONTRACT_TYPE}")
    try:
        question_type = QuestionType(data["question_type"])
    except (TypeError, ValueError) as exc:
        raise ValueError("question_type is not a recognized QuestionType") from exc
    return Question(
        question_id=str(data["question_id"]), question_type=question_type,
        question_text=str(data["question_text"]), asked_at=_datetime(data["asked_at"], "asked_at"),
        authority_reference=str(data["authority_reference"]), revision=data["revision"],
        version=str(data["version"]),
    )


def answer_from_dict(data: Mapping[str, Any]) -> Answer:
    fields = {"contract_type", "answer_id", "question_reference", "primary_assessment_reference", "supporting_assessment_references", "answer_text", "confidence", "answered_at", "authority_reference", "evidence_references", "relationship_references", "revision", "version"}
    _strict_fields(data, fields)
    if data["contract_type"] != ANSWER_CONTRACT_TYPE:
        raise ValueError(f"contract_type must be {ANSWER_CONTRACT_TYPE}")
    try:
        confidence = AnswerConfidence(data["confidence"])
    except (TypeError, ValueError) as exc:
        raise ValueError("confidence is not a recognized AnswerConfidence") from exc
    sequences = ("supporting_assessment_references", "evidence_references", "relationship_references")
    if any(not isinstance(data[name], (list, tuple)) for name in sequences):
        raise ValueError("reference fields must be arrays")
    return Answer(
        answer_id=str(data["answer_id"]), question_reference=str(data["question_reference"]),
        primary_assessment_reference=str(data["primary_assessment_reference"]),
        supporting_assessment_references=tuple(str(item) for item in data["supporting_assessment_references"]),
        answer_text=str(data["answer_text"]), confidence=confidence,
        answered_at=_datetime(data["answered_at"], "answered_at"),
        authority_reference=str(data["authority_reference"]),
        evidence_references=tuple(str(item) for item in data["evidence_references"]),
        relationship_references=tuple(str(item) for item in data["relationship_references"]),
        revision=data["revision"], version=str(data["version"]),
    )


def question_from_json(payload: str | bytes | bytearray) -> Question:
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Question JSON must be an object")
    return question_from_dict(data)


def answer_from_json(payload: str | bytes | bytearray) -> Answer:
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Answer JSON must be an object")
    return answer_from_dict(data)
