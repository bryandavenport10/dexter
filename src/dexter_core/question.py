"""Deterministic answers derived exclusively from governed assessments."""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from uuid import NAMESPACE_URL, uuid5

from .contracts.assessment import Assessment
from .contracts.question import Answer, AnswerConfidence, Question
from .serialization import contract_to_json


class QuestionEngine:
    """Answer validated questions without prediction, generation, or action."""

    def __init__(self, *, authority_reference: str) -> None:
        if not isinstance(authority_reference, str) or not authority_reference.strip():
            raise ValueError("authority_reference is required")
        self.authority_reference = authority_reference.strip()

    def answer(self, question: Question, assessments: Sequence[Assessment]) -> Answer:
        if not isinstance(question, Question):
            raise TypeError("question must be Question")
        if not question.validate().is_valid:
            raise ValueError("question must validate")
        if isinstance(assessments, (str, bytes, bytearray)) or not isinstance(assessments, Sequence):
            raise TypeError("assessments must be a sequence of Assessment")
        ordered = tuple(assessments)
        if not ordered:
            raise ValueError("at least one assessment is required")
        for index, assessment in enumerate(ordered):
            if not isinstance(assessment, Assessment):
                raise TypeError(f"assessments[{index}] must be Assessment")
            if not assessment.validate().is_valid:
                raise ValueError(f"assessments[{index}] must validate")
        identifiers = tuple(item.assessment_id for item in ordered)
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("assessments must be unique")

        primary = ordered[0]
        evidence = _ordered_unique(reference for item in ordered for reference in item.evidence_references)
        relationships = _ordered_unique(reference for item in ordered for reference in item.relationship_references)
        correlations = _ordered_unique(
            reference for item in ordered
            for reference in (item.primary_correlation_reference, *item.supporting_correlation_references)
        )
        answered_at = max(question.asked_at, *(item.assessed_at for item in ordered))
        confidence = AnswerConfidence(primary.confidence.value)
        text = (
            f"Observed: {primary.assessment_statement} "
            f"Evidence: {', '.join(evidence)}. "
            f"Correlations: {', '.join(correlations)}. "
            f"Assessment: {primary.assessment_id}. "
            f"Assessment basis: {primary.assessment_basis}"
        )
        material = {
            "answer_text": text, "answered_at": answered_at,
            "assessment_references": identifiers, "authority_reference": self.authority_reference,
            "confidence": confidence.value, "evidence_references": evidence,
            "question_reference": question.question_id, "relationship_references": relationships,
        }
        value = Answer(
            answer_id=f"dexter:answer:{uuid5(NAMESPACE_URL, contract_to_json(material))}",
            question_reference=question.question_id,
            primary_assessment_reference=primary.assessment_id,
            supporting_assessment_references=identifiers[1:],
            answer_text=text, confidence=confidence, answered_at=answered_at,
            authority_reference=self.authority_reference,
            evidence_references=evidence, relationship_references=relationships,
        )
        value.validate().raise_for_errors()
        return value


def _ordered_unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))
