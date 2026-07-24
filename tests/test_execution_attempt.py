import json
import unittest
from datetime import datetime, timedelta, timezone
from dexter_core import EvidenceReference, RelationshipKind, RelationshipReference
from dexter_core.contracts import ExecutionAttempt, ExecutionAttemptState, execution_attempt_from_dict, execution_attempt_from_json, execution_attempt_to_dict, execution_attempt_to_json

AT = datetime(2026, 7, 23, 23, 35, tzinfo=timezone.utc)
ID = "dexter:execution-attempt:123e4567-e89b-12d3-a456-426614174000"
def attempt(**changes: object) -> ExecutionAttempt:
    values: dict[str, object] = {"attempt_id": ID, "lease_id": "dexter:lease:123e4567-e89b-12d3-a456-426614174001", "worker_id": "dexter:worker:worker-1", "provider_id": "dexter:provider:provider-1", "provider_assignment_id": "dexter:provider-assignment:123e4567-e89b-12d3-a456-426614174009", "state": ExecutionAttemptState.CREATED, "attempt_timestamp": AT, "authority_reference": "dexter:authority:governance", "evidence_references": (EvidenceReference("https://example.test/evidence", "application/json"),), "relationship_references": (RelationshipReference("dexter:lease:123e4567-e89b-12d3-a456-426614174001", RelationshipKind.RELATED_TO),)}
    values.update(changes)
    return ExecutionAttempt(**values)  # type: ignore[arg-type]

class ExecutionAttemptTests(unittest.TestCase):
    def test_valid_attempt(self) -> None: self.assertTrue(attempt().validate().is_valid)
    def test_required_values(self) -> None:
        for field, code in (("attempt_id", "missing_attempt_identity"), ("provider_assignment_id", "missing_provider_assignment_reference"), ("lease_id", "missing_lease_reference"), ("worker_id", "missing_worker_identity"), ("provider_id", "missing_provider_identity"), ("authority_reference", "missing_authority_reference")):
            with self.subTest(field=field): self.assertEqual(attempt(**{field: ""}).validate().issues[0].code, code)
    def test_invalid_and_unknown_states(self) -> None:
        self.assertEqual(attempt(state="RUNNING").validate().issues[0].code, "invalid_state")
        self.assertEqual(attempt(state=ExecutionAttemptState.UNKNOWN).validate().issues[0].code, "unknown_state")
        data = execution_attempt_to_dict(attempt()); data["state"] = "RUNNING"
        with self.assertRaisesRegex(ValueError, "ExecutionAttemptState"): execution_attempt_from_dict(data)
    def test_revision_and_version(self) -> None:
        self.assertEqual(attempt(revision=0).validate().issues[0].code, "invalid_revision")
        self.assertEqual(attempt(revision=True).validate().issues[0].code, "invalid_revision")
        self.assertEqual(attempt(version="2.0").validate().issues[0].code, "unsupported_version")
    def test_timestamp_requirement_and_normalization(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware"): attempt(attempt_timestamp=datetime(2026, 7, 23, 23, 35))
        value = attempt(attempt_timestamp=datetime(2026, 7, 23, 19, 35, tzinfo=timezone(timedelta(hours=-4))))
        self.assertEqual(value.attempt_timestamp, AT)
    def test_dictionary_and_json_round_trips(self) -> None:
        value = attempt(state=ExecutionAttemptState.AUTHORIZED, revision=2)
        self.assertEqual(execution_attempt_from_dict(execution_attempt_to_dict(value)), value)
        payload = execution_attempt_to_json(value)
        self.assertEqual(execution_attempt_to_json(execution_attempt_from_json(payload)), payload)
        self.assertEqual(json.loads(payload)["attempt_timestamp"], "2026-07-23T23:35:00Z")
    def test_validation_failures_raise(self) -> None:
        report = attempt(provider_assignment_id="", lease_id="", worker_id="", provider_id="", authority_reference="").validate()
        self.assertEqual(len(report.issues), 5)
        with self.assertRaises(ValueError): report.raise_for_errors()
    def test_repository_compatibility_and_strict_fields(self) -> None:
        data = execution_attempt_to_dict(attempt())
        self.assertEqual((data["contract_type"], data["state"], data["provider_assignment_id"]), ("dexter.execution_attempt", "CREATED", "dexter:provider-assignment:123e4567-e89b-12d3-a456-426614174009"))
        self.assertEqual(data["relationship_references"][0]["kind"], "related_to")
        data["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "unknown fields"): execution_attempt_from_dict(data)
    def test_missing_wire_field(self) -> None:
        data = execution_attempt_to_dict(attempt()); del data["authority_reference"]
        with self.assertRaisesRegex(ValueError, "missing required fields"): execution_attempt_from_dict(data)

if __name__ == "__main__": unittest.main()
