import json
import unittest
from datetime import datetime, timedelta, timezone
from dexter_core import EvidenceReference, RelationshipKind, RelationshipReference
from dexter_core.contracts import ExecutionVerification, VerificationResult, execution_verification_from_dict, execution_verification_from_json, execution_verification_to_dict, execution_verification_to_json

VERIFIED_AT = datetime(2026, 7, 24, 0, 35, tzinfo=timezone.utc)
VERIFICATION_ID = "dexter:execution-verification:123e4567-e89b-12d3-a456-426614174010"
def verification(**changes: object) -> ExecutionVerification:
    values: dict[str, object] = {"verification_id": VERIFICATION_ID, "execution_session_id": "dexter:execution-session:123e4567-e89b-12d3-a456-426614174010", "execution_attempt_id": "dexter:execution-attempt:123e4567-e89b-12d3-a456-426614174000", "provider_assignment_id": "dexter:provider-assignment:123e4567-e89b-12d3-a456-426614174009", "lease_id": "dexter:lease:123e4567-e89b-12d3-a456-426614174001", "worker_id": "dexter:worker:worker-1", "provider_id": "dexter:provider:provider-1", "result": VerificationResult.VERIFIED, "verified_at": VERIFIED_AT, "authority_reference": "dexter:authority:governance", "evidence_references": (EvidenceReference("https://example.test/evidence", "application/json"),), "relationship_references": (RelationshipReference("dexter:execution-attempt:123e4567-e89b-12d3-a456-426614174000", RelationshipKind.RELATED_TO),)}
    values.update(changes)
    return ExecutionVerification(**values)  # type: ignore[arg-type]

class ExecutionVerificationTests(unittest.TestCase):
    def test_valid_verification(self) -> None: self.assertTrue(verification().validate().is_valid)
    def test_required_values(self) -> None:
        for field, code in (("verification_id", "missing_verification_identity"), ("execution_session_id", "missing_execution_session_reference"), ("execution_attempt_id", "missing_execution_attempt_reference"), ("provider_assignment_id", "missing_provider_assignment_reference"), ("lease_id", "missing_lease_reference"), ("worker_id", "missing_worker_identity"), ("provider_id", "missing_provider_identity"), ("authority_reference", "missing_authority_reference")):
            with self.subTest(field=field): self.assertEqual(verification(**{field: ""}).validate().issues[0].code, code)
    def test_invalid_and_unknown_results(self) -> None:
        self.assertEqual(verification(result="NOTICE").validate().issues[0].code, "invalid_verification_result")
        self.assertEqual(verification(result=VerificationResult.UNKNOWN).validate().issues[0].code, "unknown_verification_result")
        data = execution_verification_to_dict(verification()); data["result"] = "NOTICE"
        with self.assertRaisesRegex(ValueError, "VerificationResult"): execution_verification_from_dict(data)
    def test_revision_and_version(self) -> None:
        self.assertEqual(verification(revision=0).validate().issues[0].code, "invalid_revision")
        self.assertEqual(verification(revision=True).validate().issues[0].code, "invalid_revision")
        self.assertEqual(verification(version="2.0").validate().issues[0].code, "unsupported_version")
    def test_timestamp_requirements_and_normalization(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware"): verification(verified_at=datetime(2026, 7, 24, 0, 35))
        value = verification(verified_at=datetime(2026, 7, 23, 20, 35, tzinfo=timezone(timedelta(hours=-4))))
        self.assertEqual(value.verified_at, VERIFIED_AT)
    def test_dictionary_and_json_round_trips(self) -> None:
        value = verification(result=VerificationResult.PARTIALLY_VERIFIED, revision=2)
        self.assertEqual(execution_verification_from_dict(execution_verification_to_dict(value)), value)
        payload = execution_verification_to_json(value)
        self.assertEqual(execution_verification_to_json(execution_verification_from_json(payload)), payload)
        self.assertEqual(json.loads(payload)["verified_at"], "2026-07-24T00:35:00Z")
    def test_validation_failures_raise(self) -> None:
        report = verification(execution_session_id="", execution_attempt_id="", provider_assignment_id="", lease_id="", worker_id="", provider_id="", authority_reference="").validate()
        self.assertEqual(len(report.issues), 7)
        with self.assertRaises(ValueError): report.raise_for_errors()
    def test_repository_compatibility_and_strict_fields(self) -> None:
        data = execution_verification_to_dict(verification())
        self.assertEqual((data["contract_type"], data["result"], data["execution_attempt_id"]), ("dexter.execution_verification", "VERIFIED", "dexter:execution-attempt:123e4567-e89b-12d3-a456-426614174000"))
        self.assertEqual(data["relationship_references"][0]["kind"], "related_to")
        data["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "unknown fields"): execution_verification_from_dict(data)
    def test_missing_wire_field(self) -> None:
        data = execution_verification_to_dict(verification()); del data["authority_reference"]
        with self.assertRaisesRegex(ValueError, "missing required fields"): execution_verification_from_dict(data)
    def test_all_supported_results_except_unknown_validate(self) -> None:
        for result in (VerificationResult.VERIFIED, VerificationResult.PARTIALLY_VERIFIED, VerificationResult.FAILED_VERIFICATION, VerificationResult.INCONCLUSIVE):
            with self.subTest(result=result): self.assertTrue(verification(result=result).validate().is_valid)

if __name__ == "__main__": unittest.main()
