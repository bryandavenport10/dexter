from datetime import datetime, timezone

from dexter_core import (
    Authority,
    AuthorityKind,
    GovernedEntity,
    LifecycleState,
    OperationalStatus,
    ProvenanceReference,
    entity_from_json,
    entity_to_json,
)


def main() -> None:
    now = datetime.now(timezone.utc)
    entity = GovernedEntity(
        entity_type="dataset",
        name="Customer Reference Data",
        lifecycle_state=LifecycleState.ACTIVE,
        operational_status=OperationalStatus.OPERATIONAL,
        authority=Authority("data-office", "Data Office", AuthorityKind.ORGANIZATION, now),
        provenance=(ProvenanceReference("https://example.com/sources/customer-data", now),),
        attributes={"classification": "internal"},
    )
    entity.validate().raise_for_errors()
    payload = entity_to_json(entity, indent=2)
    restored = entity_from_json(payload)
    assert restored.entity_id == entity.entity_id
    print(payload)


if __name__ == "__main__":
    main()

