"""Canonical, pure Worker Claim contract."""

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

WORKER_CLAIM_CONTRACT_TYPE = "dexter.worker_claim"
WORKER_CLAIM_VERSION = "1.0"


class ClaimState(StringEnum):
    REQUESTED = "REQUESTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("claim_timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def _valid_identity(value: str) -> bool:
    prefix = "dexter:claim:"
    if not value.startswith(prefix):
        return False
    try:
        UUID(value.removeprefix(prefix))
    except ValueError:
        return False
    return True


@dataclass(frozen=True, slots=True)
class WorkerClaim:
    """A Worker's ownership assertion for a Pending Job; never authority to execute."""

    claim_id: str
    pending_job_id: str
    worker_id: str
    claim_timestamp: datetime
    state: ClaimState
    authority_reference: str
    evidence_references: tuple[EvidenceReference, ...] = ()
    relationship_references: tuple[RelationshipReference, ...] = ()
    revision: int = 1
    version: str = WORKER_CLAIM_VERSION
    contract_type: str = field(default=WORKER_CLAIM_CONTRACT_TYPE, init=False)

    def __post_init__(self) -> None:
        for name in ("claim_id", "pending_job_id", "worker_id", "authority_reference", "version"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string")
            object.__setattr__(self, name, value.strip())
        object.__setattr__(self, "claim_timestamp", _utc(self.claim_timestamp))
        object.__setattr__(self, "evidence_references", tuple(self.evidence_references))
        object.__setattr__(self, "relationship_references", tuple(self.relationship_references))

    def validate(self) -> ValidationReport:
        issues: list[ValidationIssue] = []
        required = (("claim_id", "missing_claim_identity"), ("pending_job_id", "missing_pending_job_reference"),
                    ("worker_id", "missing_worker_identity"), ("authority_reference", "missing_authority_reference"))
        for name, code in required:
            if not getattr(self, name):
                issues.append(ValidationIssue(code, f"{name} is required", f"$.{name}"))
        if self.claim_id and not _valid_identity(self.claim_id):
            issues.append(ValidationIssue("invalid_claim_identity", "claim_id must be dexter:claim:<uuid>", "$.claim_id"))
        if not isinstance(self.state, ClaimState):
            issues.append(ValidationIssue("invalid_state", "state is not a recognized ClaimState", "$.state"))
        elif self.state is ClaimState.UNKNOWN:
            issues.append(ValidationIssue("unknown_state", "UNKNOWN cannot silently validate", "$.state"))
        if not isinstance(self.revision, int) or isinstance(self.revision, bool) or self.revision < 1:
            issues.append(ValidationIssue("invalid_revision", "revision must be a positive integer", "$.revision"))
        if self.version != WORKER_CLAIM_VERSION:
            issues.append(ValidationIssue("unsupported_version", f"expected {WORKER_CLAIM_VERSION}", "$.version"))
        return ValidationReport(tuple(issues))


def worker_claim_to_dict(claim: WorkerClaim) -> dict[str, Any]:
    return contract_to_dict(claim)


def worker_claim_to_json(claim: WorkerClaim, *, indent: int | None = None) -> str:
    return contract_to_json(claim, indent=indent)


def _datetime(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("claim_timestamp must be a timestamp string")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("claim_timestamp must be an ISO 8601 timestamp") from exc


def worker_claim_from_dict(data: Mapping[str, Any]) -> WorkerClaim:
    fields = {"contract_type", "claim_id", "pending_job_id", "worker_id", "claim_timestamp", "state",
              "authority_reference", "evidence_references", "relationship_references", "revision", "version"}
    unknown = set(data).difference(fields)
    if unknown:
        raise ValueError(f"unknown fields: {', '.join(sorted(unknown))}")
    missing = fields.difference({"evidence_references", "relationship_references"}).difference(data)
    if missing:
        raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")
    if data["contract_type"] != WORKER_CLAIM_CONTRACT_TYPE:
        raise ValueError(f"contract_type must be {WORKER_CLAIM_CONTRACT_TYPE}")
    evidence = data.get("evidence_references", ())
    relationships = data.get("relationship_references", ())
    if not isinstance(evidence, (list, tuple)) or not isinstance(relationships, (list, tuple)):
        raise ValueError("reference fields must be arrays")
    try:
        state = ClaimState(data["state"])
    except (TypeError, ValueError) as exc:
        raise ValueError("state is not a recognized ClaimState") from exc
    return WorkerClaim(
        claim_id=str(data["claim_id"]), pending_job_id=str(data["pending_job_id"]), worker_id=str(data["worker_id"]),
        claim_timestamp=_datetime(data["claim_timestamp"]), state=state, authority_reference=str(data["authority_reference"]),
        evidence_references=tuple(EvidenceReference(uri=str(x["uri"]), media_type=str(x["media_type"]), description=x.get("description"), digest=x.get("digest")) for x in evidence),
        relationship_references=tuple(RelationshipReference(target_entity_id=str(x["target_entity_id"]), kind=RelationshipKind(x["kind"]), attributes=x.get("attributes")) for x in relationships),
        revision=data["revision"], version=str(data["version"]),
    )


def worker_claim_from_json(payload: str | bytes | bytearray) -> WorkerClaim:
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Worker Claim JSON must be an object")
    return worker_claim_from_dict(data)
