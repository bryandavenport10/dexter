from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any, Mapping

from .entity import GovernedEntity
from .enums import AuthorityKind, LifecycleState, OperationalStatus, RelationshipKind
from .references import Authority, EvidenceReference, ProvenanceReference, RelationshipReference


def contract_to_dict(contract: Any) -> dict[str, Any]:
    """Encode a dataclass contract using Dexter canonical JSON values."""
    encoded = _encode(contract)
    if not isinstance(encoded, dict):
        raise TypeError("contract must encode to an object")
    return encoded


def contract_to_json(contract: Any, *, indent: int | None = None) -> str:
    """Serialize a contract deterministically using Dexter canonical JSON."""
    return json.dumps(contract_to_dict(contract), indent=indent, sort_keys=True, separators=None if indent else (",", ":"))


def _encode(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {key: _encode(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_encode(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return {name: _encode(getattr(value, name)) for name in value.__dataclass_fields__}
    return value


def entity_to_dict(entity: GovernedEntity) -> dict[str, Any]:
    return contract_to_dict(entity)


def entity_to_json(entity: GovernedEntity, *, indent: int | None = None) -> str:
    return contract_to_json(entity, indent=indent)


def _datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def entity_from_dict(data: Mapping[str, Any]) -> GovernedEntity:
    required = {"entity_type", "name", "authority"}
    missing = required.difference(data)
    if missing:
        raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")
    authority = data["authority"]
    if not isinstance(authority, Mapping):
        raise ValueError("authority must be an object")
    kwargs: dict[str, Any] = dict(data)
    kwargs["authority"] = Authority(
        identifier=str(authority["identifier"]), name=str(authority["name"]),
        kind=AuthorityKind(authority["kind"]), asserted_at=_datetime(str(authority["asserted_at"])),
    )
    kwargs["lifecycle_state"] = LifecycleState(data.get("lifecycle_state", LifecycleState.DRAFT))
    kwargs["operational_status"] = OperationalStatus(data.get("operational_status", OperationalStatus.UNKNOWN))
    kwargs["provenance"] = tuple(ProvenanceReference(uri=str(x["uri"]), recorded_at=_datetime(str(x["recorded_at"])), description=x.get("description"), digest=x.get("digest")) for x in data.get("provenance", ()))
    kwargs["evidence"] = tuple(EvidenceReference(uri=str(x["uri"]), media_type=str(x["media_type"]), description=x.get("description"), digest=x.get("digest")) for x in data.get("evidence", ()))
    kwargs["relationships"] = tuple(RelationshipReference(target_entity_id=str(x["target_entity_id"]), kind=RelationshipKind(x["kind"]), attributes=x.get("attributes")) for x in data.get("relationships", ()))
    if "created_at" in data:
        kwargs["created_at"] = _datetime(str(data["created_at"]))
    if "updated_at" in data:
        kwargs["updated_at"] = _datetime(str(data["updated_at"]))
    return GovernedEntity(**kwargs)


def entity_from_json(payload: str | bytes | bytearray) -> GovernedEntity:
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("entity JSON must be an object")
    return entity_from_dict(data)

