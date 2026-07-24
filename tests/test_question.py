import json
import unittest
from datetime import datetime, timezone

from dexter_core import QuestionEngine
from dexter_core.contracts import (
    Answer, AnswerConfidence, Assessment, AssessmentConfidence, AssessmentType,
    Question, QuestionType, answer_from_dict, answer_from_json, answer_to_dict,
    answer_to_json, question_from_dict, question_from_json, question_to_dict,
    question_to_json,
)

NOW = datetime(2026, 7, 24, 5, tzinfo=timezone.utc)


def assessment(kind: AssessmentType, suffix: str = "0", confidence: AssessmentConfidence = AssessmentConfidence.HIGH) -> Assessment:
    return Assessment(
        assessment_id=f"dexter:assessment:123e4567-e89b-12d3-a456-42661417400{suffix}",
        assessment_type=kind,
        primary_correlation_reference=f"dexter:correlation:primary-{suffix}",
        supporting_correlation_references=(f"dexter:correlation:supporting-{suffix}",),
        assessment_statement=f"{kind.value} was observed.",
        assessment_basis=f"Exact {kind.value} rule matched governed correlations.",
        confidence=confidence, assessed_at=NOW,
        authority_reference="dexter:authority:assessment-engine",
        evidence_references=(f"dexter:evidence:primary-{suffix}", f"dexter:evidence:supporting-{suffix}"),
        relationship_references=(f"dexter:relationship:{suffix}",),
    )


def question(kind: QuestionType = QuestionType.STATUS) -> Question:
    return Question(
        question_id="dexter:question:123e4567-e89b-12d3-a456-426614174000",
        question_type=kind, question_text="What is the governed operational status?",
        asked_at=NOW, authority_reference="dexter:authority:operator",
    )


class QuestionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = QuestionEngine(authority_reference="dexter:authority:question-engine")

    def test_supported_operational_answers(self) -> None:
        kinds = (
            AssessmentType.RESOURCE_UTILIZATION, AssessmentType.STATE_TRANSITION,
            AssessmentType.CONFIGURATION_CHANGE, AssessmentType.CAPACITY,
            AssessmentType.CONNECTIVITY, AssessmentType.SERVICE_DEGRADATION,
        )
        for kind in kinds:
            with self.subTest(kind):
                source = assessment(kind)
                value = self.engine.answer(question(), (source,))
                self.assertEqual(value.primary_assessment_reference, source.assessment_id)
                self.assertEqual(value.confidence, AnswerConfidence.HIGH)
                for reference in (*source.evidence_references, source.primary_correlation_reference,
                                  *source.supporting_correlation_references, source.assessment_id):
                    self.assertIn(reference, value.answer_text)

    def test_all_question_types_are_accepted_except_unknown(self) -> None:
        kinds = (QuestionType.WHAT, QuestionType.WHY, QuestionType.WHEN, QuestionType.WHERE, QuestionType.WHICH, QuestionType.STATUS)
        for kind in kinds:
            self.assertTrue(question(kind).validate().is_valid)
        self.assertIn("invalid_question_type", self._codes(question(QuestionType.UNKNOWN)))
        with self.assertRaisesRegex(ValueError, "question must validate"):
            self.engine.answer(question(QuestionType.UNKNOWN), (assessment(AssessmentType.CAPACITY),))

    def test_missing_assessment_and_invalid_assessment(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one assessment"):
            self.engine.answer(question(), ())
        with self.assertRaisesRegex(ValueError, "must validate"):
            self.engine.answer(question(), (assessment(AssessmentType.UNKNOWN),))

    def test_confidence_mapping_and_unknown_validation(self) -> None:
        cases = (
            (AssessmentConfidence.LOW, AnswerConfidence.LOW),
            (AssessmentConfidence.MEDIUM, AnswerConfidence.MEDIUM),
            (AssessmentConfidence.HIGH, AnswerConfidence.HIGH),
            (AssessmentConfidence.CERTAIN, AnswerConfidence.CERTAIN),
        )
        for source, expected in cases:
            value = self.engine.answer(question(), (assessment(AssessmentType.CAPACITY, confidence=source),))
            self.assertEqual(value.confidence, expected)
        self.assertIn("invalid_confidence", self._codes(self._answer(confidence=AnswerConfidence.UNKNOWN)))

    def test_question_and_answer_serialization(self) -> None:
        asked = question()
        value = self.engine.answer(asked, (assessment(AssessmentType.CONNECTIVITY),))
        self.assertEqual(question_from_dict(question_to_dict(asked)), asked)
        self.assertEqual(question_from_json(question_to_json(asked)), asked)
        self.assertEqual(answer_from_dict(answer_to_dict(value)), value)
        payload = answer_to_json(value)
        self.assertEqual(answer_to_json(answer_from_json(payload)), payload)
        self.assertEqual(json.loads(payload)["answered_at"], "2026-07-24T05:00:00Z")
        data = answer_to_dict(value)
        data["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            answer_from_dict(data)

    def test_validation_rules(self) -> None:
        question_cases = (({"question_id": "bad"}, "invalid_question_identity"), ({"question_text": ""}, "missing_question_text"), ({"authority_reference": ""}, "missing_authority_reference"), ({"revision": 0}, "invalid_revision"), ({"version": "2.0"}, "unsupported_version"))
        for changes, expected in question_cases:
            values: dict[str, object] = {"question_id": question().question_id, "question_type": QuestionType.STATUS, "question_text": "Status?", "asked_at": NOW, "authority_reference": "authority"}
            values.update(changes)
            self.assertIn(expected, self._codes(Question(**values)))  # type: ignore[arg-type]
        answer_cases = (({"answer_id": "bad"}, "invalid_answer_identity"), ({"question_reference": ""}, "missing_question_reference"), ({"primary_assessment_reference": ""}, "missing_primary_assessment"), ({"answer_text": ""}, "missing_answer_text"), ({"authority_reference": ""}, "missing_authority_reference"), ({"evidence_references": ()}, "invalid_evidence_references"), ({"revision": 0}, "invalid_revision"), ({"version": "2.0"}, "unsupported_version"))
        for changes, expected in answer_cases:
            self.assertIn(expected, self._codes(self._answer(**changes)))

    def test_lineage_supporting_assessments_and_repeatability(self) -> None:
        sources = (assessment(AssessmentType.CAPACITY, "0"), assessment(AssessmentType.CAPACITY, "1"))
        first = self.engine.answer(question(), sources)
        second = QuestionEngine(authority_reference="dexter:authority:question-engine").answer(question(), sources)
        self.assertEqual(first, second)
        self.assertEqual(answer_to_json(first), answer_to_json(second))
        self.assertEqual(first.supporting_assessment_references, (sources[1].assessment_id,))
        self.assertEqual(first.evidence_references, sources[0].evidence_references + sources[1].evidence_references)
        self.assertEqual(first.relationship_references, ("dexter:relationship:0", "dexter:relationship:1"))

    @staticmethod
    def _codes(value: object) -> set[str]:
        return {issue.code for issue in value.validate().issues}  # type: ignore[attr-defined]

    def _answer(self, **changes: object) -> Answer:
        values: dict[str, object] = {
            "answer_id": "dexter:answer:123e4567-e89b-12d3-a456-426614174000",
            "question_reference": "dexter:question:one", "primary_assessment_reference": "dexter:assessment:one",
            "supporting_assessment_references": (), "answer_text": "Governed answer.",
            "confidence": AnswerConfidence.HIGH, "answered_at": NOW,
            "authority_reference": "dexter:authority:question-engine",
            "evidence_references": ("dexter:evidence:one",), "relationship_references": (),
        }
        values.update(changes)
        return Answer(**values)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
