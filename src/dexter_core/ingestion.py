"""Deterministic orchestration from governed connector output to Evidence storage."""
from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from .connectors.base import Connector
from .contracts.connector import CollectionStatus, ConnectorStatus
from .contracts.ingestion import (
    IngestionError,
    IngestionErrorCategory,
    IngestionRequest,
    IngestionResult,
    IngestionStatus,
)
from .persistence.evidence import (
    DuplicateEvidenceError,
    EvidenceRepository,
    RepositoryStatus,
)


class EvidenceIngestionService:
    """Coordinates validation, collection, and immutable Evidence persistence."""

    def __init__(
        self, connector: Connector, repository: EvidenceRepository
    ) -> None:
        if not all(
            callable(getattr(connector, name, None))
            for name in ("collect", "health")
        ):
            raise TypeError("connector must implement Connector")
        if not all(
            callable(getattr(repository, name, None))
            for name in (
                "store",
                "get_by_identity",
                "get_by_source",
                "get_by_time_window",
                "get_by_type",
                "get_by_relationship",
                "health",
            )
        ):
            raise TypeError("repository must implement EvidenceRepository")
        self._connector = connector
        self._repository = repository

    def ingest(self, request: IngestionRequest) -> IngestionResult:
        if not isinstance(request, IngestionRequest):
            raise TypeError("request must be IngestionRequest")

        request_issues = request.validate()
        if not request_issues.is_valid:
            return self._failure(
                request,
                IngestionStatus.FAILED,
                IngestionErrorCategory.VALIDATION_FAILURE,
                "Ingestion request validation failed",
                RepositoryStatus.UNKNOWN,
            )

        try:
            metadata = self._connector.metadata
        except Exception:
            return self._failure(
                request,
                IngestionStatus.FAILED,
                IngestionErrorCategory.CONNECTOR_UNAVAILABLE,
                "Connector metadata is unavailable; details were withheld",
                RepositoryStatus.UNKNOWN,
                retryable=True,
            )
        if (
            not metadata.validate().is_valid
            or metadata.connector_id != request.connector_id
            or metadata.source_system_id
            != request.collection_context.source_system_id
        ):
            return self._failure(
                request,
                IngestionStatus.FAILED,
                IngestionErrorCategory.VALIDATION_FAILURE,
                "Connector metadata does not match the ingestion request",
                RepositoryStatus.UNKNOWN,
            )
        if set(request.requested_capabilities).difference(metadata.capabilities):
            return self._failure(
                request,
                IngestionStatus.UNSUPPORTED,
                IngestionErrorCategory.UNSUPPORTED_CAPABILITY,
                "The connector does not support every requested capability",
                RepositoryStatus.UNKNOWN,
            )

        try:
            repository_health = self._repository.health()
        except Exception:
            repository_health = None
        if repository_health is None or not repository_health.is_healthy:
            return self._failure(
                request,
                IngestionStatus.FAILED,
                IngestionErrorCategory.REPOSITORY_UNAVAILABLE,
                "Evidence repository is unavailable; details were withheld",
                RepositoryStatus.UNAVAILABLE,
                retryable=True,
            )

        try:
            connector_health = self._connector.health(request.collection_context)
        except Exception:
            return self._failure(
                request,
                IngestionStatus.FAILED,
                IngestionErrorCategory.CONNECTOR_UNAVAILABLE,
                "Connector health could not be established; details were withheld",
                RepositoryStatus.HEALTHY,
                retryable=True,
            )
        if (
            not connector_health.validate().is_valid
            or connector_health.status is not ConnectorStatus.READY
        ):
            return self._failure(
                request,
                IngestionStatus.FAILED,
                IngestionErrorCategory.CONNECTOR_UNAVAILABLE,
                "Connector is not ready for collection",
                RepositoryStatus.HEALTHY,
                retryable=True,
            )

        try:
            collection = self._connector.collect(request.collection_context)
        except Exception:
            return self._failure(
                request,
                IngestionStatus.FAILED,
                IngestionErrorCategory.CONNECTOR_UNAVAILABLE,
                "Connector collection failed; details were withheld",
                RepositoryStatus.HEALTHY,
                retryable=True,
            )

        if (
            not collection.validate().is_valid
            or collection.collection_context_id
            != request.collection_context.collection_id
            or collection.connector_id != request.connector_id
        ):
            return self._failure(
                request,
                IngestionStatus.FAILED,
                IngestionErrorCategory.VALIDATION_FAILURE,
                "Connector collection result validation failed",
                RepositoryStatus.HEALTHY,
                collection_result_reference=collection.result_id,
                completed_at=collection.completed_at,
            )
        if collection.status is CollectionStatus.UNSUPPORTED:
            return self._failure(
                request,
                IngestionStatus.UNSUPPORTED,
                IngestionErrorCategory.UNSUPPORTED_CAPABILITY,
                "Connector reported an unsupported capability",
                RepositoryStatus.HEALTHY,
                collection_result_reference=collection.result_id,
                completed_at=collection.completed_at,
            )
        if collection.status is CollectionStatus.NO_DATA:
            return self._failure(
                request,
                IngestionStatus.NO_DATA,
                IngestionErrorCategory.NO_DATA,
                "Connector reported no evidence",
                RepositoryStatus.HEALTHY,
                collection_result_reference=collection.result_id,
                completed_at=collection.completed_at,
            )
        if collection.status is CollectionStatus.FAILED:
            return self._failure(
                request,
                IngestionStatus.FAILED,
                IngestionErrorCategory.CONNECTOR_UNAVAILABLE,
                "Connector reported a governed collection failure",
                RepositoryStatus.HEALTHY,
                collection_result_reference=collection.result_id,
                completed_at=collection.completed_at,
                retryable=True,
            )

        stored: list[str] = []
        for evidence in collection.evidence:
            if not evidence.validate().is_valid:
                return self._failure(
                    request,
                    IngestionStatus.FAILED,
                    IngestionErrorCategory.VALIDATION_FAILURE,
                    "Collected evidence validation failed",
                    RepositoryStatus.HEALTHY,
                    stored=tuple(stored),
                    collection_result_reference=collection.result_id,
                    completed_at=collection.completed_at,
                )
            try:
                self._repository.store(evidence)
            except DuplicateEvidenceError:
                return self._failure(
                    request,
                    IngestionStatus.FAILED,
                    IngestionErrorCategory.DUPLICATE_EVIDENCE,
                    "Evidence identity already exists",
                    RepositoryStatus.HEALTHY,
                    stored=tuple(stored),
                    collection_result_reference=collection.result_id,
                    completed_at=collection.completed_at,
                )
            except Exception:
                return self._failure(
                    request,
                    IngestionStatus.FAILED,
                    IngestionErrorCategory.REPOSITORY_UNAVAILABLE,
                    "Evidence repository storage failed; details were withheld",
                    RepositoryStatus.UNAVAILABLE,
                    stored=tuple(stored),
                    collection_result_reference=collection.result_id,
                    completed_at=collection.completed_at,
                    retryable=True,
                )
            stored.append(evidence.evidence_id)

        result = IngestionResult(
            result_id=self._result_id(request),
            request_reference=request.request_id,
            collection_result_reference=collection.result_id,
            status=IngestionStatus.SUCCEEDED,
            evidence_count=len(stored),
            stored_evidence_references=tuple(stored),
            repository_status=RepositoryStatus.HEALTHY,
            completed_at=collection.completed_at,
            authority_reference=request.authority_reference,
        )
        result.validate().raise_for_errors()
        return result

    def _failure(
        self,
        request: IngestionRequest,
        status: IngestionStatus,
        category: IngestionErrorCategory,
        message: str,
        repository_status: RepositoryStatus,
        *,
        stored: tuple[str, ...] = (),
        collection_result_reference: str | None = None,
        completed_at=None,
        retryable: bool = False,
    ) -> IngestionResult:
        timestamp = completed_at or request.requested_at
        error = IngestionError(
            error_id=f"dexter:ingestion-error:{uuid5(NAMESPACE_URL, f'{request.request_id}|{category.value}')}",
            category=category,
            message=message,
            occurred_at=timestamp,
            authority_reference=request.authority_reference,
            retryable=retryable,
        )
        result = IngestionResult(
            result_id=self._result_id(request),
            request_reference=request.request_id,
            collection_result_reference=collection_result_reference
            or self._collection_result_id(request),
            status=status,
            evidence_count=len(stored),
            stored_evidence_references=stored,
            repository_status=repository_status,
            completed_at=timestamp,
            authority_reference=request.authority_reference,
            errors=(error,),
        )
        return result

    @staticmethod
    def _result_id(request: IngestionRequest) -> str:
        return (
            f"dexter:ingestion-result:"
            f"{uuid5(NAMESPACE_URL, request.request_id)}"
        )

    @staticmethod
    def _collection_result_id(request: IngestionRequest) -> str:
        return (
            f"dexter:collection-result:"
            f"{uuid5(NAMESPACE_URL, request.collection_context.collection_id)}"
        )
