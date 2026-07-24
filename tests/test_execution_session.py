import json
import unittest
from datetime import datetime, timedelta, timezone
from dexter_core import EvidenceReference, RelationshipKind, RelationshipReference
from dexter_core.contracts import ExecutionSession, ExecutionSessionState, execution_session_from_dict, execution_session_from_json, execution_session_to_dict, execution_session_to_json

STARTED_AT = datetime(2026, 7, 24, 0, 35, tzinfo=timezone.utc)
ENDED_AT = datetime(2026, 7, 24, 0, 40, tzinfo=timezone.utc)
SESSION_ID = "dexter:execution-session:123e4567-e89b-12d3-a456-426614174010"
def session(**changes: object) -> ExecutionSession:
    values: dict[str, object] = {"session_id": SESSION_ID, "execution_attempt_id": "dexter:execution-attempt:123e4567-e89b-12d3-a456-426614174000", "provider_assignment_id": "dexter:provider-assignment:123e4567-e89b-12d3-a456-426614174009", "lease_id": "dexter:lease:123e4567-e89b-12d3-a456-426614174001", "worker_id": "dexter:worker:worker-1", "provider_id": "dexter:provider:provider-1", "state": ExecutionSessionState.CREATED, "session_started_at": STARTED_AT, "authority_reference": "dexter:authority:governance", "evidence_references": (EvidenceReference("https://example.test/evidence", "application/json"),), "relationship_references": (RelationshipReference("dexter:execution-attempt:123e4567-e89b-12d3-a456-426614174000", RelationshipKind.RELATED_TO),)}
    values.update(changes)
    return ExecutionSession(**values)  # type: ignore[arg-type]

class ExecutionSessionTests(unittest.TestCase):
    def test_valid_session(self) -> None: self.assertTrue(session().validate().is_valid)
    def test_required_values(self) -> None:
        for field, code in (("session_id", "missing_session_identity"), ("execution_attempt_id", "missing_execution_attempt_reference"), ("provider_assignment_id", "missing_provider_assignment_reference"), ("lease_id", "missing_lease_reference"), ("worker_id", "missing_worker_identity"), ("provider_id", "missing_provider_identity"), ("authority_reference", "missing_authority_reference")):
            with self.subTest(field=field): self.assertEqual(session(**{field: ""}).validate().issues[0].code, code)
    def test_invalid_and_unknown_states(self) -> None:
        self.assertEqual(session(state="PAUSED").validate().issues[0].code, "invalid_state")
        self.assertEqual(session(state=ExecutionSessionState.UNKNOWN).validate().issues[0].code, "unknown_state")
        data = execution_session_to_dict(session()); data["state"] = "PAUSED"
        with self.assertRaisesRegex(ValueError, "ExecutionSessionState"): execution_session_from_dict(data)
    def test_ended_before_started(self) -> None:
        self.assertEqual(session(session_ended_at=STARTED_AT - timedelta(seconds=1)).validate().issues[0].code, "session_ended_before_started")
    def test_revision_and_version(self) -> None:
        self.assertEqual(session(revision=0).validate().issues[0].code, "invalid_revision")
        self.assertEqual(session(revision=True).validate().issues[0].code, "invalid_revision")
        self.assertEqual(session(version="2.0").validate().issues[0].code, "unsupported_version")
    def test_timestamp_requirements_and_normalization(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware"): session(session_started_at=datetime(2026, 7, 24, 0, 35))
        with self.assertRaisesRegex(ValueError, "timezone-aware"): session(session_ended_at=datetime(2026, 7, 24, 0, 40))
        value = session(session_started_at=datetime(2026, 7, 23, 20, 35, tzinfo=timezone(timedelta(hours=-4))), session_ended_at=datetime(2026, 7, 23, 20, 40, tzinfo=timezone(timedelta(hours=-4))))
        self.assertEqual((value.session_started_at, value.session_ended_at), (STARTED_AT, ENDED_AT))
    def test_dictionary_and_json_round_trips(self) -> None:
        value = session(state=ExecutionSessionState.COMPLETED, session_ended_at=ENDED_AT, revision=2)
        self.assertEqual(execution_session_from_dict(execution_session_to_dict(value)), value)
        payload = execution_session_to_json(value)
        self.assertEqual(execution_session_to_json(execution_session_from_json(payload)), payload)
        encoded = json.loads(payload)
        self.assertEqual((encoded["session_started_at"], encoded["session_ended_at"]), ("2026-07-24T00:35:00Z", "2026-07-24T00:40:00Z"))
    def test_validation_failures_raise(self) -> None:
        report = session(execution_attempt_id="", provider_assignment_id="", lease_id="", worker_id="", provider_id="", authority_reference="").validate()
        self.assertEqual(len(report.issues), 6)
        with self.assertRaises(ValueError): report.raise_for_errors()
    def test_repository_compatibility_and_strict_fields(self) -> None:
        data = execution_session_to_dict(session())
        self.assertEqual((data["contract_type"], data["state"], data["execution_attempt_id"]), ("dexter.execution_session", "CREATED", "dexter:execution-attempt:123e4567-e89b-12d3-a456-426614174000"))
        self.assertEqual(data["relationship_references"][0]["kind"], "related_to")
        data["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "unknown fields"): execution_session_from_dict(data)
    def test_missing_wire_field(self) -> None:
        data = execution_session_to_dict(session()); del data["authority_reference"]
        with self.assertRaisesRegex(ValueError, "missing required fields"): execution_session_from_dict(data)
    def test_all_supported_states_except_unknown_validate(self) -> None:
        for state in (ExecutionSessionState.CREATED, ExecutionSessionState.STARTING, ExecutionSessionState.RUNNING, ExecutionSessionState.COMPLETED, ExecutionSessionState.FAILED, ExecutionSessionState.CANCELLED):
            with self.subTest(state=state): self.assertTrue(session(state=state).validate().is_valid)

if __name__ == "__main__": unittest.main()
