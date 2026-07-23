import json
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

from dexter_core import EvidenceReference, RelationshipKind, RelationshipReference
from dexter_core.contracts import ClaimState, WorkerClaim, worker_claim_from_dict, worker_claim_from_json, worker_claim_to_dict, worker_claim_to_json

NOW = datetime(2026, 7, 23, 22, 45, tzinfo=timezone.utc)
CLAIM_ID = "dexter:claim:123e4567-e89b-12d3-a456-426614174000"


def claim(**changes: object) -> WorkerClaim:
    values: dict[str, object] = {
        "claim_id": CLAIM_ID, "pending_job_id": "dexter:pending-job:job-1", "worker_id": "dexter:worker:worker-1",
        "claim_timestamp": NOW, "state": ClaimState.REQUESTED, "authority_reference": "dexter:authority:governance",
        "evidence_references": (EvidenceReference("https://example.test/evidence", "application/json"),),
        "relationship_references": (RelationshipReference("dexter:pending-job:job-1", RelationshipKind.RELATED_TO),),
    }
    values.update(changes)
    return WorkerClaim(**values)  # type: ignore[arg-type]


class WorkerClaimTests(unittest.TestCase):
    def test_valid_claim(self) -> None:
        self.assertTrue(claim().validate().is_valid)

    def test_identity_is_stable_and_immutable(self) -> None:
        value = claim()
        self.assertEqual(worker_claim_from_json(worker_claim_to_json(value)).claim_id, value.claim_id)
        with self.assertRaises(FrozenInstanceError):
            value.claim_id = "changed"  # type: ignore[misc]

    def test_required_references(self) -> None:
        cases = (("authority_reference", "missing_authority_reference"), ("worker_id", "missing_worker_identity"),
                 ("pending_job_id", "missing_pending_job_reference"), ("claim_id", "missing_claim_identity"))
        for field, code in cases:
            with self.subTest(field=field):
                self.assertEqual(claim(**{field: ""}).validate().issues[0].code, code)

    def test_invalid_and_unknown_states(self) -> None:
        self.assertEqual(claim(state="CLAIMED").validate().issues[0].code, "invalid_state")
        self.assertEqual(claim(state=ClaimState.UNKNOWN).validate().issues[0].code, "unknown_state")
        data = worker_claim_to_dict(claim()); data["state"] = "CLAIMED"
        with self.assertRaisesRegex(ValueError, "recognized ClaimState"):
            worker_claim_from_dict(data)

    def test_revision_and_version_integrity(self) -> None:
        self.assertEqual(claim(revision=0).validate().issues[0].code, "invalid_revision")
        self.assertEqual(claim(version="2.0").validate().issues[0].code, "unsupported_version")

    def test_deterministic_serialization_round_trip(self) -> None:
        payload = worker_claim_to_json(claim(state=ClaimState.ACCEPTED, revision=2))
        self.assertEqual(worker_claim_to_json(worker_claim_from_json(payload)), payload)
        self.assertEqual(json.loads(payload)["claim_timestamp"], "2026-07-23T22:45:00Z")

    def test_validation_failures_raise(self) -> None:
        report = claim(worker_id="", authority_reference="").validate()
        self.assertEqual(len(report.issues), 2)
        with self.assertRaises(ValueError):
            report.raise_for_errors()

    def test_repository_compatibility_and_strict_fields(self) -> None:
        data = worker_claim_to_dict(claim())
        self.assertEqual(data["state"], "REQUESTED")
        self.assertEqual(data["relationship_references"][0]["kind"], "related_to")
        data["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            worker_claim_from_dict(data)

    def test_missing_wire_field(self) -> None:
        data = worker_claim_to_dict(claim()); del data["authority_reference"]
        with self.assertRaisesRegex(ValueError, "missing required fields"):
            worker_claim_from_dict(data)


if __name__ == "__main__":
    unittest.main()
