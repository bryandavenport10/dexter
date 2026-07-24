"""Tests for governed connector contracts and the reusable Proxmox boundary."""
import unittest
from datetime import timedelta
from dexter_core.connectors import Connector, PROXMOX_CAPABILITIES, ProxmoxConnector
from dexter_core.contracts import *
from test_proxmox_evidence import NOW, connector
CID="dexter:connector:123e4567-e89b-12d3-a456-426614174000"
COLID="dexter:collection:123e4567-e89b-12d3-a456-426614174001"
RID="dexter:collection-result:123e4567-e89b-12d3-a456-426614174002"
EID="dexter:connector-error:123e4567-e89b-12d3-a456-426614174003"
SID="dexter:connector-status:123e4567-e89b-12d3-a456-426614174004"

def context(value=None, **changes):
    fields=dict(collection_id=COLID,connector_id=value.metadata.connector_id if value else CID,source_system_id="proxmox-ve",requested_capabilities=(ConnectorCapability.NODE_OBSERVATION,),requested_at=NOW,authority_reference="authority:ops",correlation_id="request:57",authentication_reference="authref:reader")
    fields.update(changes); return ConnectorCollectionContext(**fields)

def error(**changes):
    fields=dict(error_id=EID,connector_id=CID,collection_context_id=COLID,category=ConnectorErrorCategory.CONNECTIVITY,message="Source unavailable",occurred_at=NOW,retryable=True,authority_reference="authority:ops")
    fields.update(changes); return ConnectorError(**fields)

def result(**changes):
    fields=dict(result_id=RID,collection_context_id=COLID,connector_id=CID,source_system_id="proxmox-ve",status=CollectionStatus.SUCCEEDED,started_at=NOW,completed_at=NOW,evidence=(),errors=(),authority_reference="authority:ops")
    fields.update(changes); return ConnectorCollectionResult(**fields)

class ConnectorFrameworkTests(unittest.TestCase):
    def test_metadata_and_duplicate_capabilities(self):
        value=ConnectorMetadata(CID,"proxmox-ve","1.0","proxmox-ve",(ConnectorCapability.NODE_OBSERVATION,ConnectorCapability.CLUSTER_OBSERVATION),"authority:ops")
        self.assertTrue(value.validate().is_valid); self.assertEqual(value.capabilities,tuple(sorted(value.capabilities,key=lambda x:x.value)))
        with self.assertRaisesRegex(ValueError,"unique"): ConnectorMetadata(CID,"p","1","s",(ConnectorCapability.NODE_OBSERVATION,)*2,"a")
    def test_context_validation(self):
        self.assertTrue(context().validate().is_valid)
        self.assertIn("missing_authority",{x.code for x in context(authority_reference="").validate().issues})
        self.assertIn("invalid_authentication_reference",{x.code for x in context(authentication_reference="password=secret").validate().issues})
        with self.assertRaisesRegex(ValueError,"unique"): context(requested_capabilities=(ConnectorCapability.NODE_OBSERVATION,)*2)
    def test_result_validation(self):
        for status in (CollectionStatus.SUCCEEDED,CollectionStatus.PARTIALLY_SUCCEEDED,CollectionStatus.FAILED): self.assertTrue(result(status=status,errors=(error(),) if status is not CollectionStatus.SUCCEEDED else ()).validate().is_valid)
        self.assertIn("completed_before_started",{x.code for x in result(completed_at=NOW-timedelta(seconds=1)).validate().issues})
        self.assertIn("unknown_collection_status",{x.code for x in result(status=CollectionStatus.UNKNOWN).validate().issues})
        evidence=connector().ingest()[0]; self.assertIn("duplicate_evidence",{x.code for x in result(evidence=(evidence,evidence)).validate().issues})
    def test_status_and_errors(self):
        status=ConnectorStatusRecord(SID,CID,"proxmox-ve",ConnectorStatus.UNKNOWN,NOW,"authority:ops")
        self.assertIn("unknown_connector_status",{x.code for x in status.validate().issues}); self.assertTrue(error().validate().is_valid)
        self.assertIn("unknown_error_category",{x.code for x in error(category=ConnectorErrorCategory.UNKNOWN).validate().issues})
        self.assertIn("invalid_error_category",{x.code for x in error(category="OTHER").validate().issues})
        for msg in ("password=secret","Authorization: Bearer abc","https://host/api?credential=x","https://host/api?token=x"): self.assertIn("unsafe_error_message",{x.code for x in error(message=msg).validate().issues})
    def test_round_trips_and_strict_fields(self):
        metadata=ConnectorMetadata(CID,"proxmox-ve","1.0","proxmox-ve",(),"authority:ops"); status=ConnectorStatusRecord(SID,CID,"proxmox-ve",ConnectorStatus.READY,NOW,"authority:ops")
        cases=((metadata,connector_metadata_to_dict,connector_metadata_from_dict,connector_metadata_to_json,connector_metadata_from_json),(context(),collection_context_to_dict,collection_context_from_dict,collection_context_to_json,collection_context_from_json),(status,connector_status_to_dict,connector_status_from_dict,connector_status_to_json,connector_status_from_json),(error(),connector_error_to_dict,connector_error_from_dict,connector_error_to_json,connector_error_from_json),(result(errors=(error(),)),collection_result_to_dict,collection_result_from_dict,collection_result_to_json,collection_result_from_json))
        for value,to_dict,from_dict,to_json,from_json in cases:
            self.assertEqual(from_dict(to_dict(value)),value); self.assertEqual(to_json(from_json(to_json(value))),to_json(value)); data=to_dict(value); data["unknown"]=True
            with self.assertRaisesRegex(ValueError,"unknown fields"): from_dict(data)
    def test_proxmox_framework_and_get_only(self):
        value=connector(); self.assertIsInstance(value,Connector); self.assertEqual(value.metadata.capabilities,tuple(sorted(PROXMOX_CAPABILITIES,key=lambda x:x.value)))
        requested=context(value,requested_capabilities=PROXMOX_CAPABILITIES[:6]); first=value.collect(requested); self.assertEqual(first,value.collect(requested)); self.assertEqual(first.status,CollectionStatus.SUCCEEDED); self.assertTrue(first.validate().is_valid); self.assertEqual(value.health(requested).status,ConnectorStatus.READY)
        self.assertFalse(any(hasattr(value,name) for name in ("post","put","patch","delete")))
    def test_safe_governed_failure(self):
        class Broken:
            def get(self,path): raise RuntimeError("password=secret Authorization: Bearer abc")
        value=ProxmoxConnector(Broken(),cluster_id="lab",api_endpoint="https://pve.test/api",authentication_context="token-id:reader",clock=lambda:NOW); governed=value.collect(context(value))
        self.assertEqual(governed.status,CollectionStatus.FAILED); self.assertTrue(governed.validate().is_valid); self.assertNotIn("secret",collection_result_to_json(governed)); self.assertFalse(any(hasattr(value._transport,n) for n in ("post","put","patch","delete")))
