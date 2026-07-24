import json
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from dexter_core.connectors import ProxmoxConnector
from dexter_core.contracts import Evidence, EvidenceType, ObservationType, SourceAuthority, evidence_from_dict, evidence_from_json, evidence_to_dict, evidence_to_json

NOW = datetime(2026, 7, 24, 3, 5, tzinfo=timezone.utc)

class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.responses = {
            "/cluster/status": [{"type": "cluster", "name": "lab", "quorate": 1}, {"type": "node", "name": "pve1", "online": 1}],
            "/version": {"version": "8.4.1", "release": "8.4", "repoid": "abc", "raw": "excluded"},
            "/nodes": [{"node": "pve1", "status": "online", "cpu": .1, "mem": 100, "maxmem": 1000}],
            "/nodes/pve1/status": {"timestamp": NOW.timestamp(), "uptime": 500, "cpu": .2, "rootfs": {"used": 20}, "pveversion": "pve-manager/8.4.1", "secret": "excluded"},
            "/nodes/pve1/qemu": [{"vmid": 100, "name": "web", "status": "running"}],
            "/nodes/pve1/qemu/100/status/current": {"timestamp": NOW.timestamp(), "cpu": .3, "mem": 200, "maxmem": 400, "disk": 50, "maxdisk": 100},
            "/nodes/pve1/qemu/100/config": {"net0": "virtio=AA:BB:CC:DD:EE:FF,bridge=vmbr0", "description": "excluded"},
            "/nodes/pve1/lxc": [{"vmid": 200, "name": "dns", "status": "stopped"}],
            "/nodes/pve1/lxc/200/status/current": {"timestamp": NOW.timestamp(), "cpu": 0, "mem": 0, "maxmem": 200, "disk": 20, "maxdisk": 40},
            "/nodes/pve1/lxc/200/config": {"net0": "name=eth0,bridge=vmbr0", "unprivileged": 1},
            "/nodes/pve1/storage": [{"storage": "local-zfs", "type": "zfspool", "active": 1, "total": 1000, "used": 300, "avail": 700}],
            "/nodes/pve1/tasks": [{"upid": "UPID:pve1:1", "type": "vzdump", "status": "OK", "starttime": NOW.timestamp(), "endtime": NOW.timestamp()}],
        }
    def get(self, path: str):
        self.calls.append(path)
        return {"data": self.responses[path]}

def connector() -> ProxmoxConnector:
    return ProxmoxConnector(FakeTransport(), cluster_id="lab", api_endpoint="https://pve.test:8006/api2/json", authentication_context="token-id:collector@pve!dexter", clock=lambda: NOW)

def sample(**changes: object) -> Evidence:
    values: dict[str, object] = {"evidence_id": "dexter:evidence:123e4567-e89b-12d3-a456-426614174000", "evidence_type": EvidenceType.PROXMOX_NODE, "source_system": "proxmox-ve", "source_object": "node/pve1", "observation_timestamp": NOW, "collection_timestamp": NOW, "authority": SourceAuthority("lab", "pve1", "https://pve.test/api2/json", "proxmox-ve-api:get", "token-id:collector", NOW), "payload": {"status": "online"}, "relationships": ("proxmox:cluster:lab",)}
    values.update(changes)
    return Evidence(**values)  # type: ignore[arg-type]

