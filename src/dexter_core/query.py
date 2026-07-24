"""Deterministic read-only access to governed operational data."""

from dataclasses import dataclass
from typing import Protocol
from uuid import NAMESPACE_URL, uuid5
from .contracts.query import QueryRequest, QueryResponse, QueryType
from .contracts.ingestion import RepositoryStatus
from .persistence.evidence import RepositoryHealth
from .serialization import contract_to_dict, contract_to_json


class QueryValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class GovernedDataRepository:
    evidence_repository: object
    assessments: tuple = ()
    questions: tuple = ()
    answers: tuple = ()

    def __post_init__(self):
        for n in ("assessments", "questions", "answers"):
            object.__setattr__(self, n, tuple(getattr(self, n)))

    def evidence(self, identity=None):
        if identity is None:
            return self.evidence_repository.get_all()
        x = self.evidence_repository.get_by_identity(identity)
        return () if x is None else (x,)

    def assessment(self, identity=None):
        return tuple(
            sorted(
                (
                    x
                    for x in self.assessments
                    if identity is None or x.assessment_id == identity
                ),
                key=lambda x: x.assessment_id,
            )
        )

    def question(self):
        return tuple(sorted(self.questions, key=lambda x: x.question_id))

    def answer(self):
        return tuple(sorted(self.answers, key=lambda x: x.answer_id))

    def status(self):
        return self.evidence_repository.health()


class EmptyEvidenceRepository:
    def get_all(self):
        return ()

    def get_by_identity(self, identity):
        return None

    def health(self):
        return RepositoryHealth(RepositoryStatus.HEALTHY, "empty read-only repository")


class QueryService:
    def __init__(self, repository):
        self._repository = repository

    def query(self, r):
        if not isinstance(r, QueryRequest):
            raise TypeError("request must be QueryRequest")
        report = r.validate()
        if not report.is_valid:
            raise QueryValidationError("; ".join(x.message for x in report.issues))
        parts = r.requested_resource.strip("/").split("/", 1)
        identity = parts[1] if len(parts) > 1 else None
        dispatch = {
            QueryType.EVIDENCE: lambda: self._repository.evidence(identity),
            QueryType.ASSESSMENT: lambda: self._repository.assessment(identity),
            QueryType.QUESTION: self._repository.question,
            QueryType.ANSWER: self._repository.answer,
            QueryType.STATUS: lambda: (self._repository.status(),),
        }
        objects = dispatch[r.query_type]()
        returned = tuple(contract_to_dict(x) for x in objects)
        fingerprint = (
            contract_to_json(r) + "|" + "|".join(contract_to_json(x) for x in objects)
        )
        response = QueryResponse(
            f"dexter:query-response:{uuid5(NAMESPACE_URL,fingerprint)}",
            r.request_id,
            r.requested_at,
            len(returned),
            returned,
            r.authority_reference,
            r.revision,
            r.version,
        )
        response.validate().raise_for_errors()
        return response
