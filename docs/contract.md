# Governed Entity Contract

## Identity and versioning

`entity_id` is assigned once as `dexter:<uuid>` and is part of entity identity. Consumers must preserve it across serialization, storage, and updates. `schema_version` versions the serialized contract independently from the Python distribution. This release emits and validates schema `1.0`.

`GovernedEntity` is a frozen dataclass. This prevents accidental reassignment of identity or governance state. Create a new value (for example with `dataclasses.replace`) when recording an intentional state transition, retain the same `entity_id`, and advance `updated_at`.

## Governance fields

- `entity_type` is the domain-level classification.
- `lifecycle_state` is one of draft, active, deprecated, or retired.
- `operational_status` is unknown, operational, degraded, or unavailable.
- `authority` records the person, organization, or system asserting the entity.
- `provenance` identifies origins and the time they were recorded.
- `evidence` links supporting material and states its media type.
- `relationships` are typed outbound references to other stable entity IDs.
- `attributes` holds domain-specific, JSON-serializable values.

## Validation

Construction enforces structural invariants such as valid identifiers, absolute reference URIs, non-empty required strings, and timezone-aware timestamps. `GovernedEntity.validate()` enforces semantic rules and returns a `ValidationReport`. Active entities require provenance; timestamps must be ordered; self-relationships are rejected; and the schema version must be supported.

Applications can pass callable custom rules to `validate`. Each rule accepts the entity and returns a sequence of `ValidationIssue` values. Call `report.raise_for_errors()` at a trust boundary to raise `EntityValidationError` with the complete report.

## Serialization

`entity_to_dict` and `entity_to_json` produce JSON-compatible data. Timestamps use ISO 8601 UTC notation. `entity_from_dict` and `entity_from_json` reconstruct typed values. Deserialization performs the same structural checks as direct construction. Validate the returned entity before admitting it to a governed store.

