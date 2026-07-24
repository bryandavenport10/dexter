"""Public API for Dexter Core."""

from .entity import CURRENT_SCHEMA_VERSION, GovernedEntity, new_entity_id
from .enums import AuthorityKind, LifecycleState, OperationalStatus, RelationshipKind
from .references import Authority, EvidenceReference, ProvenanceReference, RelationshipReference
from .serialization import contract_to_dict, contract_to_json, entity_from_dict, entity_from_json, entity_to_dict, entity_to_json
from .validation import EntityValidationError, ValidationIssue, ValidationReport, ValidationRule, Validator
from .correlation import CorrelationEngine
from .contracts.evidence_correlation import CorrelationType, EvidenceCorrelation
from .assessment import AssessmentEngine
from .contracts.assessment import Assessment, AssessmentConfidence, AssessmentType

__version__ = "0.1.0"

__all__ = [
    "CURRENT_SCHEMA_VERSION", "Assessment", "AssessmentConfidence", "AssessmentEngine",
    "AssessmentType", "Authority", "AuthorityKind", "CorrelationEngine",
    "CorrelationType", "EvidenceCorrelation", "EntityValidationError",
    "EvidenceReference", "GovernedEntity", "LifecycleState", "OperationalStatus",
    "ProvenanceReference", "RelationshipKind", "RelationshipReference", "ValidationIssue",
    "ValidationReport", "ValidationRule", "Validator", "contract_to_dict", "contract_to_json", "entity_from_dict", "entity_from_json",
    "entity_to_dict", "entity_to_json", "new_entity_id",
]
