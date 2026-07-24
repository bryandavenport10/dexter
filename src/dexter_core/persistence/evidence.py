"""Immutable PostgreSQL persistence for connector-produced Evidence."""
from __future__ import annotations
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Protocol, runtime_checkable
from ..contracts.evidence import Evidence, EvidenceType, evidence_from_json, evidence_to_json
from ..contracts.ingestion import RepositoryStatus
from ..contracts.observation import utc_timestamp

class EvidenceRepositoryError(RuntimeError):
    """Base class for evidence repository failures."""

class DuplicateEvidenceError(EvidenceRepositoryError):
    """Raised when an immutable Evidence identity already exists."""

@dataclass(frozen=True, slots=True)
class RepositoryHealth:
    status: RepositoryStatus
    detail: str | None = None
    @property
    def is_healthy(self) -> bool:
        return self.status is RepositoryStatus.HEALTHY

@runtime_checkable
class EvidenceRepository(Protocol):
    """Storage boundary for immutable, governed Evidence."""
    def store(self, evidence: Evidence) -> None: ...
    def get_by_identity(self, evidence_id: str) -> Evidence | None: ...
    def get_by_source(self, source_system: str, source_object: str | None = None) -> tuple[Evidence, ...]: ...
    def get_by_time_window(self, start: datetime, end: datetime) -> tuple[Evidence, ...]: ...
    def get_by_type(self, evidence_type: EvidenceType) -> tuple[Evidence, ...]: ...
    def get_by_relationship(self, relationship: str) -> tuple[Evidence, ...]: ...
    def health(self) -> RepositoryHealth: ...

class _Cursor(Protocol):
    def execute(self, query: str, params: tuple[Any, ...] = ()) -> Any: ...
    def fetchone(self) -> tuple[Any, ...] | None: ...
    def fetchall(self) -> list[tuple[Any, ...]]: ...
    def __enter__(self) -> "_Cursor": ...
    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...

class _Connection(Protocol):
    def cursor(self) -> _Cursor: ...
    def __enter__(self) -> "_Connection": ...
    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...

ConnectionFactory = Callable[[], AbstractContextManager[_Connection]]
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS dexter_evidence (
    evidence_id TEXT PRIMARY KEY,
    evidence_type TEXT NOT NULL,
    source_system TEXT NOT NULL,
    source_object TEXT NOT NULL,
    observation_timestamp TIMESTAMPTZ NOT NULL,
    collection_timestamp TIMESTAMPTZ NOT NULL,
    relationships TEXT[] NOT NULL,
    version TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision > 0),
    evidence_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS dexter_evidence_source_idx
    ON dexter_evidence (source_system, source_object, observation_timestamp, evidence_id);
CREATE INDEX IF NOT EXISTS dexter_evidence_time_idx
    ON dexter_evidence (observation_timestamp, evidence_id);
CREATE INDEX IF NOT EXISTS dexter_evidence_type_idx
    ON dexter_evidence (evidence_type, observation_timestamp, evidence_id);
CREATE INDEX IF NOT EXISTS dexter_evidence_relationships_idx
    ON dexter_evidence USING GIN (relationships);
""".strip()
_SELECT = "SELECT evidence_json FROM dexter_evidence"
_ORDER = " ORDER BY observation_timestamp ASC, evidence_id ASC"

class PostgreSQLEvidenceRepository:
    """PostgreSQL repository retaining canonical Evidence JSON without mutation."""
    def __init__(self, connection_factory: ConnectionFactory) -> None:
        if not callable(connection_factory):
            raise TypeError("connection_factory must be callable")
        self._connection_factory = connection_factory

    def initialize_schema(self) -> None:
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(SCHEMA_SQL)

    def store(self, evidence: Evidence) -> None:
        if not isinstance(evidence, Evidence):
            raise TypeError("evidence must be Evidence")
        evidence.validate().raise_for_errors()
        payload = evidence_to_json(evidence)
        try:
            with self._connection_factory() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("""INSERT INTO dexter_evidence (
                        evidence_id, evidence_type, source_system, source_object,
                        observation_timestamp, collection_timestamp, relationships,
                        version, revision, evidence_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (evidence.evidence_id, evidence.evidence_type.value, evidence.source_system,
                     evidence.source_object, evidence.observation_timestamp,
                     evidence.collection_timestamp, list(evidence.relationships), evidence.version,
                     evidence.revision, payload))
        except Exception as exc:
            if _sqlstate(exc) == "23505":
                raise DuplicateEvidenceError(f"evidence identity already exists: {evidence.evidence_id}") from exc
            raise

    def get_by_identity(self, evidence_id: str) -> Evidence | None:
        rows = self._query(f"{_SELECT} WHERE evidence_id = %s", (_required_text(evidence_id, "evidence_id"),))
        return rows[0] if rows else None

    def get_by_source(self, source_system: str, source_object: str | None = None) -> tuple[Evidence, ...]:
        source = _required_text(source_system, "source_system")
        if source_object is None:
            return self._query(f"{_SELECT} WHERE source_system = %s{_ORDER}", (source,))
        return self._query(f"{_SELECT} WHERE source_system = %s AND source_object = %s{_ORDER}",
                           (source, _required_text(source_object, "source_object")))

    def get_by_time_window(self, start: datetime, end: datetime) -> tuple[Evidence, ...]:
        beginning, ending = utc_timestamp(start, "start"), utc_timestamp(end, "end")
        if ending < beginning:
            raise ValueError("end cannot precede start")
        return self._query(f"{_SELECT} WHERE observation_timestamp >= %s AND observation_timestamp <= %s{_ORDER}",
                           (beginning, ending))

    def get_by_type(self, evidence_type: EvidenceType) -> tuple[Evidence, ...]:
        if not isinstance(evidence_type, EvidenceType):
            raise TypeError("evidence_type must be EvidenceType")
        return self._query(f"{_SELECT} WHERE evidence_type = %s{_ORDER}", (evidence_type.value,))

    def get_by_relationship(self, relationship: str) -> tuple[Evidence, ...]:
        return self._query(f"{_SELECT} WHERE relationships @> %s::text[]{_ORDER}",
                           ([_required_text(relationship, "relationship")],))

    def health(self) -> RepositoryHealth:
        try:
            with self._connection_factory() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    row = cursor.fetchone()
            if row != (1,):
                return RepositoryHealth(RepositoryStatus.UNAVAILABLE, "unexpected health response")
        except Exception as exc:
            return RepositoryHealth(RepositoryStatus.UNAVAILABLE, str(exc))
        return RepositoryHealth(RepositoryStatus.HEALTHY)

    def _query(self, sql: str, params: tuple[Any, ...]) -> tuple[Evidence, ...]:
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
        return tuple(evidence_from_json(row[0]) for row in rows)

def _required_text(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} is required")
    return normalized

def _sqlstate(exc: BaseException) -> str | None:
    current: BaseException | None = exc
    while current is not None:
        state = getattr(current, "sqlstate", None) or getattr(current, "pgcode", None)
        if state:
            return str(state)
        current = current.__cause__
    return None
