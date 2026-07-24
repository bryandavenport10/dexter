"""Deterministic assessment rules for governed evidence correlations."""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from .contracts.assessment import Assessment, AssessmentConfidence, AssessmentType
from .contracts.evidence_correlation import CorrelationType, EvidenceCorrelation
from .serialization import contract_to_json


@dataclass(frozen=True, slots=True)
class _Rule:
    kind: AssessmentType
    groups: tuple[frozenset[str], ...]
    statement: str
    correlation_types: frozenset[CorrelationType] = frozenset()


_RULES = (
    _Rule(AssessmentType.STATE_TRANSITION, (), "Correlated evidence records a state transition.", frozenset({CorrelationType.STATE_CHANGE})),
    _Rule(AssessmentType.RESOURCE_UTILIZATION, (frozenset({"cpu", "processor"}), frozenset({"memory", "ram"})), "Correlated evidence records concurrent CPU and memory utilization pressure."),
    _Rule(AssessmentType.CONFIGURATION_CHANGE, (frozenset({"configuration", "config"}),), "Correlated evidence records a configuration change."),
    _Rule(AssessmentType.SERVICE_DEGRADATION, (frozenset({"degraded", "degradation", "unavailable", "failure", "failed", "error", "latency"}),), "Correlated evidence records service degradation."),
    _Rule(AssessmentType.CAPACITY, (frozenset({"storage", "disk", "capacity", "filesystem"}),), "Correlated evidence records storage capacity conditions."),
    _Rule(AssessmentType.CONNECTIVITY, (frozenset({"network", "connectivity", "link", "packet", "interface"}),), "Correlated evidence records network connectivity conditions."),
)


class AssessmentEngine:
    """Turn validated correlations into explainable assessments using exact rules."""

    def __init__(self, *, authority_reference: str) -> None:
        if not isinstance(authority_reference, str) or not authority_reference.strip():
            raise ValueError("authority_reference is required")
        self.authority_reference = authority_reference.strip()

    def assess(self, correlations: Sequence[EvidenceCorrelation]) -> Assessment:
        if isinstance(correlations, (str, bytes, bytearray)) or not isinstance(correlations, Sequence):
            raise TypeError("correlations must be a sequence of EvidenceCorrelation")
        ordered = tuple(correlations)
        if len(ordered) < 2:
            raise ValueError("a primary correlation and at least one supporting correlation are required")
        for index, correlation in enumerate(ordered):
            if not isinstance(correlation, EvidenceCorrelation):
                raise TypeError(f"correlations[{index}] must be EvidenceCorrelation")
            if not correlation.validate().is_valid:
                raise ValueError(f"correlations[{index}] must validate")
        identifiers = tuple(item.correlation_id for item in ordered)
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("correlations must be unique")
        rule = self._matching_rule(ordered)
        if rule is None:
            raise ValueError("correlations do not match an implemented assessment rule")
        evidence = _ordered_unique(reference for item in ordered for reference in item.evidence_references)
        relationships = _ordered_unique(reference for item in ordered for reference in item.relationship_references)
        confidence = _confidence(ordered)
        basis = f"Rule {rule.kind.value} matched correlations {', '.join(identifiers)}. Supporting evidence: {', '.join(evidence)}."
        material = {"assessment_type": rule.kind.value, "authority_reference": self.authority_reference, "correlation_references": identifiers, "evidence_references": evidence, "relationship_references": relationships, "confidence": confidence.value}
        value = Assessment(
            assessment_id=f"dexter:assessment:{uuid5(NAMESPACE_URL, contract_to_json(material))}",
            assessment_type=rule.kind, primary_correlation_reference=identifiers[0],
            supporting_correlation_references=identifiers[1:], assessment_statement=rule.statement,
            assessment_basis=basis, confidence=confidence, assessed_at=max(item.correlated_at for item in ordered),
            authority_reference=self.authority_reference, evidence_references=evidence,
            relationship_references=relationships,
        )
        value.validate().raise_for_errors()
        return value

    @staticmethod
    def _matching_rule(correlations: tuple[EvidenceCorrelation, ...]) -> _Rule | None:
        tokens = {token for item in correlations for token in _tokens(" ".join((item.correlation_basis, *item.evidence_references, *item.relationship_references)))}
        types = {item.correlation_type for item in correlations}
        for rule in _RULES:
            if rule.correlation_types.intersection(types) or (rule.groups and all(group.intersection(tokens) for group in rule.groups)):
                return rule
        return None


def _tokens(value: str) -> tuple[str, ...]:
    return tuple("".join(character.lower() if character.isalnum() else " " for character in value).split())


def _ordered_unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _confidence(correlations: tuple[EvidenceCorrelation, ...]) -> AssessmentConfidence:
    count = len(correlations)
    if count >= 5 and all(item.confidence == 1.0 for item in correlations):
        return AssessmentConfidence.CERTAIN
    if count >= 4:
        return AssessmentConfidence.HIGH
    if count >= 3:
        return AssessmentConfidence.MEDIUM
    return AssessmentConfidence.LOW
