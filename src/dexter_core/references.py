from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.parse import urlparse

from .enums import AuthorityKind, RelationshipKind


def _required(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _uri(value: str, field_name: str) -> str:
    normalized = _required(value, field_name)
    parsed = urlparse(normalized)
    if not parsed.scheme:
        raise ValueError(f"{field_name} must be an absolute URI")
    return normalized


def _timestamp(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class Authority:
    identifier: str
    name: str
    kind: AuthorityKind
    asserted_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "identifier", _required(self.identifier, "identifier"))
        object.__setattr__(self, "name", _required(self.name, "name"))
        object.__setattr__(self, "asserted_at", _timestamp(self.asserted_at, "asserted_at"))


@dataclass(frozen=True, slots=True)
class ProvenanceReference:
    uri: str
    recorded_at: datetime
    description: str | None = None
    digest: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "uri", _uri(self.uri, "uri"))
        object.__setattr__(self, "recorded_at", _timestamp(self.recorded_at, "recorded_at"))
        if self.description is not None:
            object.__setattr__(self, "description", _required(self.description, "description"))
        if self.digest is not None:
            object.__setattr__(self, "digest", _required(self.digest, "digest"))


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    uri: str
    media_type: str
    description: str | None = None
    digest: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "uri", _uri(self.uri, "uri"))
        object.__setattr__(self, "media_type", _required(self.media_type, "media_type"))
        if self.description is not None:
            object.__setattr__(self, "description", _required(self.description, "description"))
        if self.digest is not None:
            object.__setattr__(self, "digest", _required(self.digest, "digest"))


@dataclass(frozen=True, slots=True)
class RelationshipReference:
    target_entity_id: str
    kind: RelationshipKind
    attributes: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_entity_id", _required(self.target_entity_id, "target_entity_id"))
        if self.attributes is not None:
            object.__setattr__(self, "attributes", dict(self.attributes))

