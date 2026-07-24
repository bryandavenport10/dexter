"""Canonical, pure Execution Attempt contract."""
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

EXECUTION_ATTEMPT_CONTRACT_TYPE = "dexter.execution_attempt"
EXECUTION_ATTEMPT_VERSION = "1.0"

class ExecutionAttemptState(StringEnum):
    CREATED = "CREATED"
    AUTHORIZED = "AUTHORIZED"
    START_REQUESTED = "START_REQUESTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"

def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("attempt_timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)

def _valid_identity(value: str) -> bool:
    prefix = "dexter:execution-attempt:"
    if not value.startswith(prefix): return False
    try: UUID(value.removeprefix(prefix))
    except ValueError: return False
    return True

@dataclass(frozen=True, slots=True)
class ExecutionAttempt:
    """Governed intent and authorization to request execution; never execution."""
    attempt_id: str
    provider_assignment_id: str
    lease_id: str
    worker_id: str
    provider_id: str
    state: ExecutionAttemptState
    attempt_timestamp: datetime
    authority_reference: str
    evidence_references: tuple[EvidenceReference, ...] = ()
    relationship_references: tuple[RelationshipReference, ...] = ()
    revision: int = 1
    version: str = EXECUTION_ATTEMPT_VERSION
    contract_type: str = field(default=EXECUTION_ATTEMPT_CONTRACT_TYPE, init=False)

    def __post_init__(self) -> None:
        for name in ("attempt_id", "provider_assignment_id", "lease_id", "worker_id", "provider_id", "authority_reference", "version"):
            value = getattr(self, name)
            if not isinstance(value, str): raise TypeError(f"{name} must be a string")
            object.__setattr__(self, name, value.strip())
        object.__setattr__(self, "attempt_timestamp", _utc(self.attempt_timestamp))
        object.__setattr__(self, "evidence_references", tuple(self.evidence_references))
        object.__setattr__(self, "relationship_references", tuple(self.relationship_references))

    def validate(self) -> ValidationReport:
        issues: list[ValidationIssue] = []
        required = (("attempt_id", "missing_attempt_identity"), ("provider_assignment_id", "missing_provider_assignment_reference"), ("lease_id", "missing_lease_reference"), ("worker_id", "missing_worker_identity"), ("provider_id", "missing_provider_identity"), ("authority_reference", "missing_authority_reference"))
        for name, code in required:
            if not getattr(self, name): issues.append(ValidationIssue(code, f"{name} is required", f"$.{name}"))
        if self.attempt_id and not _valid_identity(self.attempt_id): issues.append(ValidationIssue("invalid_attempt_identity", "attempt_id must be dexter:execution-attempt:<uuid>", "$.attempt_id"))
        if not isinstance(self.state, ExecutionAttemptState): issues.append(ValidationIssue("invalid_state", "state is not a recognized ExecutionAttemptState", "$.state"))
        elif self.state is ExecutionAttemptState.UNKNOWN: issues.append(ValidationIssue("unknown_state", "UNKNOWN cannot silently validate", "$.state"))
        if not isinstance(self.revision, int) or isinstance(self.revision, bool) or self.revision < 1: issues.append(ValidationIssue("invalid_revision", "revision must be a positive integer", "$.revision"))
        if self.version != EXECUTION_ATTEMPT_VERSION: issues.append(ValidationIssue("unsupported_version", f"expected {EXECUTION_ATTEMPT_VERSION}", "$.version"))
        return ValidationReport(tuple(issues))

def execution_attempt_to_dict(value: ExecutionAttempt) -> dict[str, Any]: return contract_to_dict(value)
def execution_attempt_to_json(value: ExecutionAttempt, *, indent: int | None = None) -> str: return contract_to_json(value, indent=indent)
def _datetime(value: Any) -> datetime:
    if not isinstance(value, str): raise ValueError("attempt_timestamp must be a timestamp string")
    try: return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc: raise ValueError("attempt_timestamp must be an ISO 8601 timestamp") from exc

def execution_attempt_from_dict(data: Mapping[str, Any]) -> ExecutionAttempt:
    fields = {"contract_type", "attempt_id", "provider_assignment_id", "lease_id", "worker_id", "provider_id", "state", "attempt_timestamp", "authority_reference", "evidence_references", "relationship_references", "revision", "version"}
    unknown = set(data).difference(fields)
    if unknown: raise ValueError(f"unknown fields: {', '.join(sorted(unknown))}")
    missing = fields.difference({"evidence_references", "relationship_references"}).difference(data)
    if missing: raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")
    if data["contract_type"] != EXECUTION_ATTEMPT_CONTRACT_TYPE: raise ValueError(f"contract_type must be {EXECUTION_ATTEMPT_CONTRACT_TYPE}")
    evidence, relationships = data.get("evidence_references", ()), data.get("relationship_references", ())
    if not isinstance(evidence, (list, tuple)) or not isinstance(relationships, (list, tuple)): raise ValueError("reference fields must be arrays")
    try: state = ExecutionAttemptState(data["state"])
    except (TypeError, ValueError) as exc: raise ValueError("state is not a recognized ExecutionAttemptState") from exc
    return ExecutionAttempt(attempt_id=str(data["attempt_id"]), provider_assignment_id=str(data["provider_assignment_id"]), lease_id=str(data["lease_id"]), worker_id=str(data["worker_id"]), provider_id=str(data["provider_id"]), state=state, attempt_timestamp=_datetime(data["attempt_timestamp"]), authority_reference=str(data["authority_reference"]), evidence_references=tuple(EvidenceReference(uri=str(x["uri"]), media_type=str(x["media_type"]), description=x.get("description"), digest=x.get("digest")) for x in evidence), relationship_references=tuple(RelationshipReference(target_entity_id=str(x["target_entity_id"]), kind=RelationshipKind(x["kind"]), attributes=x.get("attributes")) for x in relationships), revision=data["revision"], version=str(data["version"]))

def execution_attempt_from_json(payload: str | bytes | bytearray) -> ExecutionAttempt:
    data = json.loads(payload)
    if not isinstance(data, dict): raise ValueError("Execution Attempt JSON must be an object")
    return execution_attempt_from_dict(data)
