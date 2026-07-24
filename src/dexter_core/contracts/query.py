"""Read-only query request and response contracts."""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID
from ..serialization import contract_to_dict, contract_to_json
from ..validation import ValidationIssue, ValidationReport
from .observation import utc_timestamp

QUERY_REQUEST_CONTRACT_TYPE = "dexter.query-request"
QUERY_RESPONSE_CONTRACT_TYPE = "dexter.query-response"
QUERY_VERSION = "1.0"


class QueryType(str, Enum):
    EVIDENCE = "EVIDENCE"
    ASSESSMENT = "ASSESSMENT"
    QUESTION = "QUESTION"
    ANSWER = "ANSWER"
    STATUS = "STATUS"
    UNKNOWN = "UNKNOWN"


_RESOURCES = {
    QueryType.EVIDENCE: "evidence",
    QueryType.ASSESSMENT: "assessments",
    QueryType.QUESTION: "questions",
    QueryType.ANSWER: "answers",
    QueryType.STATUS: "status",
}


def _id(v: str, k: str) -> bool:
    try:
        UUID(v.removeprefix(f"dexter:{k}:"))
        return v.startswith(f"dexter:{k}:")
    except (ValueError, AttributeError):
        return False


def _text(v: Any, n: str) -> str:
    if not isinstance(v, str):
        raise TypeError(f"{n} must be a string")
    if not v.strip():
        raise ValueError(f"{n} is required")
    return v.strip()


def _base(v: Any, id_name: str, kind: str) -> list[ValidationIssue]:
    issues = []
    if not _id(getattr(v, id_name), kind):
        issues.append(
            ValidationIssue(
                f"invalid_{id_name}", f"{id_name} must be canonical", f"$.{id_name}"
            )
        )
    if not v.authority_reference:
        issues.append(
            ValidationIssue(
                "missing_authority_reference",
                "authority_reference is required",
                "$.authority_reference",
            )
        )
    if (
        not isinstance(v.revision, int)
        or isinstance(v.revision, bool)
        or v.revision < 1
    ):
        issues.append(
            ValidationIssue(
                "invalid_revision", "revision must be positive", "$.revision"
            )
        )
    if v.version != QUERY_VERSION:
        issues.append(
            ValidationIssue(
                "unsupported_version", f"expected {QUERY_VERSION}", "$.version"
            )
        )
    return issues


@dataclass(frozen=True, slots=True)
class QueryRequest:
    request_id: str
    query_type: QueryType
    requested_resource: str
    requested_at: datetime
    authority_reference: str
    revision: int = 1
    version: str = QUERY_VERSION
    contract_type: str = field(default=QUERY_REQUEST_CONTRACT_TYPE, init=False)

    def __post_init__(self):
        for n in ("request_id", "requested_resource", "authority_reference", "version"):
            object.__setattr__(self, n, _text(getattr(self, n), n))
        object.__setattr__(
            self, "requested_at", utc_timestamp(self.requested_at, "requested_at")
        )

    def validate(self) -> ValidationReport:
        i = _base(self, "request_id", "query-request")
        if (
            not isinstance(self.query_type, QueryType)
            or self.query_type is QueryType.UNKNOWN
        ):
            i.append(
                ValidationIssue(
                    "invalid_query_type",
                    "query_type must be recognized and cannot be UNKNOWN",
                    "$.query_type",
                )
            )
        parts = self.requested_resource.strip("/").split("/")
        root = parts[0]
        identity_allowed = self.query_type in (QueryType.EVIDENCE, QueryType.ASSESSMENT)
        recognized = (
            _RESOURCES.get(self.query_type) == root
            and len(parts) <= 2
            and (len(parts) == 1 or (identity_allowed and bool(parts[1])))
        )
        if not recognized:
            i.append(
                ValidationIssue(
                    "unrecognized_resource",
                    "requested_resource does not match a recognized query endpoint",
                    "$.requested_resource",
                )
            )
        return ValidationReport(tuple(i))


