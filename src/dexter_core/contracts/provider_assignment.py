"""Canonical, pure Provider Assignment contract."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import UUID
from ..enums import RelationshipKind, StringEnum
from ..references import EvidenceReference, RelationshipReference
from ..serialization import contract_to_dict, contract_to_json
from ..validation import ValidationIssue, ValidationReport

PROVIDER_ASSIGNMENT_CONTRACT_TYPE = "dexter.provider_assignment"
PROVIDER_ASSIGNMENT_VERSION = "1.0"

class ProviderAssignmentState(StringEnum):
    ASSIGNED = "ASSIGNED"
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    COMPLETED = "COMPLETED"
    UNKNOWN = "UNKNOWN"

def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("assigned_at must be timezone-aware")
    return value.astimezone(timezone.utc)

def _valid_identity(value: str) -> bool:
    prefix = "dexter:provider-assignment:"
    if not value.startswith(prefix): return False
    try: UUID(value.removeprefix(prefix))
    except ValueError: return False
    return True

@dataclass(frozen=True, slots=True)
class ProviderAssignment:
    """Governed authorization for a provider to satisfy a Lease."""
    assignment_id: str
    lease_id: str
    worker_id: str
    provider_id: str
    provider_capability: str
    state: ProviderAssignmentState
    assigned_at: datetime
    authority_reference: str
    evidence_references: tuple[EvidenceReference, ...] = ()
    relationship_references: tuple[RelationshipReference, ...] = ()
    revision: int = 1
    version: str = PROVIDER_ASSIGNMENT_VERSION
    contract_type: str = field(default=PROVIDER_ASSIGNMENT_CONTRACT_TYPE, init=False)

    def __post_init__(self) -> None:
        for name in ("assignment_id", "lease_id", "worker_id", "provider_id", "provider_capability", "authority_reference", "version"):
            value = getattr(self, name)
            if not isinstance(value, str): raise TypeError(f"{name} must be a string")
            object.__setattr__(self, name, value.strip())
        object.__setattr__(self, "assigned_at", _utc(self.assigned_at))
        object.__setattr__(self, "evidence_references", tuple(self.evidence_references))
        object.__setattr__(self, "relationship_references", tuple(self.relationship_references))

    def validate(self) -> ValidationReport:
        issues: list[ValidationIssue] = []
        required = (("assignment_id", "missing_assignment_identity"), ("lease_id", "missing_lease_reference"), ("worker_id", "missing_worker_identity"), ("provider_id", "missing_provider_identity"), ("provider_capability", "missing_provider_capability"), ("authority_reference", "missing_authority_reference"))
        for name, code in required:
            if not getattr(self, name): issues.append(ValidationIssue(code, f"{name} is required", f"$.{name}"))
        if self.assignment_id and not _valid_identity(self.assignment_id): issues.append(ValidationIssue("invalid_assignment_identity", "assignment_id must be dexter:provider-assignment:<uuid>", "$.assignment_id"))
        if not isinstance(self.state, ProviderAssignmentState): issues.append(ValidationIssue("invalid_state", "state is not a recognized ProviderAssignmentState", "$.state"))
        elif self.state is ProviderAssignmentState.UNKNOWN: issues.append(ValidationIssue("unknown_state", "UNKNOWN cannot silently validate", "$.state"))
        if not isinstance(self.revision, int) or isinstance(self.revision, bool) or self.revision < 1: issues.append(ValidationIssue("invalid_revision", "revision must be a positive integer", "$.revision"))
        if self.version != PROVIDER_ASSIGNMENT_VERSION: issues.append(ValidationIssue("unsupported_version", f"expected {PROVIDER_ASSIGNMENT_VERSION}", "$.version"))
        return ValidationReport(tuple(issues))

def provider_assignment_to_dict(value: ProviderAssignment) -> dict[str, Any]: return contract_to_dict(value)
def provider_assignment_to_json(value: ProviderAssignment, *, indent: int | None = None) -> str: return contract_to_json(value, indent=indent)
def _datetime(value: Any) -> datetime:
    if not isinstance(value, str): raise ValueError("assigned_at must be a timestamp string")
    try: return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc: raise ValueError("assigned_at must be an ISO 8601 timestamp") from exc

def provider_assignment_from_dict(data: Mapping[str, Any]) -> ProviderAssignment:
    fields = {"contract_type", "assignment_id", "lease_id", "worker_id", "provider_id", "provider_capability", "state", "assigned_at", "authority_reference", "evidence_references", "relationship_references", "revision", "version"}
    unknown = set(data).difference(fields)
    if unknown: raise ValueError(f"unknown fields: {', '.join(sorted(unknown))}")
    missing = fields.difference({"evidence_references", "relationship_references"}).difference(data)
    if missing: raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")
    if data["contract_type"] != PROVIDER_ASSIGNMENT_CONTRACT_TYPE: raise ValueError(f"contract_type must be {PROVIDER_ASSIGNMENT_CONTRACT_TYPE}")
    evidence, relationships = data.get("evidence_references", ()), data.get("relationship_references", ())
    if not isinstance(evidence, (list, tuple)) or not isinstance(relationships, (list, tuple)): raise ValueError("reference fields must be arrays")
    try: state = ProviderAssignmentState(data["state"])
    except (TypeError, ValueError) as exc: raise ValueError("state is not a recognized ProviderAssignmentState") from exc
    return ProviderAssignment(assignment_id=str(data["assignment_id"]), lease_id=str(data["lease_id"]), worker_id=str(data["worker_id"]), provider_id=str(data["provider_id"]), provider_capability=str(data["provider_capability"]), state=state, assigned_at=_datetime(data["assigned_at"]), authority_reference=str(data["authority_reference"]), evidence_references=tuple(EvidenceReference(uri=str(x["uri"]), media_type=str(x["media_type"]), description=x.get("description"), digest=x.get("digest")) for x in evidence), relationship_references=tuple(RelationshipReference(target_entity_id=str(x["target_entity_id"]), kind=RelationshipKind(x["kind"]), attributes=x.get("attributes")) for x in relationships), revision=data["revision"], version=str(data["version"]))

def provider_assignment_from_json(payload: str | bytes | bytearray) -> ProviderAssignment:
    data = json.loads(payload)
    if not isinstance(data, dict): raise ValueError("Provider Assignment JSON must be an object")
    return provider_assignment_from_dict(data)
