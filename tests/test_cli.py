"""Tests for Dexter's thin CLI."""

import json
import unittest
from datetime import datetime, timezone
from importlib.metadata import entry_points
from uuid import UUID
from typer.testing import CliRunner
import dexter_core.cli as cli
from dexter_core import GovernedDataRepository, QueryService, QuestionEngine
from dexter_core.connectors.proxmox import ProxmoxConnector
from dexter_core.contracts import *
from dexter_core.contracts.evidence import Evidence, EvidenceType, SourceAuthority
from dexter_core.persistence import RepositoryHealth, RepositoryStatus

NOW = datetime(2026, 7, 24, 17, 40, tzinfo=timezone.utc)
from dexter_core.ingestion import EvidenceIngestionService

EID = "dexter:evidence:123e4567-e89b-12d3-a456-426614174001"
AID = "dexter:assessment:123e4567-e89b-12d3-a456-426614174002"
QID = "dexter:question:123e4567-e89b-12d3-a456-426614174003"
UID = UUID("123e4567-e89b-12d3-a456-426614174099")


def ev():
    return Evidence(
        EID,
        EvidenceType.PROXMOX_VIRTUAL_MACHINE,
        "proxmox-ve",
        "node/pve1/vm/100",
        NOW,
        NOW,
        SourceAuthority(
            "lab",
            "pve1",
            "https://pve.test/api",
            "proxmox-ve-api:get",
            "authref:reader",
            NOW,
        ),
        {"name": "app", "status": "running", "cpu": 0.9},
    )


def ass():
    return Assessment(
        AID,
        AssessmentType.RESOURCE_UTILIZATION,
        "dexter:correlation:primary",
        ("dexter:correlation:supporting",),
        "Resource pressure was observed.",
        "Governed utilization threshold matched.",
        AssessmentConfidence.HIGH,
        NOW,
        "dexter:authority:assessment-engine",
        (EID,),
        (),
    )


def ques():
    return Question(
        QID,
        QuestionType.WHICH,
        "Which virtual machines show resource pressure?",
        NOW,
        "dexter:authority:operator",
    )


class Repo:
    def __init__(self, values=(), healthy=True):
        self.values = {x.evidence_id: x for x in values}
        self.healthy = healthy

    def store(self, x):
        self.values[x.evidence_id] = x

    def get_all(self):
        return tuple(sorted(self.values.values(), key=lambda x: x.evidence_id))

    def get_by_identity(self, x):
        return self.values.get(x)

    def get_by_source(self, *_):
        return self.get_all()

    def get_by_time_window(self, *_):
        return self.get_all()

    def get_by_type(self, *_):
        return self.get_all()

    def get_by_relationship(self, *_):
        return self.get_all()

    def health(self):
        return RepositoryHealth(
            RepositoryStatus.HEALTHY if self.healthy else RepositoryStatus.UNAVAILABLE,
            "memory repository",
        )


class Transport:
    def __init__(self, error=None):
        self.error = error
        self.paths = []

    def get(self, path):
        self.paths.append(path)
        if self.error:
            raise self.error
        return {
            "/cluster/status": {"data": []},
            "/version": {"data": {"version": "8.2"}},
            "/nodes": {"data": []},
        }[path]


def runtime(repo=None, transport=None, assessments=(), questions=(), answers=()):
    repo = repo if repo is not None else Repo((ev(),))
    connector = ProxmoxConnector(
        transport or Transport(),
        cluster_id="lab",
        api_endpoint="https://pve.test/api",
        authentication_context="authref:reader",
        clock=lambda: NOW,
    )
    config = cli.CLIConfig(
        postgres_reference="pgref:dexter",
        proxmox_endpoint="https://pve.test/api",
        proxmox_authentication_reference="authref:reader",
        proxmox_source_system_id="proxmox-ve",
        authority_reference="dexter:authority:operator",
    )
    return cli.CLIRuntime(
        QueryService(GovernedDataRepository(repo, assessments, questions, answers)),
        EvidenceIngestionService(connector, repo),
        lambda: NOW,
        lambda: UID,
        config,
    )


