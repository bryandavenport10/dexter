"""Read-only Proxmox VE observation and evidence ingestion."""
from __future__ import annotations
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import NAMESPACE_URL, uuid5
from ..contracts.evidence import Evidence, EvidenceType, SourceAuthority
from ..contracts.observation import ObservationType, ProxmoxObservation, utc_timestamp

class ProxmoxReadTransport(Protocol):
    """Minimal transport boundary: implementations expose GET only."""
    def get(self, path: str) -> Any: ...

TYPES = {ObservationType.CLUSTER: EvidenceType.PROXMOX_CLUSTER, ObservationType.NODE: EvidenceType.PROXMOX_NODE, ObservationType.VIRTUAL_MACHINE: EvidenceType.PROXMOX_VIRTUAL_MACHINE, ObservationType.CONTAINER: EvidenceType.PROXMOX_CONTAINER, ObservationType.STORAGE: EvidenceType.PROXMOX_STORAGE, ObservationType.TASK: EvidenceType.PROXMOX_TASK}

class ProxmoxConnector:
    """Collects Proxmox state without providing mutation capability."""
    def __init__(self, transport: ProxmoxReadTransport, *, cluster_id: str, api_endpoint: str, authentication_context: str, clock: Callable[[], datetime] | None = None) -> None:
        for name, value in (("cluster_id", cluster_id), ("api_endpoint", api_endpoint), ("authentication_context", authentication_context)):
            if not isinstance(value, str) or not value.strip(): raise ValueError(f"{name} is required")
        self._transport, self.cluster_id = transport, cluster_id.strip()
        self.api_endpoint, self.authentication_context = api_endpoint.rstrip("/"), authentication_context.strip()
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def collect(self) -> tuple[ProxmoxObservation, ...]:
        now = utc_timestamp(self._clock(), "collection timestamp")
        result = [ProxmoxObservation(ObservationType.CLUSTER, f"cluster/{self.cluster_id}", now, {"members": self._items("/cluster/status"), "version": selected(self._object("/version"), ("version", "release", "repoid"))})]
        for node in self._items("/nodes"):
            name, base = required(node, "node"), f"/nodes/{required(node, 'node')}"
            status = self._object(f"{base}/status")
            result.append(ProxmoxObservation(ObservationType.NODE, f"node/{name}", observed(status, now), selected({**node, **status}, ("node", "status", "online", "uptime", "cpu", "maxcpu", "mem", "maxmem", "rootfs", "loadavg", "kernel", "pveversion"))))
            for kind, endpoint, label in ((ObservationType.VIRTUAL_MACHINE, "qemu", "vm"), (ObservationType.CONTAINER, "lxc", "container")):
                for guest in self._items(f"{base}/{endpoint}"):
                    vmid = required(guest, "vmid")
                    current = self._object(f"{base}/{endpoint}/{vmid}/status/current")
                    config = self._object(f"{base}/{endpoint}/{vmid}/config")
                    payload = selected({**guest, **current}, ("vmid", "name", "status", "qmpstatus", "uptime", "cpu", "cpus", "mem", "maxmem", "disk", "maxdisk", "netin", "netout", "pid", "template"))
                    interfaces = {key: config[key] for key in sorted(config) if key.startswith("net")}
                    if interfaces: payload["network_interfaces"] = interfaces
                    result.append(ProxmoxObservation(kind, f"node/{name}/{label}/{vmid}", observed(current, now), payload))
            for storage in self._items(f"{base}/storage"):
                sid = required(storage, "storage")
                result.append(ProxmoxObservation(ObservationType.STORAGE, f"node/{name}/storage/{sid}", observed(storage, now), selected(storage, ("storage", "type", "content", "active", "enabled", "shared", "total", "used", "avail"))))
            for task in self._items(f"{base}/tasks"):
                upid = required(task, "upid")
                result.append(ProxmoxObservation(ObservationType.TASK, f"node/{name}/task/{upid}", observed(task, now), selected(task, ("upid", "type", "id", "user", "status", "starttime", "endtime", "node"))))
        return tuple(result)

    def ingest(self) -> tuple[Evidence, ...]:
        observations = self.collect()
        collected = utc_timestamp(self._clock(), "collection timestamp")
        result = tuple(self.to_evidence(item, collection_timestamp=collected) for item in observations)
        for item in result: item.validate().raise_for_errors()
        return result

    def to_evidence(self, observation: ProxmoxObservation, *, collection_timestamp: datetime | None = None) -> Evidence:
        collected = utc_timestamp(collection_timestamp or self._clock(), "collection_timestamp")
        node = source_node(observation.source_object)
        material = f"{self.cluster_id}|{observation.observation_type.value}|{observation.source_object}|{observation.observed_at.isoformat()}"
        relationships = (f"proxmox:cluster:{self.cluster_id}",) + (() if node is None else (f"proxmox:node:{node}",))
        return Evidence(evidence_id=f"dexter:evidence:{uuid5(NAMESPACE_URL, material)}", evidence_type=TYPES[observation.observation_type], source_system="proxmox-ve", source_object=observation.source_object, observation_timestamp=observation.observed_at, collection_timestamp=collected, authority=SourceAuthority(self.cluster_id, node, self.api_endpoint, "proxmox-ve-api:get", self.authentication_context, collected), payload=observation.payload, relationships=relationships)

    def _items(self, path: str) -> tuple[Mapping[str, Any], ...]:
        value = unwrap(self._transport.get(path))
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)) or not all(isinstance(item, Mapping) for item in value): raise ValueError(f"Proxmox response for {path} must contain an array of objects")
        return tuple(value)

    def _object(self, path: str) -> Mapping[str, Any]:
        value = unwrap(self._transport.get(path))
        if not isinstance(value, Mapping): raise ValueError(f"Proxmox response for {path} must contain an object")
        return value

def unwrap(response: Any) -> Any:
    if not isinstance(response, Mapping) or "data" not in response: raise ValueError("Proxmox response must be an object containing data")
    return response["data"]
def required(value: Mapping[str, Any], field: str) -> str:
    item = value.get(field)
    if item is None or not str(item).strip(): raise ValueError(f"Proxmox object is missing {field}")
    return str(item).strip()
def selected(value: Mapping[str, Any], fields: tuple[str, ...]) -> dict[str, Any]: return {field: value[field] for field in fields if field in value}
def observed(value: Mapping[str, Any], fallback: datetime) -> datetime:
    timestamp = value.get("timestamp")
    if timestamp is None: return fallback
    if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)): raise ValueError("Proxmox timestamp must be a Unix timestamp")
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)
def source_node(source: str) -> str | None:
    parts = source.split("/")
    return parts[1] if len(parts) >= 2 and parts[0] == "node" else None
