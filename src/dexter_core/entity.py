from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID, uuid4

from .enums import LifecycleState, OperationalStatus
from .references import Authority, EvidenceReference, ProvenanceReference, RelationshipReference
from .validation import ValidationIssue, ValidationReport, ValidationRule, Validator

CURRENT_SCHEMA_VERSION = "1.0"


def new_entity_id() -> str:
    """Return a globally unique, stable entity identifier."""
    return f"dexter:{uuid4()}"


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class GovernedEntity:
    """The versioned contract shared by governed Dexter resources."""

    entity_type: str
    name: str
    authority: Authority
    entity_id: str = field(default_factory=new_entity_id)
    lifecycle_state: LifecycleState = LifecycleState.DRAFT
    operational_status: OperationalStatus = OperationalStatus.UNKNOWN
    provenance: tuple[ProvenanceReference, ...] = ()
    evidence: tuple[EvidenceReference, ...] = ()
    relationships: tuple[RelationshipReference, ...] = ()
    attributes: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = CURRENT_SCHEMA_VERSION
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        for field_name in ("entity_id", "entity_type", "name", "schema_version"):
            value = getattr(self, field_name)
            if not value or not value.strip():
                raise ValueError(f"{field_name} must not be empty")
            object.__setattr__(self, field_name, value.strip())
        if not self.entity_id.startswith("dexter:"):
            raise ValueError("entity_id must use the 'dexter:' namespace")
        try:
            UUID(self.entity_id.removeprefix("dexter:"))
        except ValueError as exc:
            raise ValueError("entity_id must contain a valid UUID") from exc
        object.__setattr__(self, "created_at", _utc(self.created_at, "created_at"))
        object.__setattr__(self, "updated_at", _utc(self.updated_at, "updated_at"))
        object.__setattr__(self, "provenance", tuple(self.provenance))
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "relationships", tuple(self.relationships))
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))

    def validate(self, *rules: ValidationRule) -> ValidationReport:
        issues: list[ValidationIssue] = []
        if self.schema_version != CURRENT_SCHEMA_VERSION:
            issues.append(ValidationIssue("unsupported_schema_version", f"expected {CURRENT_SCHEMA_VERSION}", "$.schema_version"))
        if self.updated_at < self.created_at:
            issues.append(ValidationIssue("invalid_timestamp_order", "updated_at precedes created_at", "$.updated_at"))
        if self.lifecycle_state is LifecycleState.ACTIVE and not self.provenance:
            issues.append(ValidationIssue("missing_provenance", "active entities require provenance", "$.provenance"))
        if any(item.target_entity_id == self.entity_id for item in self.relationships):
            issues.append(ValidationIssue("self_relationship", "entity cannot relate to itself", "$.relationships"))
        custom = Validator(rules).validate(self)
        return ValidationReport(tuple(issues) + custom.issues)

