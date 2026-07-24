"""Repository compatibility tests for immutable Evidence persistence."""
import unittest
from datetime import datetime, timedelta, timezone
from dexter_core.contracts import Evidence, EvidenceType, SourceAuthority, evidence_to_json
from dexter_core.persistence import (DuplicateEvidenceError, EvidenceRepository,
    PostgreSQLEvidenceRepository, RepositoryStatus)
from dexter_core.persistence.evidence import SCHEMA_SQL

NOW = datetime(2026, 7, 24, 16, 50, tzinfo=timezone.utc)

def item(suffix="001", **changes):
    values = dict(evidence_id=f"dexter:evidence:123e4567-e89b-12d3-a456-426614174{suffix}",
        evidence_type=EvidenceType.PROXMOX_NODE, source_system="proxmox-ve",
        source_object=f"node/pve{suffix[-1]}", observation_timestamp=NOW,
        collection_timestamp=NOW + timedelta(seconds=1),
        authority=SourceAuthority("lab", "pve1", "https://pve.test/api", "GET",
                                  "authref:reader", NOW),
        payload={"status": "online"}, relationships=("proxmox:cluster:lab",))
    values.update(changes)
    return Evidence(**values)

class UniqueViolation(Exception):
    sqlstate = "23505"

class Database:
    def __init__(self): self.rows = {}; self.schema = False; self.available = True
    def connect(self):
        if not self.available: raise RuntimeError("database unavailable")
        return Connection(self)

class Connection:
    def __init__(self, database): self.database = database
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def cursor(self): return Cursor(self.database)

class Cursor:
    def __init__(self, database): self.database = database; self.results = []
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def execute(self, sql, params=()):
        if sql == SCHEMA_SQL: self.database.schema = True; return
        if sql == "SELECT 1": self.results = [(1,)]; return
        if "INSERT INTO" in sql:
            if params[0] in self.database.rows: raise UniqueViolation()
            self.database.rows[params[0]] = params
            return
        rows = list(self.database.rows.values())
        if "evidence_id =" in sql: rows = [r for r in rows if r[0] == params[0]]
        elif "source_system =" in sql:
            rows = [r for r in rows if r[2] == params[0]]
            if "source_object =" in sql: rows = [r for r in rows if r[3] == params[1]]
        elif "observation_timestamp >=" in sql: rows = [r for r in rows if params[0] <= r[4] <= params[1]]
        elif "evidence_type =" in sql: rows = [r for r in rows if r[1] == params[0]]
        elif "relationships @>" in sql: rows = [r for r in rows if params[0][0] in r[6]]
        if "ORDER BY" in sql: rows.sort(key=lambda r: (r[4], r[0]))
        self.results = [(r[9],) for r in rows]
    def fetchone(self): return self.results[0] if self.results else None
    def fetchall(self): return self.results

class EvidencePersistenceTests(unittest.TestCase):
    def setUp(self):
        self.database = Database(); self.repository = PostgreSQLEvidenceRepository(self.database.connect)
        self.first = item("001"); self.second = item("002", observation_timestamp=NOW-timedelta(hours=1),
            collection_timestamp=NOW-timedelta(minutes=59), source_system="other",
            evidence_type=EvidenceType.PROXMOX_STORAGE, relationships=("storage:shared",))

    def test_schema_and_repository_compatibility(self):
        self.repository.initialize_schema(); self.assertTrue(self.database.schema)
        self.assertIsInstance(self.repository, EvidenceRepository)
        self.assertIn("PRIMARY KEY", SCHEMA_SQL); self.assertNotIn("UPDATE", SCHEMA_SQL.upper())

    def test_store_and_retrieve_by_identity(self):
        self.repository.store(self.first)
        self.assertEqual(self.repository.get_by_identity(self.first.evidence_id), self.first)
        self.assertIsNone(self.repository.get_by_identity(item("099").evidence_id))

    def test_canonical_serialization_is_stored_unchanged(self):
        self.repository.store(self.first)
        self.assertEqual(self.database.rows[self.first.evidence_id][9], evidence_to_json(self.first))

    def test_duplicate_identity_is_rejected_without_replacement(self):
        self.repository.store(self.first)
        changed = item("001", payload={"status": "offline"}, revision=2)
        with self.assertRaises(DuplicateEvidenceError): self.repository.store(changed)
        self.assertEqual(self.repository.get_by_identity(self.first.evidence_id), self.first)

    def test_source_queries(self):
        self.repository.store(self.first); self.repository.store(self.second)
        self.assertEqual(self.repository.get_by_source("proxmox-ve"), (self.first,))
        self.assertEqual(self.repository.get_by_source("proxmox-ve", "node/pve1"), (self.first,))

    def test_time_window_is_inclusive_and_deterministic(self):
        third = item("003", observation_timestamp=NOW,
                     collection_timestamp=NOW+timedelta(seconds=2))
        for value in (self.first, self.second, third): self.repository.store(value)
        self.assertEqual(self.repository.get_by_time_window(NOW, NOW), (self.first, third))
        with self.assertRaisesRegex(ValueError, "end cannot precede"):
            self.repository.get_by_time_window(NOW, NOW-timedelta(seconds=1))

    def test_type_query(self):
        self.repository.store(self.first); self.repository.store(self.second)
        self.assertEqual(self.repository.get_by_type(EvidenceType.PROXMOX_STORAGE), (self.second,))

    def test_relationship_query(self):
        self.repository.store(self.first); self.repository.store(self.second)
        self.assertEqual(self.repository.get_by_relationship("storage:shared"), (self.second,))

    def test_health(self):
        self.assertEqual(self.repository.health().status, RepositoryStatus.HEALTHY)
        self.database.available = False
        health = self.repository.health()
        self.assertEqual(health.status, RepositoryStatus.UNAVAILABLE); self.assertFalse(health.is_healthy)

    def test_invalid_evidence_is_rejected_before_connection(self):
        invalid = item("004", revision=0); self.database.available = False
        with self.assertRaisesRegex(ValueError, "revision must be a positive integer"):
            self.repository.store(invalid)

    def test_query_input_validation(self):
        with self.assertRaisesRegex(ValueError, "source_system is required"):
            self.repository.get_by_source(" ")
        with self.assertRaises(TypeError): self.repository.get_by_type("PROXMOX_NODE")
        with self.assertRaisesRegex(ValueError, "relationship is required"):
            self.repository.get_by_relationship("")

    def test_new_repository_instance_reads_existing_database(self):
        self.repository.store(self.first)
        restarted = PostgreSQLEvidenceRepository(self.database.connect)
        self.assertEqual(restarted.get_by_identity(self.first.evidence_id), self.first)

if __name__ == "__main__": unittest.main()
