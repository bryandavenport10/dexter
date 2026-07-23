import json
import unittest
from datetime import datetime, timedelta, timezone
from dexter_core import EvidenceReference, RelationshipKind, RelationshipReference
from dexter_core.contracts import ProviderAssignment, ProviderAssignmentState, provider_assignment_from_dict, provider_assignment_from_json, provider_assignment_to_dict, provider_assignment_to_json

AT = datetime(2026, 7, 23, 23, 35, tzinfo=timezone.utc)
ID = "dexter:provider-assignment:123e4567-e89b-12d3-a456-426614174000"
def assignment(**changes: object) -> ProviderAssignment:
    values: dict[str, object] = {"assignment_id": ID, "lease_id": "dexter:lease:123e4567-e89b-12d3-a456-426614174001", "worker_id": "dexter:worker:worker-1", "provider_id": "dexter:provider:provider-1", "provider_capability": "text.generation", "state": ProviderAssignmentState.ASSIGNED, "assigned_at": AT, "authority_reference": "dexter:authority:governance", "evidence_references": (EvidenceReference("https://example.test/evidence", "application/json"),), "relationship_references": (RelationshipReference("dexter:lease:123e4567-e89b-12d3-a456-426614174001", RelationshipKind.RELATED_TO),)}
    values.update(changes)
    return ProviderAssignment(**values)  # type: ignore[arg-type]

class ProviderAssignmentTests(unittest.TestCase):
    def test_valid_assignment(self) -> None: self.assertTrue(assignment().validate().is_valid)
    def test_required_values(self) -> None:
        for field, code in (("assignment_id", "missing_assignment_identity"), ("lease_id", "missing_lease_reference"), ("worker_id", "missing_worker_identity"), ("provider_id", "missing_provider_identity"), ("provider_capability", "missing_provider_capability"), ("authority_reference", "missing_authority_reference")):
            with self.subTest(field=field): self.assertEqual(assignment(**{field: ""}).validate().issues[0].code, code)
    def test_invalid_and_unknown_states(self) -> None:
        self.assertEqual(assignment(state="RUNNING").validate().issues[0].code, "invalid_state")
        self.assertEqual(assignment(state=ProviderAssignmentState.UNKNOWN).validate().issues[0].code, "unknown_state")
        data = provider_assignment_to_dict(assignment()); data["state"] = "RUNNING"
        with self.assertRaisesRegex(ValueError, "ProviderAssignmentState"): provider_assignment_from_dict(data)
    def test_revision_and_version(self) -> None:
        self.assertEqual(assignment(revision=0).validate().issues[0].code, "invalid_revision")
        self.assertEqual(assignment(revision=True).validate().issues[0].code, "invalid_revision")
        self.assertEqual(assignment(version="2.0").validate().issues[0].code, "unsupported_version")
    def test_timestamp_requirement_and_normalization(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware"): assignment(assigned_at=datetime(2026, 7, 23, 23, 35))
        value = assignment(assigned_at=datetime(2026, 7, 23, 19, 35, tzinfo=timezone(timedelta(hours=-4))))
        self.assertEqual(value.assigned_at, AT)
    def test_dictionary_and_json_round_trips(self) -> None:
        value = assignment(state=ProviderAssignmentState.ACTIVE, revision=2)
        self.assertEqual(provider_assignment_from_dict(provider_assignment_to_dict(value)), value)
        payload = provider_assignment_to_json(value)
        self.assertEqual(provider_assignment_to_json(provider_assignment_from_json(payload)), payload)
        self.assertEqual(json.loads(payload)["assigned_at"], "2026-07-23T23:35:00Z")
    def test_validation_failures_raise(self) -> None:
        report = assignment(lease_id="", worker_id="", provider_id="", provider_capability="", authority_reference="").validate()
        self.assertEqual(len(report.issues), 5)
        with self.assertRaises(ValueError): report.raise_for_errors()
    def test_repository_compatibility_and_strict_fields(self) -> None:
        data = provider_assignment_to_dict(assignment())
        self.assertEqual((data["contract_type"], data["state"], data["provider_capability"]), ("dexter.provider_assignment", "ASSIGNED", "text.generation"))
        self.assertEqual(data["relationship_references"][0]["kind"], "related_to")
        data["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "unknown fields"): provider_assignment_from_dict(data)
    def test_missing_wire_field(self) -> None:
        data = provider_assignment_to_dict(assignment()); del data["authority_reference"]
        with self.assertRaisesRegex(ValueError, "missing required fields"): provider_assignment_from_dict(data)

if __name__ == "__main__": unittest.main()
