import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

from dexter_core import (
    Authority, AuthorityKind, GovernedEntity, LifecycleState, OperationalStatus,
    ProvenanceReference, RelationshipKind, RelationshipReference, ValidationIssue,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def authority() -> Authority:
    return Authority("owner-1", "Platform Team", AuthorityKind.ORGANIZATION, NOW)


class GovernedEntityTests(unittest.TestCase):
    def test_entity_has_stable_immutable_identity(self) -> None:
        entity = GovernedEntity("service", "Search", authority())
        self.assertTrue(entity.entity_id.startswith("dexter:"))
        with self.assertRaises(FrozenInstanceError):
            entity.entity_id = "dexter:changed"  # type: ignore[misc]

    def test_active_entity_requires_provenance(self) -> None:
        entity = GovernedEntity("service", "Search", authority(), lifecycle_state=LifecycleState.ACTIVE)
        report = entity.validate()
        self.assertFalse(report.is_valid)
        self.assertEqual(report.issues[0].code, "missing_provenance")

    def test_active_entity_with_provenance_is_valid(self) -> None:
        source = ProvenanceReference("https://example.test/source", NOW)
        entity = GovernedEntity("service", "Search", authority(), lifecycle_state=LifecycleState.ACTIVE, operational_status=OperationalStatus.OPERATIONAL, provenance=(source,))
        self.assertTrue(entity.validate().is_valid)

    def test_timestamp_order_and_self_relationship_are_reported(self) -> None:
        initial = GovernedEntity("service", "Search", authority(), created_at=NOW, updated_at=NOW - timedelta(seconds=1))
        relationship = RelationshipReference(initial.entity_id, RelationshipKind.RELATED_TO)
        entity = GovernedEntity("service", "Search", authority(), entity_id=initial.entity_id, relationships=(relationship,), created_at=NOW, updated_at=NOW - timedelta(seconds=1))
        self.assertEqual({i.code for i in entity.validate().issues}, {"invalid_timestamp_order", "self_relationship"})

    def test_custom_validation_rule(self) -> None:
        entity = GovernedEntity("service", "Search", authority())

        def require_owner(value: GovernedEntity) -> list[ValidationIssue]:
            return [] if "owner" in value.attributes else [ValidationIssue("owner_required", "owner is required", "$.attributes.owner")]

        self.assertEqual(entity.validate(require_owner).issues[0].code, "owner_required")

    def test_invalid_identity_is_rejected(self) -> None:
        for value in ("", "x", "dexter:not-a-uuid"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                GovernedEntity("service", "Search", authority(), entity_id=value)

    def test_naive_timestamp_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            Authority("owner", "Owner", AuthorityKind.PERSON, datetime(2026, 1, 1))


if __name__ == "__main__":
    unittest.main()

