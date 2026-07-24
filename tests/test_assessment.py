import json
import unittest
from datetime import datetime, timedelta, timezone

from dexter_core import AssessmentEngine
from dexter_core.contracts import Assessment, AssessmentConfidence, AssessmentType, CorrelationType, EvidenceCorrelation, assessment_from_dict, assessment_from_json, assessment_to_dict, assessment_to_json

NOW = datetime(2026, 7, 24, 4, 35, tzinfo=timezone.utc)


def correlation(suffix: str, basis: str, *, kind: CorrelationType = CorrelationType.SUPPORTED_BY, confidence: float = 1.0) -> EvidenceCorrelation:
    primary = f"dexter:evidence:123e4567-e89b-12d3-a456-4266141741{suffix}"
    related = f"dexter:evidence:123e4567-e89b-12d3-a456-4266141742{suffix}"
    return EvidenceCorrelation(
        correlation_id=f"dexter:correlation:123e4567-e89b-12d3-a456-4266141740{suffix}", correlation_type=kind,
        primary_evidence_reference=primary, related_evidence_references=(related,), correlation_basis=basis,
        confidence=confidence, correlated_at=NOW + timedelta(seconds=int(suffix)), authority_reference="dexter:authority:correlation-engine",
        evidence_references=(primary, related), relationship_references=("proxmox:cluster:lab",),
    )


class AssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = AssessmentEngine(authority_reference="dexter:authority:assessment-engine")

    def test_all_assessment_rules(self) -> None:
        cases = (
            (("CPU pressure", "memory pressure"), AssessmentType.RESOURCE_UTILIZATION),
            (("storage capacity", "disk support"), AssessmentType.CAPACITY),
            (("network connectivity", "network support"), AssessmentType.CONNECTIVITY),
            (("configuration changed", "config support"), AssessmentType.CONFIGURATION_CHANGE),
            (("service degraded", "service failure"), AssessmentType.SERVICE_DEGRADATION),
        )
        for bases, expected in cases:
            with self.subTest(expected):
                value = self.engine.assess(tuple(correlation(f"{index:02d}", basis) for index, basis in enumerate(bases)))
                self.assertEqual(value.assessment_type, expected)
        state = self.engine.assess((correlation("00", "power state", kind=CorrelationType.STATE_CHANGE), correlation("01", "support")))
        self.assertEqual(state.assessment_type, AssessmentType.STATE_TRANSITION)

    def test_missing_invalid_and_unmatched_correlations(self) -> None:
        with self.assertRaisesRegex(ValueError, "supporting correlation"):
            self.engine.assess((correlation("00", "storage"),))
        with self.assertRaisesRegex(ValueError, "implemented assessment rule"):
            self.engine.assess((correlation("00", "temperature"), correlation("01", "fan speed")))
        invalid = correlation("00", "storage", confidence=2.0)
        with self.assertRaisesRegex(ValueError, "must validate"):
            self.engine.assess((invalid, correlation("01", "storage")))

    def test_unknown_confidence_and_type_never_validate(self) -> None:
        self.assertIn("invalid_confidence", self._codes(self._record(confidence=AssessmentConfidence.UNKNOWN)))
        self.assertIn("invalid_assessment_type", self._codes(self._record(assessment_type=AssessmentType.UNKNOWN)))

    def test_serialization_round_trip_strict_fields_and_utc(self) -> None:
        value = self.engine.assess((correlation("00", "storage"), correlation("01", "disk capacity")))
        data = assessment_to_dict(value)
        self.assertEqual(assessment_from_dict(data), value)
        payload = assessment_to_json(value)
        self.assertEqual(assessment_to_json(assessment_from_json(payload)), payload)
        self.assertEqual(json.loads(payload)["assessed_at"], "2026-07-24T04:35:01Z")
        data["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            assessment_from_dict(data)

    def test_validation_rules(self) -> None:
        cases = (({"assessment_id": "bad"}, "invalid_assessment_identity"), ({"primary_correlation_reference": ""}, "missing_primary_correlation"), ({"supporting_correlation_references": ()}, "missing_supporting_correlations"), ({"assessment_statement": ""}, "missing_assessment_statement"), ({"assessment_basis": ""}, "missing_assessment_basis"), ({"authority_reference": ""}, "missing_authority_reference"), ({"revision": 0}, "invalid_revision"), ({"version": "2.0"}, "unsupported_version"))
        for changes, expected in cases:
            with self.subTest(expected):
                self.assertIn(expected, self._codes(self._record(**changes)))

    def test_deterministic_repeatability_lineage_and_confidence(self) -> None:
        inputs = (correlation("00", "CPU pressure"), correlation("01", "memory pressure"))
        first = self.engine.assess(inputs)
        second = AssessmentEngine(authority_reference="dexter:authority:assessment-engine").assess(inputs)
        self.assertEqual(first, second)
        self.assertEqual(assessment_to_json(first), assessment_to_json(second))
        self.assertEqual(first.supporting_correlation_references, (inputs[1].correlation_id,))
        for item in inputs:
            self.assertIn(item.correlation_id, first.assessment_basis)
            for evidence in item.evidence_references:
                self.assertIn(evidence, first.assessment_basis)
        expected = {2: AssessmentConfidence.LOW, 3: AssessmentConfidence.MEDIUM, 4: AssessmentConfidence.HIGH, 5: AssessmentConfidence.CERTAIN}
        for count, confidence in expected.items():
            values = tuple(correlation(f"{index:02d}", "storage capacity") for index in range(count))
            self.assertEqual(self.engine.assess(values).confidence, confidence)
        values = tuple(correlation(f"{index:02d}", "storage capacity", confidence=0.9) for index in range(5))
        self.assertEqual(self.engine.assess(values).confidence, AssessmentConfidence.HIGH)

    @staticmethod
    def _codes(value: Assessment) -> set[str]:
        return {issue.code for issue in value.validate().issues}

    def _record(self, **changes: object) -> Assessment:
        values: dict[str, object] = {"assessment_id": "dexter:assessment:123e4567-e89b-12d3-a456-426614174000", "assessment_type": AssessmentType.CAPACITY, "primary_correlation_reference": "dexter:correlation:primary", "supporting_correlation_references": ("dexter:correlation:supporting",), "assessment_statement": "Storage capacity conditions exist.", "assessment_basis": "Rule CAPACITY and evidence support this assessment.", "confidence": AssessmentConfidence.LOW, "assessed_at": NOW, "authority_reference": "dexter:authority:assessment-engine", "evidence_references": ("dexter:evidence:one", "dexter:evidence:two")}
        values.update(changes)
        return Assessment(**values)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
