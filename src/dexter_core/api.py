"""FastAPI composition root for Dexter's read-only Query API."""

import json
from datetime import datetime
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from . import __version__
from .contracts.query import (
    QUERY_VERSION,
    QueryRequest,
    QueryType,
    query_response_to_dict,
)
from .query import EmptyEvidenceRepository, GovernedDataRepository, QueryService


class CanonicalJSONResponse(JSONResponse):
    def render(self, content):
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()


def create_app(service=None):
    svc = service or QueryService(GovernedDataRepository(EmptyEvidenceRepository()))
    app = FastAPI(
        title="Dexter Query API",
        version=__version__,
        description="Deterministic read-only access to governed operational data.",
        default_response_class=CanonicalJSONResponse,
    )

    @app.get("/")
    def root():
        return {"name": "Dexter Query API", "version": __version__}

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    @app.get("/version")
    def version():
        return {"version": __version__}

    def params(
        request_identity: str = Query(...),
        requested_timestamp: datetime = Query(...),
        authority_reference: str = Query(...),
        version: str = Query(QUERY_VERSION),
        revision: int = Query(1),
    ):
        return (
            request_identity,
            requested_timestamp,
            authority_reference,
            version,
            revision,
        )

    def execute(kind, resource, v):
        try:
            request = QueryRequest(v[0], kind, resource, v[1], v[2], v[4], v[3])
            return query_response_to_dict(svc.query(request))
        except (TypeError, ValueError) as e:
            raise HTTPException(422, str(e)) from e

    @app.get("/evidence")
    def evidence(v=Depends(params)):
        return execute(QueryType.EVIDENCE, "/evidence", v)

    @app.get("/evidence/{identity}")
    def evidence_one(identity: str, v=Depends(params)):
        return execute(QueryType.EVIDENCE, f"/evidence/{identity}", v)

    @app.get("/assessments")
    def assessments(v=Depends(params)):
        return execute(QueryType.ASSESSMENT, "/assessments", v)

    @app.get("/assessments/{identity}")
    def assessment_one(identity: str, v=Depends(params)):
        return execute(QueryType.ASSESSMENT, f"/assessments/{identity}", v)

    @app.get("/questions")
    def questions(v=Depends(params)):
        return execute(QueryType.QUESTION, "/questions", v)

    @app.get("/answers")
    def answers(v=Depends(params)):
        return execute(QueryType.ANSWER, "/answers", v)

    @app.get("/status")
    def status(v=Depends(params)):
        return execute(QueryType.STATUS, "/status", v)

    return app


app = create_app()