class ProxmoxEvidenceTests(unittest.TestCase):
    def test_collects_and_normalizes_all_evidence_types(self) -> None:
        observations = connector().collect()
        self.assertEqual([item.observation_type for item in observations], [ObservationType.CLUSTER, ObservationType.NODE, ObservationType.VIRTUAL_MACHINE, ObservationType.CONTAINER, ObservationType.STORAGE, ObservationType.TASK])
        self.assertIn("bridge=vmbr0", observations[2].payload["network_interfaces"]["net0"])
        self.assertNotIn("secret", observations[1].payload)
        self.assertNotIn("raw", observations[0].payload["version"])

    def test_node_vm_container_cluster_and_storage_evidence(self) -> None:
        evidence = connector().ingest()
        expected = {EvidenceType.PROXMOX_CLUSTER, EvidenceType.PROXMOX_NODE, EvidenceType.PROXMOX_VIRTUAL_MACHINE, EvidenceType.PROXMOX_CONTAINER, EvidenceType.PROXMOX_STORAGE, EvidenceType.PROXMOX_TASK}
        self.assertEqual({item.evidence_type for item in evidence}, expected)
        self.assertTrue(all(item.validate().is_valid for item in evidence))
        self.assertEqual(evidence[1].authority.node, "pve1")

    def test_connector_is_read_only_and_deterministic(self) -> None:
        value = connector()
        first, second = value.ingest(), value.ingest()
        self.assertEqual(first, second)
        self.assertFalse(any(hasattr(value, name) for name in ("post", "put", "delete", "patch")))

    def test_missing_authority(self) -> None:
        authority = SourceAuthority("", "pve1", "", "", "", NOW)
        issues = sample(authority=authority).validate().issues
        self.assertEqual({issue.code for issue in issues}, {"missing_authority"})

    def test_missing_and_naive_timestamp(self) -> None:
        data = evidence_to_dict(sample())
        del data["observation_timestamp"]
        with self.assertRaisesRegex(ValueError, "missing required fields"): evidence_from_dict(data)
        with self.assertRaisesRegex(ValueError, "timezone-aware"): sample(observation_timestamp=datetime(2026, 7, 24))

    def test_timestamp_order_and_canonical_utc(self) -> None:
        value = sample(observation_timestamp=NOW, collection_timestamp=NOW - timedelta(seconds=1))
        self.assertEqual(value.validate().issues[0].code, "invalid_timestamp_order")
        shifted = sample(observation_timestamp=NOW.astimezone(timezone(timedelta(hours=-4))))
        self.assertEqual(json.loads(evidence_to_json(shifted))["observation_timestamp"], "2026-07-24T03:05:00Z")

    def test_invalid_and_unknown_evidence_type(self) -> None:
        self.assertEqual(sample(evidence_type="OTHER").validate().issues[0].code, "invalid_evidence_type")
        data = evidence_to_dict(sample()); data["evidence_type"] = "OTHER"
        with self.assertRaisesRegex(ValueError, "EvidenceType"): evidence_from_dict(data)

    def test_serialization_round_trip_and_strict_fields(self) -> None:
        value = sample(payload={"z": [2, 1], "a": {"state": "online"}})
        self.assertEqual(evidence_from_dict(evidence_to_dict(value)), value)
        payload = evidence_to_json(value)
        self.assertEqual(evidence_to_json(evidence_from_json(payload)), payload)
        data = evidence_to_dict(value); data["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "unknown fields"): evidence_from_dict(data)

    def test_evidence_is_deeply_immutable(self) -> None:
        value = sample(payload={"nested": {"state": "online"}, "items": [1]})
        with self.assertRaises(TypeError): value.payload["new"] = True  # type: ignore[index]
        with self.assertRaises(TypeError): value.payload["nested"]["state"] = "offline"  # type: ignore[index]
        with self.assertRaises(FrozenInstanceError): value.revision = 2  # type: ignore[misc]

    def test_version_revision_payload_source_and_identity_validation(self) -> None:
        self.assertEqual(sample(revision=0).validate().issues[0].code, "invalid_revision")
        self.assertEqual(sample(version="2.0").validate().issues[0].code, "unsupported_version")
        self.assertEqual(sample(payload={}).validate().issues[0].code, "missing_payload")
        self.assertEqual(sample(source_system="").validate().issues[0].code, "missing_source")
        self.assertEqual(sample(evidence_id="bad").validate().issues[0].code, "invalid_evidence_identity")

    def test_authority_does_not_contain_credentials(self) -> None:
        authority = evidence_to_dict(connector().ingest()[1])["authority"]
        self.assertEqual(set(authority), {"proxmox_cluster", "node", "api_endpoint", "collection_method", "authentication_context", "asserted_at"})
        self.assertNotIn("password", authority)
        self.assertNotIn("token", authority)

if __name__ == "__main__": unittest.main()
