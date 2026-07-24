import json
import unittest
from datetime import datetime, timedelta, timezone

from dexter_core import CorrelationEngine
from dexter_core.contracts import (
    CorrelationType, Evidence, EvidenceCorrelation, EvidenceType, SourceAuthority,
    evidence_correlation_from_dict, evidence_correlation_from_json,
    evidence_correlation_to_dict, evidence_correlation_to_json,
)

NOW = datetime(2026, 7, 24, 3, 50, tzinfo=timezone.utc)


def evidence(suffix: str, *, source_object: str = "node/pve1", seconds: int = 0, payload: dict[str, object] | None = None, relationships: tuple[str, ...] = ("proxmox:cluster:lab",)) -> Evidence:
    return Evidence(
        evidence_id=f"dexter:evidence:123e4567-e89b-12d3-a456-4266141740{suffix}",
        evidence_type=EvidenceType.PROXMOX_NODE, source_system="proxmox-ve",
        source_object=source_object, observation_timestamp=NOW + timedelta(seconds=seconds),
        collection_timestamp=NOW + timedelta(seconds=seconds),
        authority=SourceAuthority("lab", "pve1", "https://pve.test/api2/json", "proxmox-ve-api:get", "collector", NOW),
        payload=payload or {"status": "online"}, relationships=relationships,
    )


class EvidenceCorrelationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CorrelationEngine(authority_reference="dexter:authority:correlation-engine")
        self.primary, self.related = evidence("00"), evidence("01")

    def test_same_source_object(self) -> None:
        value = self.engine.same_source_object(self.primary, self.related)
        self.assertEqual(value.correlation_type, CorrelationType.SAME_SOURCE_OBJECT)  # type: ignore[union-attr]
        self.assertIn("node/pve1", value.correlation_basis)  # type: ignore[union-attr]
        self.assertIsNone(self.engine.same_source_object(self.primary, evidence("02", source_object="node/pve2")))

    def test_temporal_proximity_and_outside_window(self) -> None:
        self.assertIsNotNone(self.engine.temporal_proximity(self.primary, evidence("02", seconds=30), time_window=timedelta(seconds=30)))
        self.assertIsNone(self.engine.temporal_proximity(self.primary, evidence("03", seconds=31), time_window=timedelta(seconds=30)))
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self.engine.temporal_proximity(self.primary, self.related, time_window=timedelta(seconds=-1))

    def test_state_change(self) -> None:
        changed = evidence("02", payload={"status": "offline"})
        self.assertEqual(self.engine.state_change(self.primary, changed).correlation_type, CorrelationType.STATE_CHANGE)  # type: ignore[union-attr]
        self.assertIsNone(self.engine.state_change(self.primary, self.related))

    def test_supported_by(self) -> None:
        self.assertEqual(self.engine.supported_by(self.primary, self.related).correlation_type, CorrelationType.SUPPORTED_BY)  # type: ignore[union-attr]
        self.assertIsNone(self.engine.supported_by(self.primary, evidence("02", payload={"status": "offline"})))

    def test_contradicted_by(self) -> None:
        changed = evidence("02", payload={"status": "offline"})
        self.assertEqual(self.engine.contradicted_by(self.primary, changed).correlation_type, CorrelationType.CONTRADICTED_BY)  # type: ignore[union-attr]
        self.assertIsNone(self.engine.contradicted_by(self.primary, self.related))

    def test_related_resource(self) -> None:
        related = evidence("02", source_object="node/pve1/vm/100", relationships=("proxmox:cluster:lab", "proxmox:node:pve1"))
        value = self.engine.related_resource(self.primary, related)
        self.assertEqual(value.relationship_references, ("proxmox:cluster:lab",))  # type: ignore[union-attr]
        self.assertIsNone(self.engine.related_resource(self.primary, evidence("03", relationships=("other:resource",))))

    def test_duplicate_evidence_rejection(self) -> None:
        with self.assertRaisesRegex(ValueError, "distinct"):
            self.engine.same_source_object(self.primary, self.primary)
        value = self._record(related_evidence_references=(self.related.evidence_id, self.related.evidence_id), evidence_references=(self.primary.evidence_id, self.related.evidence_id, self.related.evidence_id))
        self.assertIn("duplicate_evidence", {issue.code for issue in value.validate().issues})

    def test_invalid_confidence_and_type(self) -> None:
        self.assertEqual(self._record(confidence=1.1).validate().issues[0].code, "invalid_confidence")
        self.assertEqual(self._record(correlation_type=CorrelationType.UNKNOWN).validate().issues[0].code, "invalid_correlation_type")
        with self.assertRaisesRegex(ValueError, "cannot be UNKNOWN"):
            self.engine.correlate(self.primary, self.related, CorrelationType.UNKNOWN)

    def test_serialization_round_trip_strict_fields_and_utc(self) -> None:
        value = self.engine.same_source_object(self.primary, self.related)
        data = evidence_correlation_to_dict(value)
        self.assertEqual(evidence_correlation_from_dict(data), value)
        payload = evidence_correlation_to_json(value)
        self.assertEqual(evidence_correlation_to_json(evidence_correlation_from_json(payload)), payload)
        self.assertEqual(json.loads(payload)["correlated_at"], "2026-07-24T03:50:00Z")
        data["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            evidence_correlation_from_dict(data)

    def test_validation_failures(self) -> None:
        cases = (
            ({"correlation_id": "bad"}, "invalid_correlation_identity"),
            ({"primary_evidence_reference": ""}, "missing_primary_evidence"),
            ({"related_evidence_references": ()}, "missing_related_evidence"),
            ({"correlation_basis": ""}, "missing_correlation_basis"),
            ({"authority_reference": ""}, "missing_authority_reference"),
            ({"revision": 0}, "invalid_revision"), ({"version": "2.0"}, "unsupported_version"),
        )
        for changes, expected in cases:
            with self.subTest(expected):
                self.assertIn(expected, {issue.code for issue in self._record(**changes).validate().issues})

    def test_repository_compatibility_and_deterministic_repeatability(self) -> None:
        first = self.engine.correlate(self.primary, self.related, CorrelationType.SAME_SOURCE_OBJECT)
        second = CorrelationEngine(authority_reference="dexter:authority:correlation-engine").correlate(self.primary, self.related, CorrelationType.SAME_SOURCE_OBJECT)
        self.assertEqual(first, second)
        self.assertEqual(evidence_correlation_to_json(first), evidence_correlation_to_json(second))
        self.assertEqual(first.confidence, 1.0)  # type: ignore[union-attr]
        self.assertEqual(first.evidence_references, (self.primary.evidence_id, self.related.evidence_id))  # type: ignore[union-attr]

    def _record(self, **changes: object) -> EvidenceCorrelation:
        values: dict[str, object] = {
            "correlation_id": "dexter:correlation:123e4567-e89b-12d3-a456-426614174000",
            "correlation_type": CorrelationType.SAME_SOURCE_OBJECT,
            "primary_evidence_reference": self.primary.evidence_id,
            "related_evidence_references": (self.related.evidence_id,),
            "correlation_basis": "identical source object: node/pve1", "confidence": 1.0,
            "correlated_at": NOW, "authority_reference": "dexter:authority:correlation-engine",
            "evidence_references": (self.primary.evidence_id, self.related.evidence_id),
        }
        values.update(changes)
        return EvidenceCorrelation(**values)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