@dataclass(frozen=True, slots=True)
class QueryResponse:
    response_id: str
    request_reference: str
    responded_at: datetime
    result_count: int
    returned_objects: tuple[Mapping[str, Any], ...]
    authority_reference: str
    revision: int = 1
    version: str = QUERY_VERSION
    contract_type: str = field(default=QUERY_RESPONSE_CONTRACT_TYPE, init=False)

    def __post_init__(self):
        for n in ("response_id", "request_reference", "authority_reference", "version"):
            object.__setattr__(self, n, _text(getattr(self, n), n))
        object.__setattr__(
            self, "responded_at", utc_timestamp(self.responded_at, "responded_at")
        )
        object.__setattr__(
            self,
            "returned_objects",
            tuple(MappingProxyType(dict(x)) for x in self.returned_objects),
        )

    def validate(self) -> ValidationReport:
        i = _base(self, "response_id", "query-response")
        if not _id(self.request_reference, "query-request"):
            i.append(
                ValidationIssue(
                    "invalid_request_reference",
                    "request_reference must be canonical",
                    "$.request_reference",
                )
            )
        if (
            not isinstance(self.result_count, int)
            or isinstance(self.result_count, bool)
            or self.result_count < 0
        ):
            i.append(
                ValidationIssue(
                    "invalid_result_count",
                    "result_count must be non-negative",
                    "$.result_count",
                )
            )
        elif self.result_count != len(self.returned_objects):
            i.append(
                ValidationIssue(
                    "result_count_mismatch",
                    "result_count must equal returned_objects",
                    "$.result_count",
                )
            )
        return ValidationReport(tuple(i))


def query_request_to_dict(v):
    return contract_to_dict(v)


def query_request_to_json(v, *, indent=None):
    return contract_to_json(v, indent=indent)


def query_response_to_dict(v):
    return contract_to_dict(v)


def query_response_to_json(v, *, indent=None):
    return contract_to_json(v, indent=indent)


def _strict(d, f):
    if set(d) - f:
        raise ValueError(f"unknown fields: {', '.join(sorted(set(d)-f))}")
    if f - set(d):
        raise ValueError(f"missing required fields: {', '.join(sorted(f-set(d)))}")


def _dt(v, n):
    if not isinstance(v, str):
        raise ValueError(f"{n} must be a timestamp string")
    return datetime.fromisoformat(v.replace("Z", "+00:00"))


def query_request_from_dict(d):
    f = {
        "contract_type",
        "request_id",
        "query_type",
        "requested_resource",
        "requested_at",
        "authority_reference",
        "revision",
        "version",
    }
    _strict(d, f)
    if d["contract_type"] != QUERY_REQUEST_CONTRACT_TYPE:
        raise ValueError("invalid contract_type")
    return QueryRequest(
        str(d["request_id"]),
        QueryType(d["query_type"]),
        str(d["requested_resource"]),
        _dt(d["requested_at"], "requested_at"),
        str(d["authority_reference"]),
        d["revision"],
        str(d["version"]),
    )


def query_response_from_dict(d):
    f = {
        "contract_type",
        "response_id",
        "request_reference",
        "responded_at",
        "result_count",
        "returned_objects",
        "authority_reference",
        "revision",
        "version",
    }
    _strict(d, f)
    if d["contract_type"] != QUERY_RESPONSE_CONTRACT_TYPE or not isinstance(
        d["returned_objects"], list
    ):
        raise ValueError("invalid query response")
    return QueryResponse(
        str(d["response_id"]),
        str(d["request_reference"]),
        _dt(d["responded_at"], "responded_at"),
        d["result_count"],
        tuple(d["returned_objects"]),
        str(d["authority_reference"]),
        d["revision"],
        str(d["version"]),
    )


def query_request_from_json(p):
    return query_request_from_dict(json.loads(p))


def query_response_from_json(p):
    return query_response_from_dict(json.loads(p))
