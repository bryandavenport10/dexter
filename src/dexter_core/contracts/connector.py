"""Governed contracts shared by read-only infrastructure connectors."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping
from urllib.parse import urlsplit
from uuid import UUID

from ..enums import StringEnum
from ..serialization import contract_to_dict, contract_to_json
from ..validation import ValidationIssue, ValidationReport
from .evidence import Evidence, evidence_from_dict
from .observation import utc_timestamp

CONNECTOR_CONTRACT_VERSION = "1.0"
CONNECTOR_METADATA_CONTRACT_TYPE = "dexter.connector_metadata"
CONNECTOR_STATUS_CONTRACT_TYPE = "dexter.connector_status"
COLLECTION_CONTEXT_CONTRACT_TYPE = "dexter.connector_collection_context"
COLLECTION_RESULT_CONTRACT_TYPE = "dexter.connector_collection_result"
CONNECTOR_ERROR_CONTRACT_TYPE = "dexter.connector_error"


class ConnectorCapability(StringEnum):
    CLUSTER_OBSERVATION = "CLUSTER_OBSERVATION"
    NODE_OBSERVATION = "NODE_OBSERVATION"
    VIRTUAL_MACHINE_OBSERVATION = "VIRTUAL_MACHINE_OBSERVATION"
    CONTAINER_OBSERVATION = "CONTAINER_OBSERVATION"
    STORAGE_OBSERVATION = "STORAGE_OBSERVATION"
    TASK_OBSERVATION = "TASK_OBSERVATION"
    HEALTH_STATUS_OBSERVATION = "HEALTH_STATUS_OBSERVATION"
    VERSION_OBSERVATION = "VERSION_OBSERVATION"


class ConnectorStatus(StringEnum):
    READY = "READY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    DISABLED = "DISABLED"
    UNKNOWN = "UNKNOWN"


class CollectionStatus(StringEnum):
    SUCCEEDED = "SUCCEEDED"
    PARTIALLY_SUCCEEDED = "PARTIALLY_SUCCEEDED"
    FAILED = "FAILED"
    NO_DATA = "NO_DATA"
    UNSUPPORTED = "UNSUPPORTED"
    UNKNOWN = "UNKNOWN"


class ConnectorErrorCategory(StringEnum):
    AUTHENTICATION = "AUTHENTICATION"
    AUTHORIZATION = "AUTHORIZATION"
    CONNECTIVITY = "CONNECTIVITY"
    TIMEOUT = "TIMEOUT"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    UNSUPPORTED = "UNSUPPORTED"
    INTERNAL = "INTERNAL"
    UNKNOWN = "UNKNOWN"


def _strings(value: object, names: tuple[str, ...]) -> None:
    for name in names:
        item = getattr(value, name)
        if not isinstance(item, str):
            raise TypeError(f"{name} must be a string")
        object.__setattr__(value, name, item.strip())


def _valid_identity(value: str, kind: str) -> bool:
    prefix = f"dexter:{kind}:"
    if not value.startswith(prefix):
        return False
    try:
        UUID(value.removeprefix(prefix))
    except ValueError:
        return False
    return True


def _base_issues(value: object, identity_name: str, identity_kind: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    identity = getattr(value, identity_name)
    if not identity:
        issues.append(ValidationIssue("missing_identity", f"{identity_name} is required", f"$.{identity_name}"))
    elif not _valid_identity(identity, identity_kind):
        issues.append(ValidationIssue("invalid_identity", f"{identity_name} must be dexter:{identity_kind}:<uuid>", f"$.{identity_name}"))
    authority = getattr(value, "authority_reference")
    if not authority:
        issues.append(ValidationIssue("missing_authority", "authority_reference is required", "$.authority_reference"))
    revision = getattr(value, "revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        issues.append(ValidationIssue("invalid_revision", "revision must be a positive integer", "$.revision"))
    if getattr(value, "version") != CONNECTOR_CONTRACT_VERSION:
        issues.append(ValidationIssue("unsupported_version", f"expected {CONNECTOR_CONTRACT_VERSION}", "$.version"))
    return issues


_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(password|passwd|api[_-]?token|access[_-]?token|private[_-]?key|cookie|authorization)\s*[:=]"
)
_AUTHENTICATION_REFERENCE = re.compile(r"^authref:[A-Za-z0-9][A-Za-z0-9._:/!-]*$")


def is_safe_text(value: str) -> bool:
    """Return whether governed text is free of common secret-bearing forms."""
    if _SECRET_ASSIGNMENT.search(value):
        return False
    for word in value.split():
        if "://" not in word:
            continue
        parsed = urlsplit(word.rstrip(".,;)"))
        if parsed.username is not None or parsed.password is not None or parsed.query:
            return False
    return True


def _item_key(item: Any) -> str:
    if isinstance(item, StringEnum):
        return item.value
    for name in ("evidence_id", "error_id"):
        if hasattr(item, name):
            return str(getattr(item, name))
    return str(item)


def _unique_sorted(values: tuple[Any, ...], name: str, *, reject_duplicates: bool = True) -> tuple[Any, ...]:
    normalized = tuple(sorted(values, key=_item_key))
    keys = tuple(_item_key(item) for item in normalized)
    if reject_duplicates and len(set(keys)) != len(keys):
        raise ValueError(f"{name} must contain unique values")
    return normalized


@dataclass(frozen=True, slots=True)
class ConnectorMetadata:
    connector_id: str
    connector_type: str
    connector_version: str
    source_system_id: str
    capabilities: tuple[ConnectorCapability, ...]
    authority_reference: str
    revision: int = 1
    version: str = CONNECTOR_CONTRACT_VERSION
    contract_type: str = field(default=CONNECTOR_METADATA_CONTRACT_TYPE, init=False)

    def __post_init__(self) -> None:
        _strings(self, ("connector_id", "connector_type", "connector_version", "source_system_id", "authority_reference", "version"))
        object.__setattr__(self, "capabilities", _unique_sorted(tuple(self.capabilities), "capabilities"))

    def validate(self) -> ValidationReport:
        issues = _base_issues(self, "connector_id", "connector")
        for name in ("connector_type", "connector_version", "source_system_id"):
            if not getattr(self, name):
                issues.append(ValidationIssue(f"missing_{name}", f"{name} is required", f"$.{name}"))
        if any(not isinstance(item, ConnectorCapability) for item in self.capabilities):
            issues.append(ValidationIssue("invalid_capability", "capabilities must be recognized", "$.capabilities"))
        return ValidationReport(tuple(issues))


@dataclass(frozen=True, slots=True)
class ConnectorCollectionContext:
    collection_id: str
    connector_id: str
    source_system_id: str
    requested_capabilities: tuple[ConnectorCapability, ...]
    requested_at: datetime
    authority_reference: str
    correlation_id: str
    authentication_reference: str | None = None
    revision: int = 1
    version: str = CONNECTOR_CONTRACT_VERSION
    contract_type: str = field(default=COLLECTION_CONTEXT_CONTRACT_TYPE, init=False)

    def __post_init__(self) -> None:
        _strings(self, ("collection_id", "connector_id", "source_system_id", "authority_reference", "correlation_id", "version"))
        if self.authentication_reference is not None:
            if not isinstance(self.authentication_reference, str):
                raise TypeError("authentication_reference must be a string or None")
            object.__setattr__(self, "authentication_reference", self.authentication_reference.strip() or None)
        object.__setattr__(self, "requested_at", utc_timestamp(self.requested_at, "requested_at"))
        object.__setattr__(self, "requested_capabilities", _unique_sorted(tuple(self.requested_capabilities), "requested_capabilities"))

    def validate(self) -> ValidationReport:
        issues = _base_issues(self, "collection_id", "collection")
        if not _valid_identity(self.connector_id, "connector"):
            issues.append(ValidationIssue("invalid_connector_reference", "connector_id must be canonical", "$.connector_id"))
        if not self.source_system_id:
            issues.append(ValidationIssue("missing_source_system", "source_system_id is required", "$.source_system_id"))
        if not self.correlation_id:
            issues.append(ValidationIssue("missing_correlation", "correlation_id is required", "$.correlation_id"))
        if any(not isinstance(item, ConnectorCapability) for item in self.requested_capabilities):
            issues.append(ValidationIssue("invalid_capability", "requested capabilities must be recognized", "$.requested_capabilities"))
        if self.authentication_reference is not None and (
            _AUTHENTICATION_REFERENCE.fullmatch(self.authentication_reference) is None
            or not is_safe_text(self.authentication_reference)
        ):
            issues.append(ValidationIssue("invalid_authentication_reference", "authentication_reference must be a protected authref identifier", "$.authentication_reference"))
        return ValidationReport(tuple(issues))


@dataclass(frozen=True, slots=True)
class ConnectorStatusRecord:
    status_id: str
    connector_id: str
    source_system_id: str
    status: ConnectorStatus
    observed_at: datetime
    authority_reference: str
    message: str | None = None
    revision: int = 1
    version: str = CONNECTOR_CONTRACT_VERSION
    contract_type: str = field(default=CONNECTOR_STATUS_CONTRACT_TYPE, init=False)

    def __post_init__(self) -> None:
        _strings(self, ("status_id", "connector_id", "source_system_id", "authority_reference", "version"))
        object.__setattr__(self, "observed_at", utc_timestamp(self.observed_at, "observed_at"))
        if self.message is not None:
            if not isinstance(self.message, str):
                raise TypeError("message must be a string or None")
            object.__setattr__(self, "message", self.message.strip() or None)

    def validate(self) -> ValidationReport:
        issues = _base_issues(self, "status_id", "connector-status")
        if not _valid_identity(self.connector_id, "connector"):
            issues.append(ValidationIssue("invalid_connector_reference", "connector_id must be canonical", "$.connector_id"))
        if not self.source_system_id:
            issues.append(ValidationIssue("missing_source_system", "source_system_id is required", "$.source_system_id"))
        if not isinstance(self.status, ConnectorStatus):
            issues.append(ValidationIssue("invalid_connector_status", "status is not recognized", "$.status"))
        elif self.status is ConnectorStatus.UNKNOWN:
            issues.append(ValidationIssue("unknown_connector_status", "UNKNOWN cannot validate in a finalized status record", "$.status"))
        if self.message is not None and not is_safe_text(self.message):
            issues.append(ValidationIssue("unsafe_status_message", "message may contain secret material", "$.message"))
        return ValidationReport(tuple(issues))


@dataclass(frozen=True, slots=True)
class ConnectorError:
    error_id: str
    connector_id: str
    collection_context_id: str
    category: ConnectorErrorCategory
    message: str
    occurred_at: datetime
    retryable: bool
    authority_reference: str
    revision: int = 1
    version: str = CONNECTOR_CONTRACT_VERSION
    contract_type: str = field(default=CONNECTOR_ERROR_CONTRACT_TYPE, init=False)

    def __post_init__(self) -> None:
        _strings(self, ("error_id", "connector_id", "collection_context_id", "message", "authority_reference", "version"))
        object.__setattr__(self, "occurred_at", utc_timestamp(self.occurred_at, "occurred_at"))
        if not isinstance(self.retryable, bool):
            raise TypeError("retryable must be a bool")

    def validate(self) -> ValidationReport:
        issues = _base_issues(self, "error_id", "connector-error")
        if not _valid_identity(self.connector_id, "connector"):
            issues.append(ValidationIssue("invalid_connector_reference", "connector_id must be canonical", "$.connector_id"))
        if not _valid_identity(self.collection_context_id, "collection"):
            issues.append(ValidationIssue("invalid_collection_reference", "collection_context_id must be canonical", "$.collection_context_id"))
        if not isinstance(self.category, ConnectorErrorCategory):
            issues.append(ValidationIssue("invalid_error_category", "category is not recognized", "$.category"))
        elif self.category is ConnectorErrorCategory.UNKNOWN:
            issues.append(ValidationIssue("unknown_error_category", "UNKNOWN cannot validate in a finalized error", "$.category"))
        if not self.message:
            issues.append(ValidationIssue("missing_error_message", "message is required", "$.message"))
        elif not is_safe_text(self.message):
            issues.append(ValidationIssue("unsafe_error_message", "message may contain secret material", "$.message"))
        return ValidationReport(tuple(issues))


@dataclass(frozen=True, slots=True)
class ConnectorCollectionResult:
    result_id: str
    collection_context_id: str
    connector_id: str
    source_system_id: str
    status: CollectionStatus
    started_at: datetime
    completed_at: datetime
    evidence: tuple[Evidence, ...]
    errors: tuple[ConnectorError, ...]
    authority_reference: str
    revision: int = 1
    version: str = CONNECTOR_CONTRACT_VERSION
    contract_type: str = field(default=COLLECTION_RESULT_CONTRACT_TYPE, init=False)

    def __post_init__(self) -> None:
        _strings(self, ("result_id", "collection_context_id", "connector_id", "source_system_id", "authority_reference", "version"))
        object.__setattr__(self, "started_at", utc_timestamp(self.started_at, "started_at"))
        object.__setattr__(self, "completed_at", utc_timestamp(self.completed_at, "completed_at"))
        object.__setattr__(self, "evidence", _unique_sorted(tuple(self.evidence), "evidence", reject_duplicates=False))
        object.__setattr__(self, "errors", _unique_sorted(tuple(self.errors), "errors", reject_duplicates=False))

    def validate(self) -> ValidationReport:
        issues = _base_issues(self, "result_id", "collection-result")
        if not _valid_identity(self.collection_context_id, "collection"):
            issues.append(ValidationIssue("invalid_collection_reference", "collection_context_id must be canonical", "$.collection_context_id"))
        if not _valid_identity(self.connector_id, "connector"):
            issues.append(ValidationIssue("invalid_connector_reference", "connector_id must be canonical", "$.connector_id"))
        if not self.source_system_id:
            issues.append(ValidationIssue("missing_source_system", "source_system_id is required", "$.source_system_id"))
        if not isinstance(self.status, CollectionStatus):
            issues.append(ValidationIssue("invalid_collection_status", "status is not recognized", "$.status"))
        elif self.status is CollectionStatus.UNKNOWN:
            issues.append(ValidationIssue("unknown_collection_status", "UNKNOWN cannot validate in a finalized result", "$.status"))
        if self.completed_at < self.started_at:
            issues.append(ValidationIssue("completed_before_started", "completed_at must not precede started_at", "$.completed_at"))
        evidence_ids = [item.evidence_id for item in self.evidence]
        if len(set(evidence_ids)) != len(evidence_ids):
            issues.append(ValidationIssue("duplicate_evidence", "evidence identities must be unique", "$.evidence"))
        for index, item in enumerate(self.evidence):
            for issue in item.validate().issues:
                issues.append(ValidationIssue(issue.code, issue.message, f"$.evidence[{index}]{issue.path[1:]}"))
        for index, item in enumerate(self.errors):
            for issue in item.validate().issues:
                issues.append(ValidationIssue(issue.code, issue.message, f"$.errors[{index}]{issue.path[1:]}"))
        return ValidationReport(tuple(issues))


def _datetime(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a timestamp string")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO 8601 timestamp") from exc


def _strict(data: Mapping[str, Any], fields: set[str], contract_type: str, optional: set[str] = set()) -> None:
    unknown = set(data).difference(fields)
    if unknown:
        raise ValueError(f"unknown fields: {', '.join(sorted(unknown))}")
    missing = fields.difference(optional).difference(data)
    if missing:
        raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")
    if data["contract_type"] != contract_type:
        raise ValueError(f"contract_type must be {contract_type}")


def _enum_tuple(value: Any, enum: type[StringEnum], name: str) -> tuple[Any, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be an array")
    try:
        return tuple(enum(item) for item in value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} contains an unrecognized value") from exc


def connector_metadata_from_dict(data: Mapping[str, Any]) -> ConnectorMetadata:
    fields = {"contract_type", "connector_id", "connector_type", "connector_version", "source_system_id", "capabilities", "authority_reference", "revision", "version"}
    _strict(data, fields, CONNECTOR_METADATA_CONTRACT_TYPE)
    return ConnectorMetadata(str(data["connector_id"]), str(data["connector_type"]), str(data["connector_version"]), str(data["source_system_id"]), _enum_tuple(data["capabilities"], ConnectorCapability, "capabilities"), str(data["authority_reference"]), data["revision"], str(data["version"]))


def collection_context_from_dict(data: Mapping[str, Any]) -> ConnectorCollectionContext:
    fields = {"contract_type", "collection_id", "connector_id", "source_system_id", "requested_capabilities", "requested_at", "authority_reference", "correlation_id", "authentication_reference", "revision", "version"}
    _strict(data, fields, COLLECTION_CONTEXT_CONTRACT_TYPE, {"authentication_reference"})
    return ConnectorCollectionContext(str(data["collection_id"]), str(data["connector_id"]), str(data["source_system_id"]), _enum_tuple(data["requested_capabilities"], ConnectorCapability, "requested_capabilities"), _datetime(data["requested_at"], "requested_at"), str(data["authority_reference"]), str(data["correlation_id"]), None if data.get("authentication_reference") is None else str(data["authentication_reference"]), data["revision"], str(data["version"]))


def connector_status_from_dict(data: Mapping[str, Any]) -> ConnectorStatusRecord:
    fields = {"contract_type", "status_id", "connector_id", "source_system_id", "status", "observed_at", "authority_reference", "message", "revision", "version"}
    _strict(data, fields, CONNECTOR_STATUS_CONTRACT_TYPE, {"message"})
    try:
        status = ConnectorStatus(data["status"])
    except (TypeError, ValueError) as exc:
        raise ValueError("status is not a recognized ConnectorStatus") from exc
    return ConnectorStatusRecord(str(data["status_id"]), str(data["connector_id"]), str(data["source_system_id"]), status, _datetime(data["observed_at"], "observed_at"), str(data["authority_reference"]), None if data.get("message") is None else str(data["message"]), data["revision"], str(data["version"]))


def connector_error_from_dict(data: Mapping[str, Any]) -> ConnectorError:
    fields = {"contract_type", "error_id", "connector_id", "collection_context_id", "category", "message", "occurred_at", "retryable", "authority_reference", "revision", "version"}
    _strict(data, fields, CONNECTOR_ERROR_CONTRACT_TYPE)
    try:
        category = ConnectorErrorCategory(data["category"])
    except (TypeError, ValueError) as exc:
        raise ValueError("category is not a recognized ConnectorErrorCategory") from exc
    return ConnectorError(str(data["error_id"]), str(data["connector_id"]), str(data["collection_context_id"]), category, str(data["message"]), _datetime(data["occurred_at"], "occurred_at"), data["retryable"], str(data["authority_reference"]), data["revision"], str(data["version"]))


def collection_result_from_dict(data: Mapping[str, Any]) -> ConnectorCollectionResult:
    fields = {"contract_type", "result_id", "collection_context_id", "connector_id", "source_system_id", "status", "started_at", "completed_at", "evidence", "errors", "authority_reference", "revision", "version"}
    _strict(data, fields, COLLECTION_RESULT_CONTRACT_TYPE)
    if not isinstance(data["evidence"], (list, tuple)) or not isinstance(data["errors"], (list, tuple)):
        raise ValueError("evidence and errors must be arrays")
    try:
        status = CollectionStatus(data["status"])
    except (TypeError, ValueError) as exc:
        raise ValueError("status is not a recognized CollectionStatus") from exc
    return ConnectorCollectionResult(str(data["result_id"]), str(data["collection_context_id"]), str(data["connector_id"]), str(data["source_system_id"]), status, _datetime(data["started_at"], "started_at"), _datetime(data["completed_at"], "completed_at"), tuple(evidence_from_dict(item) for item in data["evidence"]), tuple(connector_error_from_dict(item) for item in data["errors"]), str(data["authority_reference"]), data["revision"], str(data["version"]))


def _to_dict(value: Any) -> dict[str, Any]:
    return contract_to_dict(value)


def _to_json(value: Any, *, indent: int | None = None) -> str:
    return contract_to_json(value, indent=indent)


def _from_json(payload: str | bytes | bytearray, loader: Any, label: str) -> Any:
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError(f"{label} JSON must be an object")
    return loader(data)


connector_metadata_to_dict = _to_dict
connector_metadata_to_json = _to_json
collection_context_to_dict = _to_dict
collection_context_to_json = _to_json
connector_status_to_dict = _to_dict
connector_status_to_json = _to_json
connector_error_to_dict = _to_dict
connector_error_to_json = _to_json
collection_result_to_dict = _to_dict
collection_result_to_json = _to_json


def connector_metadata_from_json(payload: str | bytes | bytearray) -> ConnectorMetadata:
    return _from_json(payload, connector_metadata_from_dict, "Connector Metadata")


def collection_context_from_json(payload: str | bytes | bytearray) -> ConnectorCollectionContext:
    return _from_json(payload, collection_context_from_dict, "Collection Context")


def connector_status_from_json(payload: str | bytes | bytearray) -> ConnectorStatusRecord:
    return _from_json(payload, connector_status_from_dict, "Connector Status")


def connector_error_from_json(payload: str | bytes | bytearray) -> ConnectorError:
    return _from_json(payload, connector_error_from_dict, "Connector Error")


def collection_result_from_json(payload: str | bytes | bytearray) -> ConnectorCollectionResult:
    return _from_json(payload, collection_result_from_dict, "Collection Result")
