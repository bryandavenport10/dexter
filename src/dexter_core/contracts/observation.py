"""Normalized, immutable observations collected from operational sources."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping

from ..enums import StringEnum


class ObservationType(StringEnum):
    CLUSTER = "CLUSTER"
    NODE = "NODE"
    VIRTUAL_MACHINE = "VIRTUAL_MACHINE"
    CONTAINER = "CONTAINER"
    STORAGE = "STORAGE"
    TASK = "TASK"


def utc_timestamp(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def immutable_value(value: Any) -> Any:
    """Copy JSON-shaped data into an immutable, deterministic representation."""
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): immutable_value(value[key]) for key in sorted(value, key=str)})
    if isinstance(value, (list, tuple)):
        return tuple(immutable_value(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError("payload values must be JSON-compatible")


@dataclass(frozen=True, slots=True)
class ProxmoxObservation:
    """A normalized observation; raw Proxmox JSON never crosses this boundary."""

    observation_type: ObservationType
    source_object: str
    observed_at: datetime
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.observation_type, ObservationType):
            raise TypeError("observation_type must be an ObservationType")
        if not isinstance(self.source_object, str) or not self.source_object.strip():
            raise ValueError("source_object is required")
        object.__setattr__(self, "source_object", self.source_object.strip())
        object.__setattr__(self, "observed_at", utc_timestamp(self.observed_at, "observed_at"))
        if not isinstance(self.payload, Mapping):
            raise TypeError("payload must be a mapping")
        object.__setattr__(self, "payload", immutable_value(self.payload))
