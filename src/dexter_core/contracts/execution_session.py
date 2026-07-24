"""Canonical, pure Execution Session contract."""
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

EXECUTION_SESSION_CONTRACT_TYPE = "dexter.execution_session"
EXECUTION_SESSION_VERSION = "1.0"

class ExecutionSessionState(StringEnum):
    CREATED = "CREATED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"

def _utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)

def _valid_identity(value: str) -> bool:
    prefix = "dexter:execution-session:"
    if not value.startswith(prefix): return False
    try: UUID(value.removeprefix(prefix))
    except ValueError: return False
    return True

@dataclass(frozen=True, slots=True)
class ExecutionSession:
    """Governed runtime context that owns execution state; never runtime behavior."""
    session_id: str
    execution_attempt_id: str
    provider_assignment_id: str
    lease_id: str
    worker_id: str
    provider_id: str
    state: ExecutionSessionState
    session_started_at: datetime
    authority_reference: str
    session_ended_at: datetime | None = None
    evidence_references: tuple[EvidenceReference, ...] = ()
    relationship_references: tuple[RelationshipReference, ...] = ()
    revision: int = 1
    version: str = EXECUTION_SESSION_VERSION
    contract_type: str = field(default=EXECUTION_SESSION_CONTRACT_TYPE, init=False)

    def __post_init__(self) -> None:
        for name in ("session_id", "execution_attempt_id", "provider_assignment_id", "lease_id", "worker_id", "provider_id", "authority_reference", "version"):
            value = getattr(self, name)
            if not isinstance(value, str): raise TypeError(f"{name} must be a string")
            object.__setattr__(self, name, value.strip())
        object.__setattr__(self, "session_started_at", _utc(self.session_started_at, "session_started_at"))
        if self.session_ended_at is not None:
            object.__setattr__(self, "session_ended_at", _utc(self.session_ended_at, "session_ended_at"))
        object.__setattr__(self, "evidence_references", tuple(self.evidence_references))
        object.__setattr__(self, "relationship_references", tuple(self.relationship_references))

    def validate(self) -> ValidationReport:
        issues: list[ValidationIssue] = []
        required = (("session_id", "missing_session_identity"), ("execution_attempt_id", "missing_execution_attempt_reference"), ("provider_assignment_id", "missing_provider_assignment_reference"), ("lease_id", "missing_lease_reference"), ("worker_id", "missing_worker_identity"), ("provider_id", "missing_provider_identity"), ("authority_reference", "missing_authority_reference"))
        for name, code in required:
            if not getattr(self, name): issues.append(ValidationIssue(code, f"{name} is required", f"$.{name}"))
        if self.session_id and not _valid_identity(self.session_id): issues.append(ValidationIssue("invalid_session_identity", "session_id must be dexter:execution-session:<uuid>", "$.session_id"))
        if not isinstance(self.state, ExecutionSessionState): issues.append(ValidationIssue("invalid_state", "state is not a recognized ExecutionSessionState", "$.state"))
        elif self.state is ExecutionSessionState.UNKNOWN: issues.append(ValidationIssue("unknown_state", "UNKNOWN cannot silently validate", "$.state"))
        if not isinstance(self.revision, int) or isinstance(self.revision, bool) or self.revision < 1: issues.append(ValidationIssue("invalid_revision", "revision must be a positive integer", "$.revision"))
        if self.version != EXECUTION_SESSION_VERSION: issues.append(ValidationIssue("unsupported_version", f"expected {EXECUTION_SESSION_VERSION}", "$.version"))
        if self.session_ended_at is not None and self.session_ended_at < self.session_started_at: issues.append(ValidationIssue("session_ended_before_started", "session_ended_at must not precede session_started_at", "$.session_ended_at"))
        return ValidationReport(tuple(issues))

def execution_session_to_dict(value: ExecutionSession) -> dict[str, Any]: return contract_to_dict(value)
def execution_session_to_json(value: ExecutionSession, *, indent: int | None = None) -> str: return contract_to_json(value, indent=indent)
def _datetime(value: Any, name: str) -> datetime:
    if not isinstance(value, str): raise ValueError(f"{name} must be a timestamp string")
    try: return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc: raise ValueError(f"{name} must be an ISO 8601 timestamp") from exc

def execution_session_from_dict(data: Mapping[str, Any]) -> ExecutionSession:
    fields = {"contract_type", "session_id", "execution_attempt_id", "provider_assignment_id", "lease_id", "worker_id", "provider_id", "state", "session_started_at", "session_ended_at", "authority_reference", "evidence_references", "relationship_references", "revision", "version"}
    unknown = set(data).difference(fields)
    if unknown: raise ValueError(f"unknown fields: {', '.join(sorted(unknown))}")
    missing = fields.difference({"session_ended_at", "evidence_references", "relationship_references"}).difference(data)
    if missing: raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")
    if data["contract_type"] != EXECUTION_SESSION_CONTRACT_TYPE: raise ValueError(f"contract_type must be {EXECUTION_SESSION_CONTRACT_TYPE}")
    evidence, relationships = data.get("evidence_references", ()), data.get("relationship_references", ())
    if not isinstance(evidence, (list, tuple)) or not isinstance(relationships, (list, tuple)): raise ValueError("reference fields must be arrays")
    try: state = ExecutionSessionState(data["state"])
    except (TypeError, ValueError) as exc: raise ValueError("state is not a recognized ExecutionSessionState") from exc
    ended = data.get("session_ended_at")
    return ExecutionSession(session_id=str(data["session_id"]), execution_attempt_id=str(data["execution_attempt_id"]), provider_assignment_id=str(data["provider_assignment_id"]), lease_id=str(data["lease_id"]), worker_id=str(data["worker_id"]), provider_id=str(data["provider_id"]), state=state, session_started_at=_datetime(data["session_started_at"], "session_started_at"), authority_reference=str(data["authority_reference"]), session_ended_at=None if ended is None else _datetime(ended, "session_ended_at"), evidence_references=tuple(EvidenceReference(uri=str(x["uri"]), media_type=str(x["media_type"]), description=x.get("description"), digest=x.get("digest")) for x in evidence), relationship_references=tuple(RelationshipReference(target_entity_id=str(x["target_entity_id"]), kind=RelationshipKind(x["kind"]), attributes=x.get("attributes")) for x in relationships), revision=data["revision"], version=str(data["version"]))

def execution_session_from_json(payload: str | bytes | bytearray) -> ExecutionSession:
    data = json.loads(payload)
    if not isinstance(data, dict): raise ValueError("Execution Session JSON must be an object")
    return execution_session_from_dict(data)
