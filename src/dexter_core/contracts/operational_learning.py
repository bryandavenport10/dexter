"""Canonical, passive Operational Learning contract."""
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

OPERATIONAL_LEARNING_RECORD_CONTRACT_TYPE = "dexter.operational_learning_record"
OPERATIONAL_LEARNING_RECORD_VERSION = "1.0"

class LearningDisposition(StringEnum):
    LEARNED = "LEARNED"
    NO_CHANGE = "NO_CHANGE"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"

def _utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None: raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)

def _valid_identity(value: str) -> bool:
    prefix = "dexter:operational-learning:"
    if not value.startswith(prefix): return False
    try: UUID(value.removeprefix(prefix))
    except ValueError: return False
    return True

@dataclass(frozen=True, slots=True)
class OperationalLearningRecord:
    """Governed learning derived from a completed, verified outcome."""
    learning_id: str
    outcome_record_id: str
    execution_verification_id: str
    execution_session_id: str
    execution_attempt_id: str
    provider_assignment_id: str
    lease_id: str
    worker_id: str
    provider_id: str
    disposition: LearningDisposition
    recorded_at: datetime
    authority_reference: str
    evidence_references: tuple[EvidenceReference, ...] = ()
    relationship_references: tuple[RelationshipReference, ...] = ()
    revision: int = 1
    version: str = OPERATIONAL_LEARNING_RECORD_VERSION
    contract_type: str = field(default=OPERATIONAL_LEARNING_RECORD_CONTRACT_TYPE, init=False)

    def __post_init__(self) -> None:
        for name in ("learning_id", "outcome_record_id", "execution_verification_id", "execution_session_id", "execution_attempt_id", "provider_assignment_id", "lease_id", "worker_id", "provider_id", "authority_reference", "version"):
            value = getattr(self, name)
            if not isinstance(value, str): raise TypeError(f"{name} must be a string")
            object.__setattr__(self, name, value.strip())
        object.__setattr__(self, "recorded_at", _utc(self.recorded_at, "recorded_at"))
        object.__setattr__(self, "evidence_references", tuple(self.evidence_references))
        object.__setattr__(self, "relationship_references", tuple(self.relationship_references))

    def validate(self) -> ValidationReport:
        issues: list[ValidationIssue] = []
        required = (("learning_id", "missing_learning_identity"), ("outcome_record_id", "missing_outcome_record_reference"), ("execution_verification_id", "missing_execution_verification_reference"), ("execution_session_id", "missing_execution_session_reference"), ("execution_attempt_id", "missing_execution_attempt_reference"), ("provider_assignment_id", "missing_provider_assignment_reference"), ("lease_id", "missing_lease_reference"), ("worker_id", "missing_worker_identity"), ("provider_id", "missing_provider_identity"), ("authority_reference", "missing_authority_reference"))
        for name, code in required:
            if not getattr(self, name): issues.append(ValidationIssue(code, f"{name} is required", f"$.{name}"))
        if self.learning_id and not _valid_identity(self.learning_id): issues.append(ValidationIssue("invalid_learning_identity", "learning_id must be dexter:operational-learning:<uuid>", "$.learning_id"))
        if not isinstance(self.disposition, LearningDisposition): issues.append(ValidationIssue("invalid_learning_disposition", "disposition is not a recognized LearningDisposition", "$.disposition"))
        elif self.disposition is LearningDisposition.UNKNOWN: issues.append(ValidationIssue("unknown_learning_disposition", "UNKNOWN cannot silently validate", "$.disposition"))
        if not isinstance(self.revision, int) or isinstance(self.revision, bool) or self.revision < 1: issues.append(ValidationIssue("invalid_revision", "revision must be a positive integer", "$.revision"))
        if self.version != OPERATIONAL_LEARNING_RECORD_VERSION: issues.append(ValidationIssue("unsupported_version", f"expected {OPERATIONAL_LEARNING_RECORD_VERSION}", "$.version"))
        return ValidationReport(tuple(issues))

def operational_learning_record_to_dict(value: OperationalLearningRecord) -> dict[str, Any]: return contract_to_dict(value)
def operational_learning_record_to_json(value: OperationalLearningRecord, *, indent: int | None = None) -> str: return contract_to_json(value, indent=indent)
def _datetime(value: Any, name: str) -> datetime:
    if not isinstance(value, str): raise ValueError(f"{name} must be a timestamp string")
    try: return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc: raise ValueError(f"{name} must be an ISO 8601 timestamp") from exc

def operational_learning_record_from_dict(data: Mapping[str, Any]) -> OperationalLearningRecord:
    fields = {"contract_type", "learning_id", "outcome_record_id", "execution_verification_id", "execution_session_id", "execution_attempt_id", "provider_assignment_id", "lease_id", "worker_id", "provider_id", "disposition", "recorded_at", "authority_reference", "evidence_references", "relationship_references", "revision", "version"}
    unknown = set(data).difference(fields)
    if unknown: raise ValueError(f"unknown fields: {', '.join(sorted(unknown))}")
    missing = fields.difference({"evidence_references", "relationship_references"}).difference(data)
    if missing: raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")
    if data["contract_type"] != OPERATIONAL_LEARNING_RECORD_CONTRACT_TYPE: raise ValueError(f"contract_type must be {OPERATIONAL_LEARNING_RECORD_CONTRACT_TYPE}")
    evidence, relationships = data.get("evidence_references", ()), data.get("relationship_references", ())
    if not isinstance(evidence, (list, tuple)) or not isinstance(relationships, (list, tuple)): raise ValueError("reference fields must be arrays")
    try: disposition = LearningDisposition(data["disposition"])
    except (TypeError, ValueError) as exc: raise ValueError("disposition is not a recognized LearningDisposition") from exc
    return OperationalLearningRecord(learning_id=str(data["learning_id"]), outcome_record_id=str(data["outcome_record_id"]), execution_verification_id=str(data["execution_verification_id"]), execution_session_id=str(data["execution_session_id"]), execution_attempt_id=str(data["execution_attempt_id"]), provider_assignment_id=str(data["provider_assignment_id"]), lease_id=str(data["lease_id"]), worker_id=str(data["worker_id"]), provider_id=str(data["provider_id"]), disposition=disposition, recorded_at=_datetime(data["recorded_at"], "recorded_at"), authority_reference=str(data["authority_reference"]), evidence_references=tuple(EvidenceReference(uri=str(x["uri"]), media_type=str(x["media_type"]), description=x.get("description"), digest=x.get("digest")) for x in evidence), relationship_references=tuple(RelationshipReference(target_entity_id=str(x["target_entity_id"]), kind=RelationshipKind(x["kind"]), attributes=x.get("attributes")) for x in relationships), revision=data["revision"], version=str(data["version"]))

def operational_learning_record_from_json(payload: str | bytes | bytearray) -> OperationalLearningRecord:
    data = json.loads(payload)
    if not isinstance(data, dict): raise ValueError("Operational Learning Record JSON must be an object")
    return operational_learning_record_from_dict(data)
