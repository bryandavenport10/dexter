import json
import unittest
from datetime import datetime, timedelta, timezone
from dexter_core import EvidenceReference, RelationshipKind, RelationshipReference
from dexter_core.contracts import OutcomeRecord, OutcomeResult, outcome_record_from_dict, outcome_record_from_json, outcome_record_to_dict, outcome_record_to_json

RECORDED_AT = datetime(2026, 7, 24, 0, 35, tzinfo=timezone.utc)
OUTCOME_ID = "dexter:outcome:123e4567-e89b-12d3-a456-426614174011"
def outcome(**changes: object) -> OutcomeRecord:
    values: dict[str, object] = {"outcome_id": OUTCOME_ID, "execution_verification_id": "dexter:execution-verification:123e4567-e89b-12d3-a456-426614174010", "execution_session_id": "dexter:execution-session:123e4567-e89b-12d3-a456-426614174010", "execution_attempt_id": "dexter:execution-attempt:123e4567-e89b-12d3-a456-426614174000", "provider_assignment_id": "dexter:provider-assignment:123e4567-e89b-12d3-a456-426614174009", "lease_id": "dexter:lease:123e4567-e89b-12d3-a456-426614174001", "worker_id": "dexter:worker:worker-1", "provider_id": "dexter:provider:provider-1", "result": OutcomeResult.PARTIAL_SUCCESS, "recorded_at": RECORDED_AT, "authority_reference": "dexter:authority:governance", "evidence_references": (EvidenceReference("https://example.test/evidence", "application/json"),), "relationship_references": (RelationshipReference("dexter:execution-attempt:123e4567-e89b-12d3-a456-426614174000", RelationshipKind.RELATED_TO),)}
    values.update(changes)
    return OutcomeRecord(**values)  # type: ignore[arg-type]

class OutcomeRecordTests(unittest.TestCase):
    def test_valid_outcome(self) -> None: self.assertTrue(outcome().validate().is_valid)
    def test_required_values(self) -> None:
        for field, code in (("outcome_id", "missing_outcome_identity"), ("execution_verification_id", "missing_execution_verification_reference"), ("execution_session_id", "missing_execution_session_reference"), ("execution_attempt_id", "missing_execution_attempt_reference"), ("provider_assignment_id", "missing_provider_assignment_reference"), ("lease_id", "missing_lease_reference"), ("worker_id", "missing_worker_identity"), ("provider_id", "missing_provider_identity"), ("authority_reference", "missing_authority_reference")):
            with self.subTest(field=field): self.assertEqual(outcome(**{field: ""}).validate().issues[0].code, code)
    def test_invalid_and_unknown_results(self) -> None:
        self.assertEqual(outcome(result="NOTICE").validate().issues[0].code, "invalid_outcome_result")
        self.assertEqual(outcome(result=OutcomeResult.UNKNOWN).validate().issues[0].code, "unknown_outcome_result")
        data = outcome_record_to_dict(outcome()); data["result"] = "NOTICE"
        with self.assertRaisesRegex(ValueError, "OutcomeResult"): outcome_record_from_dict(data)
    def test_revision_and_version(self) -> None:
        self.assertEqual(outcome(revision=0).validate().issues[0].code, "invalid_revision")
        self.assertEqual(outcome(revision=True).validate().issues[0].code, "invalid_revision")
        self.assertEqual(outcome(version="2.0").validate().issues[0].code, "unsupported_version")
    def test_timestamp_requirements_and_normalization(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware"): outcome(recorded_at=datetime(2026, 7, 24, 0, 35))
        value = outcome(recorded_at=datetime(2026, 7, 23, 20, 35, tzinfo=timezone(timedelta(hours=-4))))
        self.assertEqual(value.recorded_at, RECORDED_AT)
    def test_dictionary_and_json_round_trips(self) -> None:
        value = outcome(result=OutcomeResult.PARTIAL_SUCCESS, revision=2)
        self.assertEqual(outcome_record_from_dict(outcome_record_to_dict(value)), value)
        payload = outcome_record_to_json(value)
        self.assertEqual(outcome_record_to_json(outcome_record_from_json(payload)), payload)
        self.assertEqual(json.loads(payload)["recorded_at"], "2026-07-24T00:35:00Z")
    def test_validation_failures_raise(self) -> None:
        report = outcome(execution_verification_id="", execution_session_id="", execution_attempt_id="", provider_assignment_id="", lease_id="", worker_id="", provider_id="", authority_reference="").validate()
        self.assertEqual(len(report.issues), 8)
        with self.assertRaises(ValueError): report.raise_for_errors()
    def test_repository_compatibility_and_strict_fields(self) -> None:
        data = outcome_record_to_dict(outcome())
        self.assertEqual((data["contract_type"], data["result"], data["execution_attempt_id"]), ("dexter.outcome_record", "PARTIAL_SUCCESS", "dexter:execution-attempt:123e4567-e89b-12d3-a456-426614174000"))
        self.assertEqual(data["relationship_references"][0]["kind"], "related_to")
        data["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "unknown fields"): outcome_record_from_dict(data)
    def test_missing_wire_field(self) -> None:
        data = outcome_record_to_dict(outcome()); del data["authority_reference"]
        with self.assertRaisesRegex(ValueError, "missing required fields"): outcome_record_from_dict(data)
    def test_all_supported_results_except_unknown_validate(self) -> None:
        for result in (OutcomeResult.SUCCESS, OutcomeResult.PARTIAL_SUCCESS, OutcomeResult.FAILURE, OutcomeResult.CANCELLED, OutcomeResult.INCONCLUSIVE):
            with self.subTest(result=result): self.assertTrue(outcome(result=result).validate().is_valid)

if __name__ == "__main__": unittest.main()
