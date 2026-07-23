"""Public API for Dexter Core."""

from .entity import CURRENT_SCHEMA_VERSION, GovernedEntity, new_entity_id
from .enums import AuthorityKind, LifecycleState, OperationalStatus, RelationshipKind
from .references import Authority, EvidenceReference, ProvenanceReference, RelationshipReference
from .serialization import entity_from_dict, entity_from_json, entity_to_dict, entity_to_json
from .validation import EntityValidationError, ValidationIssue, ValidationReport, ValidationRule, Validator

__version__ = "0.1.0"

__all__ = [
    "CURRENT_SCHEMA_VERSION", "Authority", "AuthorityKind", "EntityValidationError",
    "EvidenceReference", "GovernedEntity", "LifecycleState", "OperationalStatus",
    "ProvenanceReference", "RelationshipKind", "RelationshipReference", "ValidationIssue",
    "ValidationReport", "ValidationRule", "Validator", "entity_from_dict", "entity_from_json",
    "entity_to_dict", "entity_to_json", "new_entity_id",
]

