import json
import unittest
from datetime import datetime, timedelta, timezone
from dexter_core import EvidenceReference, RelationshipKind, RelationshipReference
from dexter_core.contracts import RuntimeEvent, RuntimeEventType, runtime_event_from_dict, runtime_event_from_json, runtime_event_to_dict, runtime_event_to_json

OBSERVED_AT = datetime(2026, 7, 24, 0, 35, tzinfo=timezone.utc)
EVENT_ID = "dexter:runtime-event:123e4567-e89b-12d3-a456-426614174010"
def event(**changes: object) -> RuntimeEvent:
    values: dict[str, object] = {"event_id": EVENT_ID, "execution_session_id": "dexter:execution-session:123e4567-e89b-12d3-a456-426614174010", "execution_attempt_id": "dexter:execution-attempt:123e4567-e89b-12d3-a456-426614174000", "provider_assignment_id": "dexter:provider-assignment:123e4567-e89b-12d3-a456-426614174009", "lease_id": "dexter:lease:123e4567-e89b-12d3-a456-426614174001", "worker_id": "dexter:worker:worker-1", "provider_id": "dexter:provider:provider-1", "event_type": RuntimeEventType.STARTED, "observed_at": OBSERVED_AT, "authority_reference": "dexter:authority:governance", "evidence_references": (EvidenceReference("https://example.test/evidence", "application/json"),), "relationship_references": (RelationshipReference("dexter:execution-attempt:123e4567-e89b-12d3-a456-426614174000", RelationshipKind.RELATED_TO),)}
    values.update(changes)
    return RuntimeEvent(**values)  # type: ignore[arg-type]

class RuntimeEventTests(unittest.TestCase):
    def test_valid_event(self) -> None: self.assertTrue(event().validate().is_valid)
    def test_required_values(self) -> None:
        for field, code in (("event_id", "missing_event_identity"), ("execution_session_id", "missing_execution_session_reference"), ("execution_attempt_id", "missing_execution_attempt_reference"), ("provider_assignment_id", "missing_provider_assignment_reference"), ("lease_id", "missing_lease_reference"), ("worker_id", "missing_worker_identity"), ("provider_id", "missing_provider_identity"), ("authority_reference", "missing_authority_reference")):
            with self.subTest(field=field): self.assertEqual(event(**{field: ""}).validate().issues[0].code, code)
    def test_invalid_and_unknown_event_types(self) -> None:
        self.assertEqual(event(event_type="NOTICE").validate().issues[0].code, "invalid_event_type")
        self.assertEqual(event(event_type=RuntimeEventType.UNKNOWN).validate().issues[0].code, "unknown_event_type")
        data = runtime_event_to_dict(event()); data["event_type"] = "NOTICE"
        with self.assertRaisesRegex(ValueError, "RuntimeEventType"): runtime_event_from_dict(data)
    def test_revision_and_version(self) -> None:
        self.assertEqual(event(revision=0).validate().issues[0].code, "invalid_revision")
        self.assertEqual(event(revision=True).validate().issues[0].code, "invalid_revision")
        self.assertEqual(event(version="2.0").validate().issues[0].code, "unsupported_version")
    def test_timestamp_requirements_and_normalization(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware"): event(observed_at=datetime(2026, 7, 24, 0, 35))
        value = event(observed_at=datetime(2026, 7, 23, 20, 35, tzinfo=timezone(timedelta(hours=-4))))
        self.assertEqual(value.observed_at, OBSERVED_AT)
    def test_dictionary_and_json_round_trips(self) -> None:
        value = event(event_type=RuntimeEventType.COMPLETED, revision=2)
        self.assertEqual(runtime_event_from_dict(runtime_event_to_dict(value)), value)
        payload = runtime_event_to_json(value)
        self.assertEqual(runtime_event_to_json(runtime_event_from_json(payload)), payload)
        self.assertEqual(json.loads(payload)["observed_at"], "2026-07-24T00:35:00Z")
    def test_validation_failures_raise(self) -> None:
        report = event(execution_session_id="", execution_attempt_id="", provider_assignment_id="", lease_id="", worker_id="", provider_id="", authority_reference="").validate()
        self.assertEqual(len(report.issues), 7)
        with self.assertRaises(ValueError): report.raise_for_errors()
    def test_repository_compatibility_and_strict_fields(self) -> None:
        data = runtime_event_to_dict(event())
        self.assertEqual((data["contract_type"], data["event_type"], data["execution_attempt_id"]), ("dexter.runtime_event", "STARTED", "dexter:execution-attempt:123e4567-e89b-12d3-a456-426614174000"))
        self.assertEqual(data["relationship_references"][0]["kind"], "related_to")
        data["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "unknown fields"): runtime_event_from_dict(data)
    def test_missing_wire_field(self) -> None:
        data = runtime_event_to_dict(event()); del data["authority_reference"]
        with self.assertRaisesRegex(ValueError, "missing required fields"): runtime_event_from_dict(data)
    def test_all_supported_event_types_except_unknown_validate(self) -> None:
        for event_type in (RuntimeEventType.STARTED, RuntimeEventType.HEARTBEAT, RuntimeEventType.PROGRESS, RuntimeEventType.WARNING, RuntimeEventType.PAUSED, RuntimeEventType.RESUMED, RuntimeEventType.STDOUT, RuntimeEventType.STDERR, RuntimeEventType.COMPLETED, RuntimeEventType.FAILED, RuntimeEventType.CANCELLED):
            with self.subTest(event_type=event_type): self.assertTrue(event(event_type=event_type).validate().is_valid)

if __name__ == "__main__": unittest.main()
