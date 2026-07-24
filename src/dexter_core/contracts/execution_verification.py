"""Canonical, pure Execution Verification contract."""
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

EXECUTION_VERIFICATION_CONTRACT_TYPE = "dexter.execution_verification"
EXECUTION_VERIFICATION_VERSION = "1.0"

class VerificationResult(StringEnum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    FAILED_VERIFICATION = "FAILED_VERIFICATION"
    INCONCLUSIVE = "INCONCLUSIVE"
    UNKNOWN = "UNKNOWN"

def _utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)

def _valid_identity(value: str) -> bool:
    prefix = "dexter:execution-verification:"
    if not value.startswith(prefix): return False
    try: UUID(value.removeprefix(prefix))
    except ValueError: return False
    return True

@dataclass(frozen=True, slots=True)
class ExecutionVerification:
    """Governed evaluation of completed-session evidence; never execution."""
    verification_id: str
    execution_session_id: str
    execution_attempt_id: str
    provider_assignment_id: str
    lease_id: str
    worker_id: str
    provider_id: str
    result: VerificationResult
    verified_at: datetime
    authority_reference: str
    evidence_references: tuple[EvidenceReference, ...] = ()
    relationship_references: tuple[RelationshipReference, ...] = ()
    revision: int = 1
    version: str = EXECUTION_VERIFICATION_VERSION
    contract_type: str = field(default=EXECUTION_VERIFICATION_CONTRACT_TYPE, init=False)

    def __post_init__(self) -> None:
        for name in ("verification_id", "execution_session_id", "execution_attempt_id", "provider_assignment_id", "lease_id", "worker_id", "provider_id", "authority_reference", "version"):
            value = getattr(self, name)
            if not isinstance(value, str): raise TypeError(f"{name} must be a string")
            object.__setattr__(self, name, value.strip())
        object.__setattr__(self, "verified_at", _utc(self.verified_at, "verified_at"))
        object.__setattr__(self, "evidence_references", tuple(self.evidence_references))
        object.__setattr__(self, "relationship_references", tuple(self.relationship_references))

    def validate(self) -> ValidationReport:
        issues: list[ValidationIssue] = []
        required = (("verification_id", "missing_verification_identity"), ("execution_session_id", "missing_execution_session_reference"), ("execution_attempt_id", "missing_execution_attempt_reference"), ("provider_assignment_id", "missing_provider_assignment_reference"), ("lease_id", "missing_lease_reference"), ("worker_id", "missing_worker_identity"), ("provider_id", "missing_provider_identity"), ("authority_reference", "missing_authority_reference"))
        for name, code in required:
            if not getattr(self, name): issues.append(ValidationIssue(code, f"{name} is required", f"$.{name}"))
        if self.verification_id and not _valid_identity(self.verification_id): issues.append(ValidationIssue("invalid_verification_identity", "verification_id must be dexter:execution-verification:<uuid>", "$.verification_id"))
        if not isinstance(self.result, VerificationResult): issues.append(ValidationIssue("invalid_verification_result", "result is not a recognized VerificationResult", "$.result"))
        elif self.result is VerificationResult.UNKNOWN: issues.append(ValidationIssue("unknown_verification_result", "UNKNOWN cannot silently validate", "$.result"))
        if not isinstance(self.revision, int) or isinstance(self.revision, bool) or self.revision < 1: issues.append(ValidationIssue("invalid_revision", "revision must be a positive integer", "$.revision"))
        if self.version != EXECUTION_VERIFICATION_VERSION: issues.append(ValidationIssue("unsupported_version", f"expected {EXECUTION_VERIFICATION_VERSION}", "$.version"))
        return ValidationReport(tuple(issues))

def execution_verification_to_dict(value: ExecutionVerification) -> dict[str, Any]: return contract_to_dict(value)
def execution_verification_to_json(value: ExecutionVerification, *, indent: int | None = None) -> str: return contract_to_json(value, indent=indent)
def _datetime(value: Any, name: str) -> datetime:
    if not isinstance(value, str): raise ValueError(f"{name} must be a timestamp string")
    try: return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc: raise ValueError(f"{name} must be an ISO 8601 timestamp") from exc

def execution_verification_from_dict(data: Mapping[str, Any]) -> ExecutionVerification:
    fields = {"contract_type", "verification_id", "execution_session_id", "execution_attempt_id", "provider_assignment_id", "lease_id", "worker_id", "provider_id", "result", "verified_at", "authority_reference", "evidence_references", "relationship_references", "revision", "version"}
    unknown = set(data).difference(fields)
    if unknown: raise ValueError(f"unknown fields: {', '.join(sorted(unknown))}")
    missing = fields.difference({"evidence_references", "relationship_references"}).difference(data)
    if missing: raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")
    if data["contract_type"] != EXECUTION_VERIFICATION_CONTRACT_TYPE: raise ValueError(f"contract_type must be {EXECUTION_VERIFICATION_CONTRACT_TYPE}")
    evidence, relationships = data.get("evidence_references", ()), data.get("relationship_references", ())
    if not isinstance(evidence, (list, tuple)) or not isinstance(relationships, (list, tuple)): raise ValueError("reference fields must be arrays")
    try: result = VerificationResult(data["result"])
    except (TypeError, ValueError) as exc: raise ValueError("result is not a recognized VerificationResult") from exc
    return ExecutionVerification(verification_id=str(data["verification_id"]), execution_session_id=str(data["execution_session_id"]), execution_attempt_id=str(data["execution_attempt_id"]), provider_assignment_id=str(data["provider_assignment_id"]), lease_id=str(data["lease_id"]), worker_id=str(data["worker_id"]), provider_id=str(data["provider_id"]), result=result, verified_at=_datetime(data["verified_at"], "verified_at"), authority_reference=str(data["authority_reference"]), evidence_references=tuple(EvidenceReference(uri=str(x["uri"]), media_type=str(x["media_type"]), description=x.get("description"), digest=x.get("digest")) for x in evidence), relationship_references=tuple(RelationshipReference(target_entity_id=str(x["target_entity_id"]), kind=RelationshipKind(x["kind"]), attributes=x.get("attributes")) for x in relationships), revision=data["revision"], version=str(data["version"]))

def execution_verification_from_json(payload: str | bytes | bytearray) -> ExecutionVerification:
    data = json.loads(payload)
    if not isinstance(data, dict): raise ValueError("Execution Verification JSON must be an object")
    return execution_verification_from_dict(data)
