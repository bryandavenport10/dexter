"""Deterministic correlation rules for governed evidence."""
from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from .contracts.evidence import Evidence
from .contracts.evidence_correlation import CorrelationType, EvidenceCorrelation
from .serialization import contract_to_json


class CorrelationEngine:
    """Produce correlations from exact pairwise rules.

    Same-source compares source identifiers; temporal proximity compares the
    absolute observation-time distance to the supplied inclusive window; state
    change and contradiction require the same source with unequal payloads;
    support requires the same source with equal payloads; related resource
    requires an exact shared relationship identifier. A matching rule has
    confidence 1.0; a non-match produces no correlation.
    """

    def __init__(self, *, authority_reference: str) -> None:
        if not isinstance(authority_reference, str) or not authority_reference.strip():
            raise ValueError("authority_reference is required")
        self.authority_reference = authority_reference.strip()

    def same_source_object(self, primary: Evidence, related: Evidence) -> EvidenceCorrelation | None:
        return self._correlate(primary, related, CorrelationType.SAME_SOURCE_OBJECT, primary.source_object == related.source_object, f"identical source object: {primary.source_object}")

    def temporal_proximity(self, primary: Evidence, related: Evidence, *, time_window: timedelta) -> EvidenceCorrelation | None:
        if not isinstance(time_window, timedelta) or time_window < timedelta(0):
            raise ValueError("time_window must be a non-negative timedelta")
        distance = abs(primary.observation_timestamp - related.observation_timestamp)
        return self._correlate(primary, related, CorrelationType.TEMPORAL_PROXIMITY, distance <= time_window, f"observation timestamps within supplied window of {time_window.total_seconds():g} seconds")

    def state_change(self, primary: Evidence, related: Evidence) -> EvidenceCorrelation | None:
        return self._correlate(primary, related, CorrelationType.STATE_CHANGE, primary.source_object == related.source_object and primary.payload != related.payload, f"payload state changed for source object: {primary.source_object}")

    def supported_by(self, primary: Evidence, related: Evidence) -> EvidenceCorrelation | None:
        return self._correlate(primary, related, CorrelationType.SUPPORTED_BY, primary.source_object == related.source_object and primary.payload == related.payload, f"identical payload reinforces source object: {primary.source_object}")

    def contradicted_by(self, primary: Evidence, related: Evidence) -> EvidenceCorrelation | None:
        return self._correlate(primary, related, CorrelationType.CONTRADICTED_BY, primary.source_object == related.source_object and primary.payload != related.payload, f"different payload conflicts for source object: {primary.source_object}")

    def related_resource(self, primary: Evidence, related: Evidence) -> EvidenceCorrelation | None:
        shared = tuple(sorted(set(primary.relationships).intersection(related.relationships)))
        return self._correlate(primary, related, CorrelationType.RELATED_RESOURCE, bool(shared), "shared explicit relationship identifiers: " + ", ".join(shared), relationship_references=shared)

    def correlate(self, primary: Evidence, related: Evidence, correlation_type: CorrelationType, *, time_window: timedelta | None = None) -> EvidenceCorrelation | None:
        rules: dict[CorrelationType, Callable[[], EvidenceCorrelation | None]] = {
            CorrelationType.SAME_SOURCE_OBJECT: lambda: self.same_source_object(primary, related),
            CorrelationType.TEMPORAL_PROXIMITY: lambda: self.temporal_proximity(primary, related, time_window=_required_window(time_window)),
            CorrelationType.STATE_CHANGE: lambda: self.state_change(primary, related),
            CorrelationType.SUPPORTED_BY: lambda: self.supported_by(primary, related),
            CorrelationType.CONTRADICTED_BY: lambda: self.contradicted_by(primary, related),
            CorrelationType.RELATED_RESOURCE: lambda: self.related_resource(primary, related),
        }
        if not isinstance(correlation_type, CorrelationType) or correlation_type is CorrelationType.UNKNOWN:
            raise ValueError("correlation_type must be recognized and cannot be UNKNOWN")
        return rules[correlation_type]()

    def _correlate(self, primary: Evidence, related: Evidence, correlation_type: CorrelationType, matches: bool, basis: str, *, relationship_references: tuple[str, ...] = ()) -> EvidenceCorrelation | None:
        _valid_evidence(primary, "primary")
        _valid_evidence(related, "related")
        if primary.evidence_id == related.evidence_id:
            raise ValueError("primary and related evidence must be distinct")
        if not matches:
            return None
        material: dict[str, Any] = {
            "authority_reference": self.authority_reference, "basis": basis,
            "correlation_type": correlation_type.value,
            "evidence_references": (primary.evidence_id, related.evidence_id),
            "relationship_references": relationship_references,
        }
        value = EvidenceCorrelation(
            correlation_id=f"dexter:correlation:{uuid5(NAMESPACE_URL, contract_to_json(material))}",
            correlation_type=correlation_type, primary_evidence_reference=primary.evidence_id,
            related_evidence_references=(related.evidence_id,), correlation_basis=basis,
            confidence=1.0, correlated_at=max(primary.collection_timestamp, related.collection_timestamp),
            authority_reference=self.authority_reference,
            evidence_references=(primary.evidence_id, related.evidence_id),
            relationship_references=relationship_references,
        )
        value.validate().raise_for_errors()
        return value


def _valid_evidence(value: Evidence, name: str) -> None:
    if not isinstance(value, Evidence):
        raise TypeError(f"{name} must be Evidence")
    if not value.validate().is_valid:
        raise ValueError(f"{name} evidence must validate")


def _required_window(value: timedelta | None) -> timedelta:
    if value is None:
        raise ValueError("time_window is required for temporal proximity")
    return value
