"""Canonical, pure Runtime Event contract."""
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

RUNTIME_EVENT_CONTRACT_TYPE = "dexter.runtime_event"
RUNTIME_EVENT_VERSION = "1.0"

class RuntimeEventType(StringEnum):
    STARTED = "STARTED"
    HEARTBEAT = "HEARTBEAT"
    PROGRESS = "PROGRESS"
    WARNING = "WARNING"
    PAUSED = "PAUSED"
    RESUMED = "RESUMED"
    STDOUT = "STDOUT"
    STDERR = "STDERR"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"

def _utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)

def _valid_identity(value: str) -> bool:
    prefix = "dexter:runtime-event:"
    if not value.startswith(prefix): return False
    try: UUID(value.removeprefix(prefix))
    except ValueError: return False
    return True

@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    """Immutable observation from an Execution Session; never runtime behavior."""
    event_id: str
    execution_session_id: str
    execution_attempt_id: str
    provider_assignment_id: str
    lease_id: str
    worker_id: str
    provider_id: str
    event_type: RuntimeEventType
    observed_at: datetime
    authority_reference: str
    evidence_references: tuple[EvidenceReference, ...] = ()
    relationship_references: tuple[RelationshipReference, ...] = ()
    revision: int = 1
    version: str = RUNTIME_EVENT_VERSION
    contract_type: str = field(default=RUNTIME_EVENT_CONTRACT_TYPE, init=False)

    def __post_init__(self) -> None:
        for name in ("event_id", "execution_session_id", "execution_attempt_id", "provider_assignment_id", "lease_id", "worker_id", "provider_id", "authority_reference", "version"):
            value = getattr(self, name)
            if not isinstance(value, str): raise TypeError(f"{name} must be a string")
            object.__setattr__(self, name, value.strip())
        object.__setattr__(self, "observed_at", _utc(self.observed_at, "observed_at"))
        object.__setattr__(self, "evidence_references", tuple(self.evidence_references))
        object.__setattr__(self, "relationship_references", tuple(self.relationship_references))

    def validate(self) -> ValidationReport:
        issues: list[ValidationIssue] = []
        required = (("event_id", "missing_event_identity"), ("execution_session_id", "missing_execution_session_reference"), ("execution_attempt_id", "missing_execution_attempt_reference"), ("provider_assignment_id", "missing_provider_assignment_reference"), ("lease_id", "missing_lease_reference"), ("worker_id", "missing_worker_identity"), ("provider_id", "missing_provider_identity"), ("authority_reference", "missing_authority_reference"))
        for name, code in required:
            if not getattr(self, name): issues.append(ValidationIssue(code, f"{name} is required", f"$.{name}"))
        if self.event_id and not _valid_identity(self.event_id): issues.append(ValidationIssue("invalid_event_identity", "event_id must be dexter:runtime-event:<uuid>", "$.event_id"))
        if not isinstance(self.event_type, RuntimeEventType): issues.append(ValidationIssue("invalid_event_type", "event_type is not a recognized RuntimeEventType", "$.event_type"))
        elif self.event_type is RuntimeEventType.UNKNOWN: issues.append(ValidationIssue("unknown_event_type", "UNKNOWN cannot silently validate", "$.event_type"))
        if not isinstance(self.revision, int) or isinstance(self.revision, bool) or self.revision < 1: issues.append(ValidationIssue("invalid_revision", "revision must be a positive integer", "$.revision"))
        if self.version != RUNTIME_EVENT_VERSION: issues.append(ValidationIssue("unsupported_version", f"expected {RUNTIME_EVENT_VERSION}", "$.version"))
        return ValidationReport(tuple(issues))

def runtime_event_to_dict(value: RuntimeEvent) -> dict[str, Any]: return contract_to_dict(value)
def runtime_event_to_json(value: RuntimeEvent, *, indent: int | None = None) -> str: return contract_to_json(value, indent=indent)
def _datetime(value: Any, name: str) -> datetime:
    if not isinstance(value, str): raise ValueError(f"{name} must be a timestamp string")
    try: return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc: raise ValueError(f"{name} must be an ISO 8601 timestamp") from exc

def runtime_event_from_dict(data: Mapping[str, Any]) -> RuntimeEvent:
    fields = {"contract_type", "event_id", "execution_session_id", "execution_attempt_id", "provider_assignment_id", "lease_id", "worker_id", "provider_id", "event_type", "observed_at", "authority_reference", "evidence_references", "relationship_references", "revision", "version"}
    unknown = set(data).difference(fields)
    if unknown: raise ValueError(f"unknown fields: {', '.join(sorted(unknown))}")
    missing = fields.difference({"evidence_references", "relationship_references"}).difference(data)
    if missing: raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")
    if data["contract_type"] != RUNTIME_EVENT_CONTRACT_TYPE: raise ValueError(f"contract_type must be {RUNTIME_EVENT_CONTRACT_TYPE}")
    evidence, relationships = data.get("evidence_references", ()), data.get("relationship_references", ())
    if not isinstance(evidence, (list, tuple)) or not isinstance(relationships, (list, tuple)): raise ValueError("reference fields must be arrays")
    try: event_type = RuntimeEventType(data["event_type"])
    except (TypeError, ValueError) as exc: raise ValueError("event_type is not a recognized RuntimeEventType") from exc
    return RuntimeEvent(event_id=str(data["event_id"]), execution_session_id=str(data["execution_session_id"]), execution_attempt_id=str(data["execution_attempt_id"]), provider_assignment_id=str(data["provider_assignment_id"]), lease_id=str(data["lease_id"]), worker_id=str(data["worker_id"]), provider_id=str(data["provider_id"]), event_type=event_type, observed_at=_datetime(data["observed_at"], "observed_at"), authority_reference=str(data["authority_reference"]), evidence_references=tuple(EvidenceReference(uri=str(x["uri"]), media_type=str(x["media_type"]), description=x.get("description"), digest=x.get("digest")) for x in evidence), relationship_references=tuple(RelationshipReference(target_entity_id=str(x["target_entity_id"]), kind=RelationshipKind(x["kind"]), attributes=x.get("attributes")) for x in relationships), revision=data["revision"], version=str(data["version"]))

def runtime_event_from_json(payload: str | bytes | bytearray) -> RuntimeEvent:
    data = json.loads(payload)
    if not isinstance(data, dict): raise ValueError("Runtime Event JSON must be an object")
    return runtime_event_from_dict(data)
