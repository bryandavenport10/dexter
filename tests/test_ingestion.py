"""Tests for deterministic governed Evidence ingestion."""
import unittest
from datetime import datetime, timezone

from dexter_core.connectors import Connector
from dexter_core.contracts import *
from dexter_core.ingestion import EvidenceIngestionService
from dexter_core.persistence import (DuplicateEvidenceError, EvidenceRepository,
    RepositoryHealth, RepositoryStatus)

NOW=datetime(2026,7,24,17,tzinfo=timezone.utc)
CID="dexter:connector:123e4567-e89b-12d3-a456-426614174000"
COLID="dexter:collection:123e4567-e89b-12d3-a456-426614174001"
CRID="dexter:collection-result:123e4567-e89b-12d3-a456-426614174002"
REQID="dexter:ingestion-request:123e4567-e89b-12d3-a456-426614174003"
SID="dexter:connector-status:123e4567-e89b-12d3-a456-426614174004"
EID="dexter:evidence:123e4567-e89b-12d3-a456-426614174005"
CAP=ConnectorCapability.NODE_OBSERVATION

def item(**changes):
    values=dict(evidence_id=EID,evidence_type=EvidenceType.PROXMOX_NODE,
        source_system="proxmox-ve",source_object="node/pve1",
        observation_timestamp=NOW,collection_timestamp=NOW,
        authority=SourceAuthority("lab","pve1","https://pve.test/api","GET","authref:reader",NOW),
        payload={"status":"online"})
    values.update(changes); return Evidence(**values)

def context(**changes):
    values=dict(collection_id=COLID,connector_id=CID,source_system_id="proxmox-ve",
        requested_capabilities=(CAP,),requested_at=NOW,authority_reference="authority:ops",
        correlation_id="correlation:wp-059",authentication_reference="authref:reader")
    values.update(changes); return ConnectorCollectionContext(**values)

def request(**changes):
    ctx=changes.pop("collection_context",context())
    values=dict(request_id=REQID,connector_id=CID,collection_context=ctx,
        requested_capabilities=ctx.requested_capabilities,requested_at=ctx.requested_at,
        authority_reference=ctx.authority_reference)
    values.update(changes); return IngestionRequest(**values)

class FakeConnector:
    def __init__(self,status=CollectionStatus.SUCCEEDED,evidence=(None,)):
        self.status=status; self.evidence=(item(),) if evidence==(None,) else evidence
        self.health_status=ConnectorStatus.READY; self.collect_error=None; self.calls=0
    @property
    def metadata(self):
        return ConnectorMetadata(CID,"proxmox-ve","1.0","proxmox-ve",(CAP,),"authority:ops")
    def health(self,ctx):
        return ConnectorStatusRecord(SID,CID,"proxmox-ve",self.health_status,NOW,"authority:ops")
    def collect(self,ctx):
        self.calls+=1
        if self.collect_error: raise self.collect_error
        return ConnectorCollectionResult(CRID,ctx.collection_id,CID,"proxmox-ve",self.status,
            NOW,NOW,self.evidence,(),"authority:ops")

class MemoryRepository:
    def __init__(self): self.values={}; self.available=True; self.store_error=None
    def store(self,value):
        if self.store_error: raise self.store_error
        if value.evidence_id in self.values: raise DuplicateEvidenceError(value.evidence_id)
        self.values[value.evidence_id]=value
    def get_by_identity(self,identity): return self.values.get(identity)
    def get_by_source(self,*args): return tuple(self.values.values())
    def get_by_time_window(self,*args): return tuple(self.values.values())
    def get_by_type(self,*args): return tuple(self.values.values())
    def get_by_relationship(self,*args): return tuple(self.values.values())
    def health(self):
        return RepositoryHealth(RepositoryStatus.HEALTHY if self.available else RepositoryStatus.UNAVAILABLE)

