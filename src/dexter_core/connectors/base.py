"""Behavior boundary for dependency-injected, read-only connectors."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..contracts.connector import (
    ConnectorCollectionContext,
    ConnectorCollectionResult,
    ConnectorMetadata,
    ConnectorStatusRecord,
)


@runtime_checkable
class Connector(Protocol):
    """Reusable connector interface; contracts contain no transport behavior."""

    @property
    def metadata(self) -> ConnectorMetadata: ...

    def collect(self, context: ConnectorCollectionContext) -> ConnectorCollectionResult: ...

    def health(self, context: ConnectorCollectionContext) -> ConnectorStatusRecord: ...
