from __future__ import annotations

from enum import Enum


class StringEnum(str, Enum):
    """A JSON-friendly string enumeration."""

    def __str__(self) -> str:
        return self.value


class LifecycleState(StringEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class OperationalStatus(StringEnum):
    UNKNOWN = "unknown"
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class AuthorityKind(StringEnum):
    PERSON = "person"
    ORGANIZATION = "organization"
    SYSTEM = "system"


class RelationshipKind(StringEnum):
    DEPENDS_ON = "depends_on"
    DERIVED_FROM = "derived_from"
    PART_OF = "part_of"
    RELATED_TO = "related_to"
    SUPERSEDES = "supersedes"