class IngestionTests(unittest.TestCase):
    def service(self,connector=None,repository=None):
        return EvidenceIngestionService(connector or FakeConnector(),repository or MemoryRepository())
    def test_protocol_and_successful_repository_ingestion(self):
        connector,repository=FakeConnector(),MemoryRepository()
        self.assertIsInstance(connector,Connector); self.assertIsInstance(repository,EvidenceRepository)
        result=self.service(connector,repository).ingest(request())
        self.assertEqual(result.status,IngestionStatus.SUCCEEDED)
        self.assertEqual(result.stored_evidence_references,(EID,)); self.assertEqual(repository.get_by_identity(EID),item())
        self.assertTrue(result.validate().is_valid)
    def test_empty_collection_succeeds_and_no_data_is_governed(self):
        empty=self.service(FakeConnector(evidence=())).ingest(request())
        self.assertEqual((empty.status,empty.evidence_count,empty.errors),(IngestionStatus.SUCCEEDED,0,()))
        no_data=self.service(FakeConnector(CollectionStatus.NO_DATA,())).ingest(request())
        self.assertEqual(no_data.status,IngestionStatus.NO_DATA)
        self.assertEqual(no_data.errors[0].category,IngestionErrorCategory.NO_DATA)
    def test_duplicate_evidence(self):
        repository=MemoryRepository(); repository.store(item())
        result=self.service(repository=repository).ingest(request())
        self.assertEqual(result.errors[0].category,IngestionErrorCategory.DUPLICATE_EVIDENCE)
    def test_repository_unavailable_and_failure_hide_credentials(self):
        repository=MemoryRepository(); repository.available=False
        result=self.service(repository=repository).ingest(request())
        self.assertEqual(result.errors[0].category,IngestionErrorCategory.REPOSITORY_UNAVAILABLE)
        repository.available=True; repository.store_error=RuntimeError("password=secret")
        result=self.service(repository=repository).ingest(request())
        self.assertEqual(result.repository_status,RepositoryStatus.UNAVAILABLE)
        self.assertNotIn("secret",ingestion_result_to_json(result))
    def test_connector_unavailable_and_failure_hide_credentials(self):
        connector=FakeConnector(); connector.health_status=ConnectorStatus.UNAVAILABLE
        result=self.service(connector).ingest(request())
        self.assertEqual(result.errors[0].category,IngestionErrorCategory.CONNECTOR_UNAVAILABLE)
        connector.health_status=ConnectorStatus.READY; connector.collect_error=RuntimeError("api_token=secret")
        result=self.service(connector).ingest(request()); self.assertNotIn("secret",ingestion_result_to_json(result))
    def test_request_and_evidence_validation_failures(self):
        connector=FakeConnector(); invalid=request(requested_at=NOW.replace(year=2025))
        result=self.service(connector).ingest(invalid)
        self.assertEqual(result.errors[0].category,IngestionErrorCategory.VALIDATION_FAILURE)
        self.assertEqual(connector.calls,0)
        result=self.service(FakeConnector(evidence=(item(revision=0),))).ingest(request())
        self.assertEqual(result.errors[0].category,IngestionErrorCategory.VALIDATION_FAILURE)
    def test_unsupported_capability(self):
        ctx=context(requested_capabilities=(ConnectorCapability.TASK_OBSERVATION,)); connector=FakeConnector()
        result=self.service(connector).ingest(request(collection_context=ctx))
        self.assertEqual(result.status,IngestionStatus.UNSUPPORTED); self.assertEqual(connector.calls,0)
    def test_serialization_strict_round_trip(self):
        result=self.service().ingest(request())
        cases=((request(),ingestion_request_to_dict,ingestion_request_from_dict,ingestion_request_to_json,ingestion_request_from_json),
            (result,ingestion_result_to_dict,ingestion_result_from_dict,ingestion_result_to_json,ingestion_result_from_json))
        for value,to_dict,from_dict,to_json,from_json in cases:
            self.assertEqual(from_dict(to_dict(value)),value); self.assertEqual(to_json(from_json(to_json(value))),to_json(value))
            data=to_dict(value); data["unknown"]=True
            with self.assertRaisesRegex(ValueError,"unknown fields"): from_dict(data)
        self.assertIn('"completed_at":"2026-07-24T17:00:00Z"',ingestion_result_to_json(result))
    def test_deterministic_repeatability(self):
        first=self.service(repository=MemoryRepository()).ingest(request())
        second=self.service(repository=MemoryRepository()).ingest(request())
        self.assertEqual(first,second); self.assertEqual(ingestion_result_to_json(first),ingestion_result_to_json(second))

if __name__=="__main__": unittest.main()
