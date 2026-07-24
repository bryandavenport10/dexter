import unittest
from datetime import datetime, timezone
from uuid import uuid4
from fastapi.testclient import TestClient
from dexter_core.api import create_app
from dexter_core.contracts.query import *
from dexter_core.contracts.ingestion import RepositoryStatus
from dexter_core.persistence.evidence import RepositoryHealth
from dexter_core.query import GovernedDataRepository, QueryService, QueryValidationError


class Repo:
    def __init__(self):
        self.stores = 0

    def get_all(self):
        return ()

    def get_by_identity(self, x):
        return None

    def health(self):
        return RepositoryHealth(RepositoryStatus.HEALTHY)

    def store(self, x):
        self.stores += 1


class QueryAPITest(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.service = QueryService(GovernedDataRepository(self.repo))
        self.client = TestClient(create_app(self.service))
        self.q = {
            "request_identity": f"dexter:query-request:{uuid4()}",
            "requested_timestamp": "2026-07-24T17:20:00Z",
            "authority_reference": "authority:test",
        }

    def test_metadata_endpoints_and_openapi(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "healthy"})
        self.assertIn("version", self.client.get("/version").json())
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertIn("/evidence", self.client.get("/openapi.json").json()["paths"])

    def test_all_query_endpoints_are_read_only(self):
        for path in (
            "/evidence",
            "/evidence/missing",
            "/assessments",
            "/assessments/missing",
            "/questions",
            "/answers",
            "/status",
        ):
            response = self.client.get(path, params=self.q)
            self.assertEqual(response.status_code, 200, path)
            self.assertEqual(
                response.json()["request_reference"], self.q["request_identity"]
            )
            self.assertEqual(response.text, json_canonical(response.json()))
        self.assertEqual(self.repo.stores, 0)

    def test_invalid_query_and_parameters(self):
        r = QueryRequest(
            f"dexter:query-request:{uuid4()}",
            QueryType.UNKNOWN,
            "/evidence",
            datetime.now(timezone.utc),
            "a",
        )
        self.assertFalse(r.validate().is_valid)
        self.assertRaises(QueryValidationError, self.service.query, r)
        invalid_endpoint = QueryRequest(
            f"dexter:query-request:{uuid4()}",
            QueryType.QUESTION,
            "/questions/not-an-endpoint",
            datetime.now(timezone.utc),
            "a",
        )
        self.assertFalse(invalid_endpoint.validate().is_valid)
        self.assertEqual(
            self.client.get("/evidence", params={**self.q, "version": "2"}).status_code,
            422,
        )

    def test_serialization_round_trip_and_unknown_rejection(self):
        r = QueryRequest(
            f"dexter:query-request:{uuid4()}",
            QueryType.EVIDENCE,
            "/evidence",
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            "a",
        )
        self.assertEqual(query_request_from_json(query_request_to_json(r)), r)
        response = self.service.query(r)
        restored = query_response_from_json(query_response_to_json(response))
        self.assertEqual(
            query_response_to_json(restored), query_response_to_json(response)
        )
        data = query_request_to_dict(r)
        data["extra"] = 1
        self.assertRaises(ValueError, query_request_from_dict, data)

    def test_deterministic_response_and_repository_compatibility(self):
        r = QueryRequest(
            f"dexter:query-request:{uuid4()}",
            QueryType.STATUS,
            "/status",
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            "a",
        )
        self.assertEqual(
            query_response_to_json(self.service.query(r)),
            query_response_to_json(self.service.query(r)),
        )


def json_canonical(value):
    import json

    return json.dumps(value, sort_keys=True, separators=(",", ":"))
