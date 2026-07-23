import unittest
from datetime import datetime, timezone

from dexter_core import (
    Authority, AuthorityKind, EvidenceReference, GovernedEntity, LifecycleState,
    ProvenanceReference, RelationshipKind, RelationshipReference, entity_from_dict,
    entity_from_json, entity_to_dict, entity_to_json,
)

NOW = datetime(2026, 1, 1, 12, 30, tzinfo=timezone.utc)


def complete_entity() -> GovernedEntity:
    return GovernedEntity(
        "dataset", "Orders", Authority("system:catalog", "Catalog", AuthorityKind.SYSTEM, NOW),
        lifecycle_state=LifecycleState.ACTIVE,
        provenance=(ProvenanceReference("s3://records/orders", NOW, digest="sha256:abc"),),
        evidence=(EvidenceReference("https://example.test/report", "application/pdf"),),
        relationships=(RelationshipReference("dexter:123e4567-e89b-12d3-a456-426614174000", RelationshipKind.DEPENDS_ON, {"required": True}),),
        attributes={"tags": ["financial", "daily"]}, created_at=NOW, updated_at=NOW,
    )


class SerializationTests(unittest.TestCase):
    def test_json_round_trip_preserves_contract(self) -> None:
        entity = complete_entity()
        restored = entity_from_json(entity_to_json(entity))
        self.assertEqual(entity_to_dict(restored), entity_to_dict(entity))
        self.assertTrue(restored.validate().is_valid)

    def test_serialized_data_is_json_compatible(self) -> None:
        data = entity_to_dict(complete_entity())
        self.assertEqual(data["authority"]["kind"], "system")
        self.assertTrue(data["created_at"].endswith("Z"))
        self.assertEqual(data["attributes"]["tags"], ["financial", "daily"])

    def test_missing_required_fields_are_reported(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing required fields"):
            entity_from_dict({})

    def test_json_root_must_be_object(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be an object"):
            entity_from_json("[]")

    def test_unknown_fields_are_rejected(self) -> None:
        data = entity_to_dict(complete_entity())
        data["unknown"] = True
        with self.assertRaises(TypeError):
            entity_from_dict(data)


if __name__ == "__main__":
    unittest.main()

