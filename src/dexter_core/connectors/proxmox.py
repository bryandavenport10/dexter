"""Read-only Proxmox VE observation and evidence ingestion."""
from __future__ import annotations
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid5
from ..contracts.connector import (
    CollectionStatus, ConnectorCapability, ConnectorCollectionContext,
    ConnectorCollectionResult, ConnectorError, ConnectorErrorCategory,
    ConnectorMetadata, ConnectorStatus, ConnectorStatusRecord,
)
from ..contracts.evidence import Evidence, EvidenceType, SourceAuthority
from ..contracts.observation import ObservationType, ProxmoxObservation, utc_timestamp

class ProxmoxReadTransport(Protocol):
    """Minimal transport boundary: implementations expose GET only."""
    def get(self, path: str) -> Any: ...

TYPES = {ObservationType.CLUSTER: EvidenceType.PROXMOX_CLUSTER, ObservationType.NODE: EvidenceType.PROXMOX_NODE, ObservationType.VIRTUAL_MACHINE: EvidenceType.PROXMOX_VIRTUAL_MACHINE, ObservationType.CONTAINER: EvidenceType.PROXMOX_CONTAINER, ObservationType.STORAGE: EvidenceType.PROXMOX_STORAGE, ObservationType.TASK: EvidenceType.PROXMOX_TASK}

PROXMOX_CAPABILITIES = (
    ConnectorCapability.CLUSTER_OBSERVATION, ConnectorCapability.NODE_OBSERVATION,
    ConnectorCapability.VIRTUAL_MACHINE_OBSERVATION, ConnectorCapability.CONTAINER_OBSERVATION,
    ConnectorCapability.STORAGE_OBSERVATION, ConnectorCapability.TASK_OBSERVATION,
    ConnectorCapability.HEALTH_STATUS_OBSERVATION, ConnectorCapability.VERSION_OBSERVATION,
)

class ProxmoxConnector:
    """Collects Proxmox state without providing mutation capability."""
    def __init__(self, transport: ProxmoxReadTransport, *, cluster_id: str, api_endpoint: str, authentication_context: str, clock: Callable[[], datetime] | None = None) -> None:
        for name, value in (("cluster_id", cluster_id), ("api_endpoint", api_endpoint), ("authentication_context", authentication_context)):
            if not isinstance(value, str) or not value.strip(): raise ValueError(f"{name} is required")
        parsed_endpoint = urlsplit(api_endpoint)
        if not parsed_endpoint.scheme or not parsed_endpoint.netloc or parsed_endpoint.username is not None or parsed_endpoint.password is not None or parsed_endpoint.query:
            raise ValueError("api_endpoint must be an absolute secret-free URL without a query")
        self._transport, self.cluster_id = transport, cluster_id.strip()
        self.api_endpoint, self.authentication_context = api_endpoint.rstrip("/"), authentication_context.strip()
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    @property
    def metadata(self) -> ConnectorMetadata:
        connector_id = f"dexter:connector:{uuid5(NAMESPACE_URL, f'proxmox-ve|{self.cluster_id}')}"
        return ConnectorMetadata(connector_id, "proxmox-ve", "1.0", "proxmox-ve", PROXMOX_CAPABILITIES, f"proxmox:cluster:{self.cluster_id}")

    def collect(self, context: ConnectorCollectionContext | None = None) -> tuple[ProxmoxObservation, ...] | ConnectorCollectionResult:
        """Collect legacy observations, or a governed result when context is supplied."""
        if context is not None:
            return self._collect_governed(context)
        return self._collect_observations()

    def _collect_observations(self) -> tuple[ProxmoxObservation, ...]:
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
        observations = self._collect_observations()
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

    def _collect_governed(self, context: ConnectorCollectionContext) -> ConnectorCollectionResult:
        context.validate().raise_for_errors()
        metadata = self.metadata
        if context.connector_id != metadata.connector_id or context.source_system_id != metadata.source_system_id:
            raise ValueError("collection context does not identify this connector")
        requested = set(context.requested_capabilities)
        common = dict(result_id=f"dexter:collection-result:{uuid5(NAMESPACE_URL, context.collection_id)}", collection_context_id=context.collection_id, connector_id=metadata.connector_id, source_system_id=metadata.source_system_id, started_at=context.requested_at, completed_at=context.requested_at, authority_reference=context.authority_reference)
        if requested.difference(metadata.capabilities):
            result = ConnectorCollectionResult(status=CollectionStatus.UNSUPPORTED, evidence=(), errors=(), **common)
            result.validate().raise_for_errors()
            return result
        try:
            observations = self._collect_observations()
            evidence = tuple(self.to_evidence(item, collection_timestamp=context.requested_at) for item in observations if _capability_for(item.observation_type) in requested)
            result = ConnectorCollectionResult(status=CollectionStatus.SUCCEEDED if evidence else CollectionStatus.NO_DATA, evidence=evidence, errors=(), **common)
        except Exception as exc:
            category = ConnectorErrorCategory.INVALID_RESPONSE if isinstance(exc, (TypeError, ValueError, KeyError)) else ConnectorErrorCategory.CONNECTIVITY
            error = ConnectorError(error_id=f"dexter:connector-error:{uuid5(NAMESPACE_URL, f'{context.collection_id}|{category.value}')}", connector_id=metadata.connector_id, collection_context_id=context.collection_id, category=category, message="Proxmox collection failed; transport details were withheld", occurred_at=context.requested_at, retryable=category is ConnectorErrorCategory.CONNECTIVITY, authority_reference=context.authority_reference)
            result = ConnectorCollectionResult(status=CollectionStatus.FAILED, evidence=(), errors=(error,), **common)
        result.validate().raise_for_errors()
        return result

    def health(self, context: ConnectorCollectionContext) -> ConnectorStatusRecord:
        context.validate().raise_for_errors()
        if context.connector_id != self.metadata.connector_id:
            raise ValueError("collection context does not identify this connector")
        value = ConnectorStatusRecord(status_id=f"dexter:connector-status:{uuid5(NAMESPACE_URL, context.collection_id)}", connector_id=self.metadata.connector_id, source_system_id=self.metadata.source_system_id, status=ConnectorStatus.READY, observed_at=context.requested_at, authority_reference=context.authority_reference)
        value.validate().raise_for_errors()
        return value

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

def _capability_for(value: ObservationType) -> ConnectorCapability:
    return {ObservationType.CLUSTER: ConnectorCapability.CLUSTER_OBSERVATION, ObservationType.NODE: ConnectorCapability.NODE_OBSERVATION, ObservationType.VIRTUAL_MACHINE: ConnectorCapability.VIRTUAL_MACHINE_OBSERVATION, ObservationType.CONTAINER: ConnectorCapability.CONTAINER_OBSERVATION, ObservationType.STORAGE: ConnectorCapability.STORAGE_OBSERVATION, ObservationType.TASK: ConnectorCapability.TASK_OBSERVATION}[value]
