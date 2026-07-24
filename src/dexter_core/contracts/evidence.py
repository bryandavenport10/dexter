"""Governed evidence produced from normalized operational observations."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping
from uuid import UUID
from ..enums import StringEnum
from ..serialization import contract_to_dict, contract_to_json
from ..validation import ValidationIssue, ValidationReport
from .observation import immutable_value, utc_timestamp

EVIDENCE_CONTRACT_TYPE = "dexter.evidence"
EVIDENCE_VERSION = "1.0"

class EvidenceType(StringEnum):
    PROXMOX_CLUSTER = "PROXMOX_CLUSTER"
    PROXMOX_NODE = "PROXMOX_NODE"
    PROXMOX_VIRTUAL_MACHINE = "PROXMOX_VIRTUAL_MACHINE"
    PROXMOX_CONTAINER = "PROXMOX_CONTAINER"
    PROXMOX_STORAGE = "PROXMOX_STORAGE"
    PROXMOX_TASK = "PROXMOX_TASK"

@dataclass(frozen=True, slots=True)
class SourceAuthority:
    proxmox_cluster: str
    node: str | None
    api_endpoint: str
    collection_method: str
    authentication_context: str
    asserted_at: datetime

    def __post_init__(self) -> None:
        for name in ("proxmox_cluster", "api_endpoint", "collection_method", "authentication_context"):
            value = getattr(self, name)
            if not isinstance(value, str): raise TypeError(f"{name} must be a string")
            object.__setattr__(self, name, value.strip())
        if self.node is not None:
            if not isinstance(self.node, str): raise TypeError("node must be a string or None")
            object.__setattr__(self, "node", self.node.strip() or None)
        object.__setattr__(self, "asserted_at", utc_timestamp(self.asserted_at, "asserted_at"))

    def validate(self) -> tuple[ValidationIssue, ...]:
        issues = []
        for name in ("proxmox_cluster", "api_endpoint", "collection_method", "authentication_context"):
            if not getattr(self, name): issues.append(ValidationIssue("missing_authority", f"authority {name} is required", f"$.authority.{name}"))
        return tuple(issues)

@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: str
    evidence_type: EvidenceType
    source_system: str
    source_object: str
    observation_timestamp: datetime
    collection_timestamp: datetime
    authority: SourceAuthority
    payload: Mapping[str, Any]
    relationships: tuple[str, ...] = ()
    revision: int = 1
    version: str = EVIDENCE_VERSION
    contract_type: str = field(default=EVIDENCE_CONTRACT_TYPE, init=False)

    def __post_init__(self) -> None:
        for name in ("evidence_id", "source_system", "source_object", "version"):
            value = getattr(self, name)
            if not isinstance(value, str): raise TypeError(f"{name} must be a string")
            object.__setattr__(self, name, value.strip())
        object.__setattr__(self, "observation_timestamp", utc_timestamp(self.observation_timestamp, "observation_timestamp"))
        object.__setattr__(self, "collection_timestamp", utc_timestamp(self.collection_timestamp, "collection_timestamp"))
        if not isinstance(self.authority, SourceAuthority): raise TypeError("authority must be a SourceAuthority")
        if not isinstance(self.payload, Mapping): raise TypeError("payload must be a mapping")
        object.__setattr__(self, "payload", immutable_value(self.payload))
        object.__setattr__(self, "relationships", tuple(str(item).strip() for item in self.relationships))

    def validate(self) -> ValidationReport:
        issues: list[ValidationIssue] = []
        if not self.evidence_id: issues.append(ValidationIssue("missing_evidence_identity", "evidence_id is required", "$.evidence_id"))
        elif not _valid_identity(self.evidence_id): issues.append(ValidationIssue("invalid_evidence_identity", "evidence_id must be dexter:evidence:<uuid>", "$.evidence_id"))
        if not isinstance(self.evidence_type, EvidenceType): issues.append(ValidationIssue("invalid_evidence_type", "evidence_type is not recognized", "$.evidence_type"))
        for name in ("source_system", "source_object"):
            if not getattr(self, name): issues.append(ValidationIssue("missing_source", f"{name} is required", f"$.{name}"))
        issues.extend(self.authority.validate())
        if self.collection_timestamp < self.observation_timestamp: issues.append(ValidationIssue("invalid_timestamp_order", "collection_timestamp cannot precede observation_timestamp", "$.collection_timestamp"))
        if not self.payload: issues.append(ValidationIssue("missing_payload", "payload is required", "$.payload"))
        if not isinstance(self.revision, int) or isinstance(self.revision, bool) or self.revision < 1: issues.append(ValidationIssue("invalid_revision", "revision must be a positive integer", "$.revision"))
        if self.version != EVIDENCE_VERSION: issues.append(ValidationIssue("unsupported_version", f"expected {EVIDENCE_VERSION}", "$.version"))
        return ValidationReport(tuple(issues))

def _valid_identity(value: str) -> bool:
    prefix = "dexter:evidence:"
    if not value.startswith(prefix): return False
    try: UUID(value.removeprefix(prefix))
    except ValueError: return False
    return True

def evidence_to_dict(value: Evidence) -> dict[str, Any]: return contract_to_dict(value)
def evidence_to_json(value: Evidence, *, indent: int | None = None) -> str: return contract_to_json(value, indent=indent)

def _datetime(value: Any, name: str) -> datetime:
    if not isinstance(value, str): raise ValueError(f"{name} must be a timestamp string")
    try: return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc: raise ValueError(f"{name} must be an ISO 8601 timestamp") from exc

def evidence_from_dict(data: Mapping[str, Any]) -> Evidence:
    fields = {"contract_type", "evidence_id", "evidence_type", "source_system", "source_object", "observation_timestamp", "collection_timestamp", "authority", "payload", "relationships", "revision", "version"}
    unknown = set(data).difference(fields)
    if unknown: raise ValueError(f"unknown fields: {', '.join(sorted(unknown))}")
    missing = fields.difference({"relationships"}).difference(data)
    if missing: raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")
    if data["contract_type"] != EVIDENCE_CONTRACT_TYPE: raise ValueError(f"contract_type must be {EVIDENCE_CONTRACT_TYPE}")
    authority = data["authority"]
    if not isinstance(authority, Mapping): raise ValueError("authority must be an object")
    authority_fields = {"proxmox_cluster", "node", "api_endpoint", "collection_method", "authentication_context", "asserted_at"}
    if set(authority) != authority_fields: raise ValueError("authority fields do not match the contract")
    try: evidence_type = EvidenceType(data["evidence_type"])
    except (TypeError, ValueError) as exc: raise ValueError("evidence_type is not a recognized EvidenceType") from exc
    if not isinstance(data["payload"], Mapping): raise ValueError("payload must be an object")
    relationships = data.get("relationships", ())
    if not isinstance(relationships, (list, tuple)): raise ValueError("relationships must be an array")
    return Evidence(evidence_id=str(data["evidence_id"]), evidence_type=evidence_type, source_system=str(data["source_system"]), source_object=str(data["source_object"]), observation_timestamp=_datetime(data["observation_timestamp"], "observation_timestamp"), collection_timestamp=_datetime(data["collection_timestamp"], "collection_timestamp"), authority=SourceAuthority(proxmox_cluster=str(authority["proxmox_cluster"]), node=None if authority["node"] is None else str(authority["node"]), api_endpoint=str(authority["api_endpoint"]), collection_method=str(authority["collection_method"]), authentication_context=str(authority["authentication_context"]), asserted_at=_datetime(authority["asserted_at"], "authority.asserted_at")), payload=data["payload"], relationships=tuple(str(item) for item in relationships), revision=data["revision"], version=str(data["version"]))

def evidence_from_json(payload: str | bytes | bytearray) -> Evidence:
    data = json.loads(payload)
    if not isinstance(data, dict): raise ValueError("Evidence JSON must be an object")
    return evidence_from_dict(data)
