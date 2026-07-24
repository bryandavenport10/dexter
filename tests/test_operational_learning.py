import json
import unittest
from datetime import datetime, timedelta, timezone
from dexter_core import EvidenceReference, RelationshipKind, RelationshipReference
from dexter_core.contracts import LearningDisposition, OperationalLearningRecord, operational_learning_record_from_dict, operational_learning_record_from_json, operational_learning_record_to_dict, operational_learning_record_to_json

RECORDED_AT = datetime(2026, 7, 24, 2, 25, tzinfo=timezone.utc)
LEARNING_ID = "dexter:operational-learning:123e4567-e89b-12d3-a456-426614174012"
def learning(**changes: object) -> OperationalLearningRecord:
    values: dict[str, object] = {"learning_id": LEARNING_ID, "outcome_record_id": "dexter:outcome:123e4567-e89b-12d3-a456-426614174011", "execution_verification_id": "dexter:execution-verification:123e4567-e89b-12d3-a456-426614174010", "execution_session_id": "dexter:execution-session:123e4567-e89b-12d3-a456-426614174010", "execution_attempt_id": "dexter:execution-attempt:123e4567-e89b-12d3-a456-426614174000", "provider_assignment_id": "dexter:provider-assignment:123e4567-e89b-12d3-a456-426614174009", "lease_id": "dexter:lease:123e4567-e89b-12d3-a456-426614174001", "worker_id": "dexter:worker:worker-1", "provider_id": "dexter:provider:provider-1", "disposition": LearningDisposition.LEARNED, "recorded_at": RECORDED_AT, "authority_reference": "dexter:authority:governance", "evidence_references": (EvidenceReference("https://example.test/verified-outcome", "application/json"),), "relationship_references": (RelationshipReference("dexter:outcome:123e4567-e89b-12d3-a456-426614174011", RelationshipKind.DERIVED_FROM),)}
    values.update(changes)
    return OperationalLearningRecord(**values)  # type: ignore[arg-type]

class OperationalLearningRecordTests(unittest.TestCase):
    def test_valid_learning_record(self) -> None: self.assertTrue(learning().validate().is_valid)
    def test_required_references_and_identities(self) -> None:
        for field, code in (("learning_id", "missing_learning_identity"), ("outcome_record_id", "missing_outcome_record_reference"), ("execution_verification_id", "missing_execution_verification_reference"), ("execution_session_id", "missing_execution_session_reference"), ("execution_attempt_id", "missing_execution_attempt_reference"), ("provider_assignment_id", "missing_provider_assignment_reference"), ("lease_id", "missing_lease_reference"), ("worker_id", "missing_worker_identity"), ("provider_id", "missing_provider_identity"), ("authority_reference", "missing_authority_reference")):
            with self.subTest(field=field): self.assertEqual(learning(**{field: ""}).validate().issues[0].code, code)
    def test_invalid_and_unknown_dispositions(self) -> None:
        self.assertEqual(learning(disposition="OBSERVED").validate().issues[0].code, "invalid_learning_disposition")
        self.assertEqual(learning(disposition=LearningDisposition.UNKNOWN).validate().issues[0].code, "unknown_learning_disposition")
        data = operational_learning_record_to_dict(learning()); data["disposition"] = "OBSERVED"
        with self.assertRaisesRegex(ValueError, "LearningDisposition"): operational_learning_record_from_dict(data)
    def test_revision_version_and_identity_validation(self) -> None:
        self.assertEqual(learning(revision=0).validate().issues[0].code, "invalid_revision")
        self.assertEqual(learning(revision=True).validate().issues[0].code, "invalid_revision")
        self.assertEqual(learning(version="2.0").validate().issues[0].code, "unsupported_version")
        self.assertEqual(learning(learning_id="dexter:operational-learning:not-a-uuid").validate().issues[0].code, "invalid_learning_identity")
    def test_timestamp_requirements_and_normalization(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware"): learning(recorded_at=datetime(2026, 7, 24, 2, 25))
        value = learning(recorded_at=datetime(2026, 7, 23, 22, 25, tzinfo=timezone(timedelta(hours=-4))))
        self.assertEqual(value.recorded_at, RECORDED_AT)
    def test_dictionary_and_json_round_trips(self) -> None:
        value = learning(disposition=LearningDisposition.NO_CHANGE, revision=2)
        self.assertEqual(operational_learning_record_from_dict(operational_learning_record_to_dict(value)), value)
        payload = operational_learning_record_to_json(value)
        self.assertEqual(operational_learning_record_to_json(operational_learning_record_from_json(payload)), payload)
        self.assertEqual(json.loads(payload)["recorded_at"], "2026-07-24T02:25:00Z")
    def test_validation_failures_raise(self) -> None:
        report = learning(outcome_record_id="", execution_verification_id="", execution_session_id="", execution_attempt_id="", provider_assignment_id="", lease_id="", worker_id="", provider_id="", authority_reference="").validate()
        self.assertEqual(len(report.issues), 9)
        with self.assertRaises(ValueError): report.raise_for_errors()
    def test_repository_compatibility_and_strict_fields(self) -> None:
        data = operational_learning_record_to_dict(learning())
        self.assertEqual((data["contract_type"], data["disposition"], data["outcome_record_id"]), ("dexter.operational_learning_record", "LEARNED", "dexter:outcome:123e4567-e89b-12d3-a456-426614174011"))
        self.assertEqual(data["relationship_references"][0]["kind"], "derived_from")
        data["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "unknown fields"): operational_learning_record_from_dict(data)
    def test_missing_wire_field_and_non_object_json(self) -> None:
        data = operational_learning_record_to_dict(learning()); del data["authority_reference"]
        with self.assertRaisesRegex(ValueError, "missing required fields"): operational_learning_record_from_dict(data)
        with self.assertRaisesRegex(ValueError, "must be an object"): operational_learning_record_from_json("[]")
    def test_all_supported_dispositions_except_unknown_validate(self) -> None:
        for disposition in (LearningDisposition.LEARNED, LearningDisposition.NO_CHANGE, LearningDisposition.REQUIRES_REVIEW, LearningDisposition.REJECTED):
            with self.subTest(disposition=disposition): self.assertTrue(learning(disposition=disposition).validate().is_valid)

if __name__ == "__main__": unittest.main()
