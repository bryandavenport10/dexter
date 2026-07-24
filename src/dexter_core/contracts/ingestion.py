"""Governed contracts for deterministic Evidence ingestion orchestration."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping
from uuid import UUID

from ..enums import StringEnum
from ..serialization import contract_to_dict, contract_to_json
from ..validation import ValidationIssue, ValidationReport
from .connector import (
    ConnectorCapability,
    ConnectorCollectionContext,
    collection_context_from_dict,
    is_safe_text,
)
from .observation import utc_timestamp

INGESTION_VERSION = "1.0"
INGESTION_REQUEST_CONTRACT_TYPE = "dexter.ingestion_request"
INGESTION_RESULT_CONTRACT_TYPE = "dexter.ingestion_result"
INGESTION_ERROR_CONTRACT_TYPE = "dexter.ingestion_error"


class IngestionStatus(StringEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    NO_DATA = "NO_DATA"
    UNSUPPORTED = "UNSUPPORTED"


class IngestionErrorCategory(StringEnum):
    CONNECTOR_UNAVAILABLE = "CONNECTOR_UNAVAILABLE"
    REPOSITORY_UNAVAILABLE = "REPOSITORY_UNAVAILABLE"
    VALIDATION_FAILURE = "VALIDATION_FAILURE"
    DUPLICATE_EVIDENCE = "DUPLICATE_EVIDENCE"
    UNSUPPORTED_CAPABILITY = "UNSUPPORTED_CAPABILITY"
    NO_DATA = "NO_DATA"


class RepositoryStatus(StringEnum):
    HEALTHY = "HEALTHY"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


def _identity(value: str, kind: str) -> bool:
    prefix = f"dexter:{kind}:"
    if not value.startswith(prefix):
        return False
    try:
        UUID(value.removeprefix(prefix))
    except ValueError:
        return False
    return True


def _text(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value.strip()


def _base_issues(
    value: object, identity_name: str, identity_kind: str
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    identity = getattr(value, identity_name)
    if not identity:
        issues.append(
            ValidationIssue(
                "missing_identity", f"{identity_name} is required", f"$.{identity_name}"
            )
        )
    elif not _identity(identity, identity_kind):
        issues.append(
            ValidationIssue(
                "invalid_identity",
                f"{identity_name} must be dexter:{identity_kind}:<uuid>",
                f"$.{identity_name}",
            )
        )
    authority = getattr(value, "authority_reference")
    if not authority:
        issues.append(
            ValidationIssue(
                "missing_authority",
                "authority_reference is required",
                "$.authority_reference",
            )
        )
    elif not is_safe_text(authority):
        issues.append(
            ValidationIssue(
                "unsafe_authority",
                "authority_reference may contain secret material",
                "$.authority_reference",
            )
        )
    revision = getattr(value, "revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        issues.append(
            ValidationIssue(
                "invalid_revision",
                "revision must be a positive integer",
                "$.revision",
            )
        )
    if getattr(value, "version") != INGESTION_VERSION:
        issues.append(
            ValidationIssue(
                "unsupported_version",
                f"expected {INGESTION_VERSION}",
                "$.version",
            )
        )
    return issues


@dataclass(frozen=True, slots=True)
class IngestionRequest:
    request_id: str
    connector_id: str
    collection_context: ConnectorCollectionContext
    requested_capabilities: tuple[ConnectorCapability, ...]
    requested_at: datetime
    authority_reference: str
    revision: int = 1
    version: str = INGESTION_VERSION
    contract_type: str = field(default=INGESTION_REQUEST_CONTRACT_TYPE, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _text(self.request_id, "request_id"))
        object.__setattr__(
            self, "connector_id", _text(self.connector_id, "connector_id")
        )
        object.__setattr__(
            self,
            "authority_reference",
            _text(self.authority_reference, "authority_reference"),
        )
        object.__setattr__(self, "version", _text(self.version, "version"))
        if not isinstance(self.collection_context, ConnectorCollectionContext):
            raise TypeError("collection_context must be ConnectorCollectionContext")
        object.__setattr__(
            self, "requested_at", utc_timestamp(self.requested_at, "requested_at")
        )
        capabilities = tuple(
            sorted(tuple(self.requested_capabilities), key=lambda item: str(item))
        )
        if len(set(capabilities)) != len(capabilities):
            raise ValueError("requested_capabilities must contain unique values")
        object.__setattr__(self, "requested_capabilities", capabilities)

    def validate(self) -> ValidationReport:
        issues = _base_issues(self, "request_id", "ingestion-request")
        if not _identity(self.connector_id, "connector"):
            issues.append(
                ValidationIssue(
                    "invalid_connector_reference",
                    "connector_id must be canonical",
                    "$.connector_id",
                )
            )
        if not self.requested_capabilities:
            issues.append(
                ValidationIssue(
                    "missing_capabilities",
                    "requested_capabilities is required",
                    "$.requested_capabilities",
                )
            )
        elif any(
            not isinstance(item, ConnectorCapability)
            for item in self.requested_capabilities
        ):
            issues.append(
                ValidationIssue(
                    "invalid_capability",
                    "requested capabilities must be recognized",
                    "$.requested_capabilities",
                )
            )
        for issue in self.collection_context.validate().issues:
            issues.append(
                ValidationIssue(
                    issue.code,
                    issue.message,
                    f"$.collection_context{issue.path[1:]}",
                )
            )
        if self.connector_id != self.collection_context.connector_id:
            issues.append(
                ValidationIssue(
                    "connector_mismatch",
                    "connector_id must match collection_context.connector_id",
                    "$.connector_id",
                )
            )
        if self.requested_capabilities != self.collection_context.requested_capabilities:
            issues.append(
                ValidationIssue(
                    "capabilities_mismatch",
                    "requested_capabilities must match the collection context",
                    "$.requested_capabilities",
                )
            )
        if self.requested_at != self.collection_context.requested_at:
            issues.append(
                ValidationIssue(
                    "requested_at_mismatch",
                    "requested_at must match the collection context",
                    "$.requested_at",
                )
            )
        if self.authority_reference != self.collection_context.authority_reference:
            issues.append(
                ValidationIssue(
                    "authority_mismatch",
                    "authority_reference must match the collection context",
                    "$.authority_reference",
                )
            )
        return ValidationReport(tuple(issues))


@dataclass(frozen=True, slots=True)
class IngestionError:
    error_id: str
    category: IngestionErrorCategory
    message: str
    occurred_at: datetime
    authority_reference: str
    retryable: bool = False
    revision: int = 1
    version: str = INGESTION_VERSION
    contract_type: str = field(default=INGESTION_ERROR_CONTRACT_TYPE, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "error_id", _text(self.error_id, "error_id"))
        object.__setattr__(self, "message", _text(self.message, "message"))
        object.__setattr__(
            self,
            "authority_reference",
            _text(self.authority_reference, "authority_reference"),
        )
        object.__setattr__(self, "version", _text(self.version, "version"))
        object.__setattr__(
            self, "occurred_at", utc_timestamp(self.occurred_at, "occurred_at")
        )
        if not isinstance(self.retryable, bool):
            raise TypeError("retryable must be a bool")

    def validate(self) -> ValidationReport:
        issues = _base_issues(self, "error_id", "ingestion-error")
        if not isinstance(self.category, IngestionErrorCategory):
            issues.append(
                ValidationIssue(
                    "invalid_error_category",
                    "category is not recognized",
                    "$.category",
                )
            )
        if not self.message:
            issues.append(
                ValidationIssue(
                    "missing_error_message", "message is required", "$.message"
                )
            )
        elif not is_safe_text(self.message):
            issues.append(
                ValidationIssue(
                    "unsafe_error_message",
                    "message may contain secret material",
                    "$.message",
                )
            )
        return ValidationReport(tuple(issues))


@dataclass(frozen=True, slots=True)
class IngestionResult:
    result_id: str
    request_reference: str
    collection_result_reference: str
    status: IngestionStatus
    evidence_count: int
    stored_evidence_references: tuple[str, ...]
    repository_status: RepositoryStatus
    completed_at: datetime
    authority_reference: str
    errors: tuple[IngestionError, ...] = ()
    revision: int = 1
    version: str = INGESTION_VERSION
    contract_type: str = field(default=INGESTION_RESULT_CONTRACT_TYPE, init=False)

    def __post_init__(self) -> None:
        for name in (
            "result_id",
            "request_reference",
            "collection_result_reference",
            "authority_reference",
            "version",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(
            self, "completed_at", utc_timestamp(self.completed_at, "completed_at")
        )
        references = tuple(sorted(self.stored_evidence_references))
        if len(set(references)) != len(references):
            raise ValueError("stored_evidence_references must contain unique values")
        object.__setattr__(self, "stored_evidence_references", references)
        object.__setattr__(
            self, "errors", tuple(sorted(self.errors, key=lambda item: item.error_id))
        )

    def validate(self) -> ValidationReport:
        issues = _base_issues(self, "result_id", "ingestion-result")
        for name, kind in (
            ("request_reference", "ingestion-request"),
            ("collection_result_reference", "collection-result"),
        ):
            if not _identity(getattr(self, name), kind):
                issues.append(
                    ValidationIssue(
                        f"invalid_{name}",
                        f"{name} must be a canonical reference",
                        f"$.{name}",
                    )
                )
        if not isinstance(self.status, IngestionStatus):
            issues.append(
                ValidationIssue(
                    "invalid_ingestion_status",
                    "status is not recognized",
                    "$.status",
                )
            )
        if (
            not isinstance(self.evidence_count, int)
            or isinstance(self.evidence_count, bool)
            or self.evidence_count < 0
        ):
            issues.append(
                ValidationIssue(
                    "invalid_evidence_count",
                    "evidence_count must be a non-negative integer",
                    "$.evidence_count",
                )
            )
        if self.evidence_count != len(self.stored_evidence_references):
            issues.append(
                ValidationIssue(
                    "evidence_count_mismatch",
                    "evidence_count must equal stored evidence references",
                    "$.evidence_count",
                )
            )
        if any(
            not _identity(reference, "evidence")
            for reference in self.stored_evidence_references
        ):
            issues.append(
                ValidationIssue(
                    "invalid_evidence_reference",
                    "stored evidence references must be canonical",
                    "$.stored_evidence_references",
                )
            )
        if not isinstance(self.repository_status, RepositoryStatus):
            issues.append(
                ValidationIssue(
                    "invalid_repository_status",
                    "repository_status is not recognized",
                    "$.repository_status",
                )
            )
        if self.status is IngestionStatus.SUCCEEDED and self.errors:
            issues.append(
                ValidationIssue(
                    "success_with_errors",
                    "a successful result cannot contain errors",
                    "$.errors",
                )
            )
        if self.status is not IngestionStatus.SUCCEEDED and not self.errors:
            issues.append(
                ValidationIssue(
                    "failure_without_error",
                    "a non-success result requires a governed error",
                    "$.errors",
                )
            )
        for index, error in enumerate(self.errors):
            for issue in error.validate().issues:
                issues.append(
                    ValidationIssue(
                        issue.code, issue.message, f"$.errors[{index}]{issue.path[1:]}"
                    )
                )
        return ValidationReport(tuple(issues))


def _datetime(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a timestamp string")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO 8601 timestamp") from exc


def _strict(data: Mapping[str, Any], fields: set[str], contract_type: str) -> None:
    unknown = set(data).difference(fields)
    if unknown:
        raise ValueError(f"unknown fields: {', '.join(sorted(unknown))}")
    missing = fields.difference(data)
    if missing:
        raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")
    if data["contract_type"] != contract_type:
        raise ValueError(f"contract_type must be {contract_type}")


def ingestion_request_from_dict(data: Mapping[str, Any]) -> IngestionRequest:
    fields = {
        "contract_type",
        "request_id",
        "connector_id",
        "collection_context",
        "requested_capabilities",
        "requested_at",
        "authority_reference",
        "revision",
        "version",
    }
    _strict(data, fields, INGESTION_REQUEST_CONTRACT_TYPE)
    if not isinstance(data["collection_context"], Mapping):
        raise ValueError("collection_context must be an object")
    if not isinstance(data["requested_capabilities"], (list, tuple)):
        raise ValueError("requested_capabilities must be an array")
    try:
        capabilities = tuple(
            ConnectorCapability(item) for item in data["requested_capabilities"]
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("requested_capabilities contains an unrecognized value") from exc
    return IngestionRequest(
        request_id=str(data["request_id"]),
        connector_id=str(data["connector_id"]),
        collection_context=collection_context_from_dict(data["collection_context"]),
        requested_capabilities=capabilities,
        requested_at=_datetime(data["requested_at"], "requested_at"),
        authority_reference=str(data["authority_reference"]),
        revision=data["revision"],
        version=str(data["version"]),
    )


def ingestion_error_from_dict(data: Mapping[str, Any]) -> IngestionError:
    fields = {
        "contract_type",
        "error_id",
        "category",
        "message",
        "occurred_at",
        "authority_reference",
        "retryable",
        "revision",
        "version",
    }
    _strict(data, fields, INGESTION_ERROR_CONTRACT_TYPE)
    try:
        category = IngestionErrorCategory(data["category"])
    except (TypeError, ValueError) as exc:
        raise ValueError("category is not a recognized IngestionErrorCategory") from exc
    return IngestionError(
        error_id=str(data["error_id"]),
        category=category,
        message=str(data["message"]),
        occurred_at=_datetime(data["occurred_at"], "occurred_at"),
        authority_reference=str(data["authority_reference"]),
        retryable=data["retryable"],
        revision=data["revision"],
        version=str(data["version"]),
    )


def ingestion_result_from_dict(data: Mapping[str, Any]) -> IngestionResult:
    fields = {
        "contract_type",
        "result_id",
        "request_reference",
        "collection_result_reference",
        "status",
        "evidence_count",
        "stored_evidence_references",
        "repository_status",
        "completed_at",
        "authority_reference",
        "errors",
        "revision",
        "version",
    }
    _strict(data, fields, INGESTION_RESULT_CONTRACT_TYPE)
    if not isinstance(data["stored_evidence_references"], (list, tuple)):
        raise ValueError("stored_evidence_references must be an array")
    if not isinstance(data["errors"], (list, tuple)):
        raise ValueError("errors must be an array")
    try:
        status = IngestionStatus(data["status"])
        repository_status = RepositoryStatus(data["repository_status"])
    except (TypeError, ValueError) as exc:
        raise ValueError("result status is not recognized") from exc
    return IngestionResult(
        result_id=str(data["result_id"]),
        request_reference=str(data["request_reference"]),
        collection_result_reference=str(data["collection_result_reference"]),
        status=status,
        evidence_count=data["evidence_count"],
        stored_evidence_references=tuple(
            str(item) for item in data["stored_evidence_references"]
        ),
        repository_status=repository_status,
        completed_at=_datetime(data["completed_at"], "completed_at"),
        authority_reference=str(data["authority_reference"]),
        errors=tuple(ingestion_error_from_dict(item) for item in data["errors"]),
        revision=data["revision"],
        version=str(data["version"]),
    )


def ingestion_request_to_dict(value: IngestionRequest) -> dict[str, Any]:
    return contract_to_dict(value)


def ingestion_request_to_json(
    value: IngestionRequest, *, indent: int | None = None
) -> str:
    return contract_to_json(value, indent=indent)


def ingestion_error_to_dict(value: IngestionError) -> dict[str, Any]:
    return contract_to_dict(value)


def ingestion_error_to_json(
    value: IngestionError, *, indent: int | None = None
) -> str:
    return contract_to_json(value, indent=indent)


def ingestion_result_to_dict(value: IngestionResult) -> dict[str, Any]:
    return contract_to_dict(value)


def ingestion_result_to_json(
    value: IngestionResult, *, indent: int | None = None
) -> str:
    return contract_to_json(value, indent=indent)


def _from_json(
    payload: str | bytes | bytearray, loader: Any, label: str
) -> IngestionRequest | IngestionError | IngestionResult:
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError(f"{label} JSON must be an object")
    return loader(data)


def ingestion_request_from_json(
    payload: str | bytes | bytearray,
) -> IngestionRequest:
    return _from_json(payload, ingestion_request_from_dict, "Ingestion Request")


def ingestion_error_from_json(payload: str | bytes | bytearray) -> IngestionError:
    return _from_json(payload, ingestion_error_from_dict, "Ingestion Error")


def ingestion_result_from_json(payload: str | bytes | bytearray) -> IngestionResult:
    return _from_json(payload, ingestion_result_from_dict, "Ingestion Result")