class CLITests(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.old = cli.runtime_factory
        source = ass()
        answer = QuestionEngine(
            authority_reference="dexter:authority:question-engine"
        ).answer(ques(), (source,))
        self.rt = runtime(assessments=(source,), questions=(ques(),), answers=(answer,))
        cli.runtime_factory = lambda: self.rt

    def tearDown(self):
        cli.runtime_factory = self.old

    def runcli(self, *args):
        return self.runner.invoke(cli.app, list(args))

    def test_help(self):
        r = self.runcli("--help")
        self.assertEqual(r.exit_code, 0)
        for x in (
            "version",
            "health",
            "status",
            "evidence",
            "assessments",
            "questions",
            "answers",
            "ingest",
            "ask",
        ):
            self.assertIn(x, r.stdout)

    def test_version_text_and_json(self):
        self.assertEqual(self.runcli("version").stdout, "0.1.0\n")
        self.assertEqual(
            json.loads(self.runcli("version", "--format", "json").stdout),
            {"version": "0.1.0"},
        )

    def test_healthy_and_unhealthy(self):
        self.assertEqual(self.runcli("health").exit_code, 0)
        self.rt = runtime(repo=Repo(healthy=False))
        r = self.runcli("health")
        self.assertEqual(r.exit_code, 1)
        self.assertIn("unhealthy", r.stderr)

    def test_status(self):
        r = self.runcli("status", "--format", "json")
        self.assertEqual(json.loads(r.stdout)[0]["status"], "HEALTHY")

    def test_evidence_list_text_json_and_filters(self):
        self.assertIn(EID, self.runcli("evidence", "list").stdout)
        r = self.runcli(
            "evidence",
            "list",
            "--source",
            "proxmox-ve",
            "--evidence-type",
            "PROXMOX_VIRTUAL_MACHINE",
            "--start",
            "2026-07-24T00:00:00Z",
            "--end",
            "2026-07-25T00:00:00Z",
            "--limit",
            "1",
            "--format",
            "json",
        )
        self.assertEqual(json.loads(r.stdout)[0]["evidence_id"], EID)

    def test_evidence_show_and_not_found(self):
        self.assertEqual(self.runcli("evidence", "show", EID).exit_code, 0)
        r = self.runcli(
            "evidence", "show", "dexter:evidence:123e4567-e89b-12d3-a456-426614174088"
        )
        self.assertEqual(r.exit_code, 3)
        self.assertIn("not found", r.stderr)

    def test_assessment_list_and_show(self):
        self.assertEqual(self.runcli("assessments", "list").exit_code, 0)
        self.assertEqual(self.runcli("assessments", "show", AID).exit_code, 0)

    def test_question_and_answer_lists(self):
        self.assertEqual(
            len(
                json.loads(self.runcli("questions", "list", "--format", "json").stdout)
            ),
            1,
        )
        self.assertEqual(
            len(json.loads(self.runcli("answers", "list", "--format", "json").stdout)),
            1,
        )

    def test_ingest_success_get_only(self):
        transport = Transport()
        self.rt = runtime(repo=Repo(), transport=transport)
        r = self.runcli("ingest", "proxmox", "--format", "json")
        self.assertEqual(r.exit_code, 0)
        self.assertEqual(json.loads(r.stdout)["status"], "SUCCEEDED")
        self.assertEqual(transport.paths, ["/cluster/status", "/version", "/nodes"])

    def test_ingest_failure_hides_credential(self):
        self.rt = runtime(
            repo=Repo(), transport=Transport(RuntimeError("token=very-secret"))
        )
        r = self.runcli("ingest", "proxmox", "--format", "json")
        self.assertEqual(r.exit_code, 4)
        self.assertNotIn("very-secret", r.output)
        self.assertIn("governed collection failure", r.stdout)

    def test_ingest_requires_configuration(self):
        self.rt.config = cli.CLIConfig(authority_reference="dexter:authority:operator")
        self.assertEqual(self.runcli("ingest", "proxmox").exit_code, 2)

    def test_ask_with_and_without_assessment(self):
        r = self.runcli(
            "ask", "Which virtual machines show resource pressure?", "--format", "json"
        )
        self.assertEqual(json.loads(r.stdout)["primary_assessment_reference"], AID)
        self.rt = runtime(assessments=())
        self.assertEqual(self.runcli("ask", "Which VM?").exit_code, 3)

    def test_invalid_inputs(self):
        cases = (
            ("version", "--format", "xml"),
            ("evidence", "list", "--start", "yesterday"),
            (
                "evidence",
                "list",
                "--start",
                "2026-07-25T00:00:00Z",
                "--end",
                "2026-07-24T00:00:00Z",
            ),
            ("evidence", "list", "--limit", "0"),
            ("evidence", "show", "bad"),
            ("ask", "   "),
        )
        for args in cases:
            with self.subTest(args=args):
                self.assertEqual(self.runcli(*args).exit_code, 2)

    def test_deterministic_output(self):
        a = self.runcli("evidence", "list", "--format", "json").stdout
        self.assertEqual(a, self.runcli("evidence", "list", "--format", "json").stdout)

    def test_console_entry_point(self):
        matches = [
            x for x in entry_points(group="console_scripts") if x.name == "dexter"
        ]
        self.assertTrue(matches)
        self.assertEqual(matches[0].value, "dexter_core.cli:app")


if __name__ == "__main__":
    unittest.main()
