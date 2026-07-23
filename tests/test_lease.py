import json
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

from dexter_core import EvidenceReference, RelationshipKind, RelationshipReference
from dexter_core.contracts import Lease, LeaseState, lease_from_dict, lease_from_json, lease_to_dict, lease_to_json

ISSUED_AT = datetime(2026, 7, 23, 23, 0, tzinfo=timezone.utc)
LEASE_ID = "dexter:lease:123e4567-e89b-12d3-a456-426614174000"


def lease(**changes: object) -> Lease:
    values: dict[str, object] = {
        "lease_id": LEASE_ID, "worker_claim_id": "dexter:claim:123e4567-e89b-12d3-a456-426614174001",
        "pending_job_id": "dexter:pending-job:job-1", "worker_id": "dexter:worker:worker-1", "state": LeaseState.ISSUED,
        "issued_at": ISSUED_AT, "expires_at": ISSUED_AT + timedelta(minutes=5), "authority_reference": "dexter:authority:governance",
        "evidence_references": (EvidenceReference("https://example.test/evidence", "application/json"),),
        "relationship_references": (RelationshipReference("dexter:pending-job:job-1", RelationshipKind.RELATED_TO),),
    }
    values.update(changes)
    return Lease(**values)  # type: ignore[arg-type]


class LeaseTests(unittest.TestCase):
    def test_valid_lease(self) -> None:
        self.assertTrue(lease().validate().is_valid)

    def test_identity_is_stable_and_immutable(self) -> None:
        value = lease()
        self.assertEqual(lease_from_json(lease_to_json(value)).lease_id, value.lease_id)
        with self.assertRaises(FrozenInstanceError):
            value.lease_id = "changed"  # type: ignore[misc]

    def test_required_references(self) -> None:
        cases = (("authority_reference", "missing_authority_reference"), ("worker_claim_id", "missing_worker_claim_reference"), ("worker_id", "missing_worker_identity"), ("pending_job_id", "missing_pending_job_reference"), ("lease_id", "missing_lease_identity"))
        for field, code in cases:
            with self.subTest(field=field):
                self.assertEqual(lease(**{field: ""}).validate().issues[0].code, code)

    def test_expiration_must_follow_issuance(self) -> None:
        for expires_at in (ISSUED_AT, ISSUED_AT - timedelta(seconds=1)):
            with self.subTest(expires_at=expires_at):
                self.assertEqual(lease(expires_at=expires_at).validate().issues[0].code, "invalid_expiration")

    def test_invalid_and_unknown_states(self) -> None:
        self.assertEqual(lease(state="RUNNING").validate().issues[0].code, "invalid_state")
        self.assertEqual(lease(state=LeaseState.UNKNOWN).validate().issues[0].code, "unknown_state")
        data = lease_to_dict(lease()); data["state"] = "RUNNING"
        with self.assertRaisesRegex(ValueError, "recognized LeaseState"):
            lease_from_dict(data)

    def test_revision_and_version_integrity(self) -> None:
        self.assertEqual(lease(revision=0).validate().issues[0].code, "invalid_revision")
        self.assertEqual(lease(revision=True).validate().issues[0].code, "invalid_revision")
        self.assertEqual(lease(version="2.0").validate().issues[0].code, "unsupported_version")

    def test_timezone_aware_timestamps_are_required_and_normalized(self) -> None:
        with self.assertRaisesRegex(ValueError, "issued_at must be timezone-aware"):
            lease(issued_at=datetime(2026, 7, 23, 23, 0))
        offset = timezone(timedelta(hours=-4))
        value = lease(issued_at=datetime(2026, 7, 23, 19, 0, tzinfo=offset), expires_at=datetime(2026, 7, 23, 19, 5, tzinfo=offset))
        self.assertEqual(value.issued_at, ISSUED_AT)
        self.assertEqual(value.issued_at.tzinfo, timezone.utc)

    def test_deterministic_serialization_round_trip(self) -> None:
        payload = lease_to_json(lease(state=LeaseState.ACTIVE, revision=2))
        self.assertEqual(lease_to_json(lease_from_json(payload)), payload)
        data = json.loads(payload)
        self.assertEqual(data["issued_at"], "2026-07-23T23:00:00Z")
        self.assertEqual(data["expires_at"], "2026-07-23T23:05:00Z")

    def test_validation_failures_raise(self) -> None:
        report = lease(worker_claim_id="", worker_id="", authority_reference="", expires_at=ISSUED_AT).validate()
        self.assertEqual(len(report.issues), 4)
        with self.assertRaises(ValueError):
            report.raise_for_errors()

    def test_repository_compatibility_and_strict_fields(self) -> None:
        data = lease_to_dict(lease())
        self.assertEqual(data["contract_type"], "dexter.lease")
        self.assertEqual(data["state"], "ISSUED")
        self.assertEqual(data["relationship_references"][0]["kind"], "related_to")
        data["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            lease_from_dict(data)

    def test_missing_wire_field(self) -> None:
        data = lease_to_dict(lease()); del data["authority_reference"]
        with self.assertRaisesRegex(ValueError, "missing required fields"):
            lease_from_dict(data)


if __name__ == "__main__":
    unittest.main()
