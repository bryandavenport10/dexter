"""Governed, deterministic relationships between pieces of evidence."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from math import isfinite
from typing import Any, Mapping
from uuid import UUID

from ..enums import StringEnum
from ..serialization import contract_to_dict, contract_to_json
from ..validation import ValidationIssue, ValidationReport
from .observation import utc_timestamp

EVIDENCE_CORRELATION_CONTRACT_TYPE = "dexter.evidence_correlation"
EVIDENCE_CORRELATION_VERSION = "1.0"


class CorrelationType(StringEnum):
    SAME_SOURCE_OBJECT = "SAME_SOURCE_OBJECT"
    TEMPORAL_PROXIMITY = "TEMPORAL_PROXIMITY"
    STATE_CHANGE = "STATE_CHANGE"
    SUPPORTED_BY = "SUPPORTED_BY"
    CONTRADICTED_BY = "CONTRADICTED_BY"
    RELATED_RESOURCE = "RELATED_RESOURCE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class EvidenceCorrelation:
    correlation_id: str
    correlation_type: CorrelationType
    primary_evidence_reference: str
    related_evidence_references: tuple[str, ...]
    correlation_basis: str
    confidence: float
    correlated_at: datetime
    authority_reference: str
    evidence_references: tuple[str, ...]
    relationship_references: tuple[str, ...] = ()
    revision: int = 1
    version: str = EVIDENCE_CORRELATION_VERSION
    contract_type: str = field(default=EVIDENCE_CORRELATION_CONTRACT_TYPE, init=False)

    def __post_init__(self) -> None:
        for name in ("correlation_id", "primary_evidence_reference", "correlation_basis", "authority_reference", "version"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string")
            object.__setattr__(self, name, value.strip())
        for name in ("related_evidence_references", "evidence_references", "relationship_references"):
            value = getattr(self, name)
            if isinstance(value, (str, bytes, bytearray)):
                raise TypeError(f"{name} must be a sequence of strings")
            object.__setattr__(self, name, tuple(str(item).strip() for item in value))
        if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
            raise TypeError("confidence must be a number")
        object.__setattr__(self, "confidence", float(self.confidence))
        object.__setattr__(self, "correlated_at", utc_timestamp(self.correlated_at, "correlated_at"))

    def validate(self) -> ValidationReport:
        issues: list[ValidationIssue] = []
        if not _valid_identity(self.correlation_id):
            issues.append(ValidationIssue("invalid_correlation_identity", "correlation_id must be dexter:correlation:<uuid>", "$.correlation_id"))
        if not isinstance(self.correlation_type, CorrelationType) or self.correlation_type is CorrelationType.UNKNOWN:
            issues.append(ValidationIssue("invalid_correlation_type", "correlation_type must be recognized and cannot be UNKNOWN", "$.correlation_type"))
        if not self.primary_evidence_reference:
            issues.append(ValidationIssue("missing_primary_evidence", "primary evidence is required", "$.primary_evidence_reference"))
        if not self.related_evidence_references:
            issues.append(ValidationIssue("missing_related_evidence", "at least one related evidence reference is required", "$.related_evidence_references"))
        if len(set(self.related_evidence_references)) != len(self.related_evidence_references):
            issues.append(ValidationIssue("duplicate_evidence", "related evidence references cannot contain duplicates", "$.related_evidence_references"))
        if self.primary_evidence_reference in self.related_evidence_references:
            issues.append(ValidationIssue("primary_evidence_repeated", "primary evidence cannot appear in related evidence", "$.related_evidence_references"))
        expected = (self.primary_evidence_reference, *self.related_evidence_references)
        if self.evidence_references != expected or len(set(self.evidence_references)) != len(self.evidence_references):
            issues.append(ValidationIssue("invalid_evidence_references", "evidence_references must contain primary then related evidence exactly once", "$.evidence_references"))
        if not self.correlation_basis:
            issues.append(ValidationIssue("missing_correlation_basis", "correlation_basis is required", "$.correlation_basis"))
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            issues.append(ValidationIssue("invalid_confidence", "confidence must be finite and between 0.0 and 1.0", "$.confidence"))
        if not self.authority_reference:
            issues.append(ValidationIssue("missing_authority_reference", "authority_reference is required", "$.authority_reference"))
        if any(not item for item in self.relationship_references) or len(set(self.relationship_references)) != len(self.relationship_references):
            issues.append(ValidationIssue("invalid_relationship_references", "relationship references must be non-empty and unique", "$.relationship_references"))
        if not isinstance(self.revision, int) or isinstance(self.revision, bool) or self.revision < 1:
            issues.append(ValidationIssue("invalid_revision", "revision must be a positive integer", "$.revision"))
        if self.version != EVIDENCE_CORRELATION_VERSION:
            issues.append(ValidationIssue("unsupported_version", f"expected {EVIDENCE_CORRELATION_VERSION}", "$.version"))
        return ValidationReport(tuple(issues))


def _valid_identity(value: str) -> bool:
    prefix = "dexter:correlation:"
    if not isinstance(value, str) or not value.startswith(prefix):
        return False
    try:
        UUID(value.removeprefix(prefix))
    except ValueError:
        return False
    return True


def evidence_correlation_to_dict(value: EvidenceCorrelation) -> dict[str, Any]:
    return contract_to_dict(value)


def evidence_correlation_to_json(value: EvidenceCorrelation, *, indent: int | None = None) -> str:
    return contract_to_json(value, indent=indent)


def _datetime(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a timestamp string")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO 8601 timestamp") from exc


def evidence_correlation_from_dict(data: Mapping[str, Any]) -> EvidenceCorrelation:
    fields = {
        "contract_type", "correlation_id", "correlation_type", "primary_evidence_reference",
        "related_evidence_references", "correlation_basis", "confidence", "correlated_at",
        "authority_reference", "evidence_references", "relationship_references", "revision", "version",
    }
    unknown = set(data).difference(fields)
    if unknown:
        raise ValueError(f"unknown fields: {', '.join(sorted(unknown))}")
    missing = fields.difference(data)
    if missing:
        raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")
    if data["contract_type"] != EVIDENCE_CORRELATION_CONTRACT_TYPE:
        raise ValueError(f"contract_type must be {EVIDENCE_CORRELATION_CONTRACT_TYPE}")
    try:
        correlation_type = CorrelationType(data["correlation_type"])
    except (TypeError, ValueError) as exc:
        raise ValueError("correlation_type is not a recognized CorrelationType") from exc
    sequence_fields = ("related_evidence_references", "evidence_references", "relationship_references")
    if any(not isinstance(data[name], (list, tuple)) for name in sequence_fields):
        raise ValueError("reference fields must be arrays")
    return EvidenceCorrelation(
        correlation_id=str(data["correlation_id"]), correlation_type=correlation_type,
        primary_evidence_reference=str(data["primary_evidence_reference"]),
        related_evidence_references=tuple(str(item) for item in data["related_evidence_references"]),
        correlation_basis=str(data["correlation_basis"]), confidence=data["confidence"],
        correlated_at=_datetime(data["correlated_at"], "correlated_at"),
        authority_reference=str(data["authority_reference"]),
        evidence_references=tuple(str(item) for item in data["evidence_references"]),
        relationship_references=tuple(str(item) for item in data["relationship_references"]),
        revision=data["revision"], version=str(data["version"]),
    )


def evidence_correlation_from_json(payload: str | bytes | bytearray) -> EvidenceCorrelation:
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("EvidenceCorrelation JSON must be an object")
    return evidence_correlation_from_dict(data)
