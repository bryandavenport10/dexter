"""Canonical, pure Lease contract."""
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

LEASE_CONTRACT_TYPE = "dexter.lease"
LEASE_VERSION = "1.0"


class LeaseState(StringEnum):
    ISSUED = "ISSUED"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    RELEASED = "RELEASED"
    UNKNOWN = "UNKNOWN"


def _utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _valid_identity(value: str) -> bool:
    prefix = "dexter:lease:"
    if not value.startswith(prefix):
        return False
    try:
        UUID(value.removeprefix(prefix))
    except ValueError:
        return False
    return True


@dataclass(frozen=True, slots=True)
class Lease:
    """Governed authorization for temporary ownership of a Pending Job."""
    lease_id: str
    worker_claim_id: str
    pending_job_id: str
    worker_id: str
    state: LeaseState
    issued_at: datetime
    expires_at: datetime
    authority_reference: str
    evidence_references: tuple[EvidenceReference, ...] = ()
    relationship_references: tuple[RelationshipReference, ...] = ()
    revision: int = 1
    version: str = LEASE_VERSION
    contract_type: str = field(default=LEASE_CONTRACT_TYPE, init=False)

    def __post_init__(self) -> None:
        for name in ("lease_id", "worker_claim_id", "pending_job_id", "worker_id", "authority_reference", "version"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string")
            object.__setattr__(self, name, value.strip())
        object.__setattr__(self, "issued_at", _utc(self.issued_at, "issued_at"))
        object.__setattr__(self, "expires_at", _utc(self.expires_at, "expires_at"))
        object.__setattr__(self, "evidence_references", tuple(self.evidence_references))
        object.__setattr__(self, "relationship_references", tuple(self.relationship_references))

    def validate(self) -> ValidationReport:
        issues: list[ValidationIssue] = []
        required = (("lease_id", "missing_lease_identity"), ("worker_claim_id", "missing_worker_claim_reference"), ("pending_job_id", "missing_pending_job_reference"), ("worker_id", "missing_worker_identity"), ("authority_reference", "missing_authority_reference"))
        for name, code in required:
            if not getattr(self, name):
                issues.append(ValidationIssue(code, f"{name} is required", f"$.{name}"))
        if self.lease_id and not _valid_identity(self.lease_id):
            issues.append(ValidationIssue("invalid_lease_identity", "lease_id must be dexter:lease:<uuid>", "$.lease_id"))
        if not isinstance(self.state, LeaseState):
            issues.append(ValidationIssue("invalid_state", "state is not a recognized LeaseState", "$.state"))
        elif self.state is LeaseState.UNKNOWN:
            issues.append(ValidationIssue("unknown_state", "UNKNOWN cannot silently validate", "$.state"))
        if self.expires_at <= self.issued_at:
            issues.append(ValidationIssue("invalid_expiration", "expires_at must occur after issued_at", "$.expires_at"))
        if not isinstance(self.revision, int) or isinstance(self.revision, bool) or self.revision < 1:
            issues.append(ValidationIssue("invalid_revision", "revision must be a positive integer", "$.revision"))
        if self.version != LEASE_VERSION:
            issues.append(ValidationIssue("unsupported_version", f"expected {LEASE_VERSION}", "$.version"))
        return ValidationReport(tuple(issues))


def lease_to_dict(lease: Lease) -> dict[str, Any]:
    return contract_to_dict(lease)


def lease_to_json(lease: Lease, *, indent: int | None = None) -> str:
    return contract_to_json(lease, indent=indent)


def _datetime(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a timestamp string")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO 8601 timestamp") from exc


def lease_from_dict(data: Mapping[str, Any]) -> Lease:
    fields = {"contract_type", "lease_id", "worker_claim_id", "pending_job_id", "worker_id", "state", "issued_at", "expires_at", "authority_reference", "evidence_references", "relationship_references", "revision", "version"}
    unknown = set(data).difference(fields)
    if unknown:
        raise ValueError(f"unknown fields: {', '.join(sorted(unknown))}")
    missing = fields.difference({"evidence_references", "relationship_references"}).difference(data)
    if missing:
        raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")
    if data["contract_type"] != LEASE_CONTRACT_TYPE:
        raise ValueError(f"contract_type must be {LEASE_CONTRACT_TYPE}")
    evidence, relationships = data.get("evidence_references", ()), data.get("relationship_references", ())
    if not isinstance(evidence, (list, tuple)) or not isinstance(relationships, (list, tuple)):
        raise ValueError("reference fields must be arrays")
    try:
        state = LeaseState(data["state"])
    except (TypeError, ValueError) as exc:
        raise ValueError("state is not a recognized LeaseState") from exc
    return Lease(
        lease_id=str(data["lease_id"]), worker_claim_id=str(data["worker_claim_id"]), pending_job_id=str(data["pending_job_id"]), worker_id=str(data["worker_id"]), state=state,
        issued_at=_datetime(data["issued_at"], "issued_at"), expires_at=_datetime(data["expires_at"], "expires_at"), authority_reference=str(data["authority_reference"]),
        evidence_references=tuple(EvidenceReference(uri=str(x["uri"]), media_type=str(x["media_type"]), description=x.get("description"), digest=x.get("digest")) for x in evidence),
        relationship_references=tuple(RelationshipReference(target_entity_id=str(x["target_entity_id"]), kind=RelationshipKind(x["kind"]), attributes=x.get("attributes")) for x in relationships),
        revision=data["revision"], version=str(data["version"]),
    )


def lease_from_json(payload: str | bytes | bytearray) -> Lease:
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Lease JSON must be an object")
    return lease_from_dict(data)
