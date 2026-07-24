"""Governed, explainable interpretations of evidence correlations."""
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

ASSESSMENT_CONTRACT_TYPE = "dexter.assessment"
ASSESSMENT_VERSION = "1.0"


class AssessmentType(StringEnum):
    RESOURCE_UTILIZATION = "RESOURCE_UTILIZATION"
    STATE_TRANSITION = "STATE_TRANSITION"
    CONFIGURATION_CHANGE = "CONFIGURATION_CHANGE"
    SERVICE_DEGRADATION = "SERVICE_DEGRADATION"
    CAPACITY = "CAPACITY"
    CONNECTIVITY = "CONNECTIVITY"
    UNKNOWN = "UNKNOWN"


class AssessmentConfidence(StringEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CERTAIN = "CERTAIN"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class Assessment:
    assessment_id: str
    assessment_type: AssessmentType
    primary_correlation_reference: str
    supporting_correlation_references: tuple[str, ...]
    assessment_statement: str
    assessment_basis: str
    confidence: AssessmentConfidence
    assessed_at: datetime
    authority_reference: str
    evidence_references: tuple[str, ...]
    relationship_references: tuple[str, ...] = ()
    revision: int = 1
    version: str = ASSESSMENT_VERSION
    contract_type: str = field(default=ASSESSMENT_CONTRACT_TYPE, init=False)

    def __post_init__(self) -> None:
        for name in ("assessment_id", "primary_correlation_reference", "assessment_statement", "assessment_basis", "authority_reference", "version"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string")
            object.__setattr__(self, name, value.strip())
        for name in ("supporting_correlation_references", "evidence_references", "relationship_references"):
            value = getattr(self, name)
            if isinstance(value, (str, bytes, bytearray)):
                raise TypeError(f"{name} must be a sequence of strings")
            object.__setattr__(self, name, tuple(str(item).strip() for item in value))
        object.__setattr__(self, "assessed_at", utc_timestamp(self.assessed_at, "assessed_at"))

    def validate(self) -> ValidationReport:
        issues: list[ValidationIssue] = []
        if not _valid_identity(self.assessment_id):
            issues.append(ValidationIssue("invalid_assessment_identity", "assessment_id must be dexter:assessment:<uuid>", "$.assessment_id"))
        if not isinstance(self.assessment_type, AssessmentType) or self.assessment_type is AssessmentType.UNKNOWN:
            issues.append(ValidationIssue("invalid_assessment_type", "assessment_type must be recognized and cannot be UNKNOWN", "$.assessment_type"))
        if not self.primary_correlation_reference:
            issues.append(ValidationIssue("missing_primary_correlation", "primary correlation is required", "$.primary_correlation_reference"))
        if not self.supporting_correlation_references:
            issues.append(ValidationIssue("missing_supporting_correlations", "at least one supporting correlation is required", "$.supporting_correlation_references"))
        if any(not item for item in self.supporting_correlation_references) or len(set(self.supporting_correlation_references)) != len(self.supporting_correlation_references) or self.primary_correlation_reference in self.supporting_correlation_references:
            issues.append(ValidationIssue("invalid_supporting_correlations", "supporting correlations must be non-empty, unique, and exclude the primary", "$.supporting_correlation_references"))
        if not self.assessment_statement:
            issues.append(ValidationIssue("missing_assessment_statement", "assessment statement is required", "$.assessment_statement"))
        if not self.assessment_basis:
            issues.append(ValidationIssue("missing_assessment_basis", "assessment basis is required", "$.assessment_basis"))
        if not isinstance(self.confidence, AssessmentConfidence) or self.confidence is AssessmentConfidence.UNKNOWN:
            issues.append(ValidationIssue("invalid_confidence", "confidence must be recognized and cannot be UNKNOWN", "$.confidence"))
        if not self.authority_reference:
            issues.append(ValidationIssue("missing_authority_reference", "authority_reference is required", "$.authority_reference"))
        if not self.evidence_references or any(not item for item in self.evidence_references) or len(set(self.evidence_references)) != len(self.evidence_references):
            issues.append(ValidationIssue("invalid_evidence_references", "evidence references must be non-empty and unique", "$.evidence_references"))
        if any(not item for item in self.relationship_references) or len(set(self.relationship_references)) != len(self.relationship_references):
            issues.append(ValidationIssue("invalid_relationship_references", "relationship references must be non-empty and unique", "$.relationship_references"))
        if not isinstance(self.revision, int) or isinstance(self.revision, bool) or self.revision < 1:
            issues.append(ValidationIssue("invalid_revision", "revision must be a positive integer", "$.revision"))
        if self.version != ASSESSMENT_VERSION:
            issues.append(ValidationIssue("unsupported_version", f"expected {ASSESSMENT_VERSION}", "$.version"))
        return ValidationReport(tuple(issues))


def _valid_identity(value: str) -> bool:
    prefix = "dexter:assessment:"
    if not isinstance(value, str) or not value.startswith(prefix):
        return False
    try:
        UUID(value.removeprefix(prefix))
    except ValueError:
        return False
    return True


def assessment_to_dict(value: Assessment) -> dict[str, Any]:
    return contract_to_dict(value)


def assessment_to_json(value: Assessment, *, indent: int | None = None) -> str:
    return contract_to_json(value, indent=indent)


def assessment_from_dict(data: Mapping[str, Any]) -> Assessment:
    fields = {"contract_type", "assessment_id", "assessment_type", "primary_correlation_reference", "supporting_correlation_references", "assessment_statement", "assessment_basis", "confidence", "assessed_at", "authority_reference", "evidence_references", "relationship_references", "revision", "version"}
    unknown = set(data).difference(fields)
    if unknown:
        raise ValueError(f"unknown fields: {', '.join(sorted(unknown))}")
    missing = fields.difference(data)
    if missing:
        raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")
    if data["contract_type"] != ASSESSMENT_CONTRACT_TYPE:
        raise ValueError(f"contract_type must be {ASSESSMENT_CONTRACT_TYPE}")
    try:
        assessment_type = AssessmentType(data["assessment_type"])
    except (TypeError, ValueError) as exc:
        raise ValueError("assessment_type is not a recognized AssessmentType") from exc
    try:
        confidence = AssessmentConfidence(data["confidence"])
    except (TypeError, ValueError) as exc:
        raise ValueError("confidence is not a recognized AssessmentConfidence") from exc
    sequence_fields = ("supporting_correlation_references", "evidence_references", "relationship_references")
    if any(not isinstance(data[name], (list, tuple)) for name in sequence_fields):
        raise ValueError("reference fields must be arrays")
    assessed_at = data["assessed_at"]
    if not isinstance(assessed_at, str):
        raise ValueError("assessed_at must be a timestamp string")
    try:
        timestamp = datetime.fromisoformat(assessed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("assessed_at must be an ISO 8601 timestamp") from exc
    return Assessment(
        assessment_id=str(data["assessment_id"]), assessment_type=assessment_type,
        primary_correlation_reference=str(data["primary_correlation_reference"]),
        supporting_correlation_references=tuple(str(item) for item in data["supporting_correlation_references"]),
        assessment_statement=str(data["assessment_statement"]), assessment_basis=str(data["assessment_basis"]),
        confidence=confidence, assessed_at=timestamp, authority_reference=str(data["authority_reference"]),
        evidence_references=tuple(str(item) for item in data["evidence_references"]),
        relationship_references=tuple(str(item) for item in data["relationship_references"]),
        revision=data["revision"], version=str(data["version"]),
    )


def assessment_from_json(payload: str | bytes | bytearray) -> Assessment:
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Assessment JSON must be an object")
    return assessment_from_dict(data)
