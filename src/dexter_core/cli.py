"""Thin local operator CLI for Dexter's governed service boundaries."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from collections.abc import Mapping
from enum import IntEnum
from typing import Any, Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen
from uuid import UUID, uuid4

import typer

from . import __version__
from .contracts.assessment import assessment_from_dict
from .connectors.proxmox import ProxmoxConnector
from .contracts.connector import ConnectorCollectionContext, is_safe_text
from .contracts.evidence import EvidenceType
from .contracts.ingestion import (
    IngestionErrorCategory,
    IngestionRequest,
    IngestionStatus,
)
from .contracts.query import (
    QueryRequest,
    QueryResponse,
    QueryType,
    query_response_from_dict,
)
from .persistence.evidence import EvidenceRepository
from .contracts.question import Question, QuestionType
from .ingestion import EvidenceIngestionService
from .query import EmptyEvidenceRepository, GovernedDataRepository, QueryService
from .question import QuestionEngine
from .serialization import contract_to_json


class ExitCode(IntEnum):
    SUCCESS = 0
    FAILURE = 1
    INVALID_INPUT = 2
    NOT_FOUND = 3
    UNAVAILABLE = 4
    UNSUPPORTED = 5


class CLIError(RuntimeError):
    def __init__(self, message: str, code: ExitCode) -> None:
        super().__init__(message)
        self.message, self.code = message, code


class QueryClient(Protocol):
    def query(self, request: QueryRequest) -> QueryResponse: ...


@dataclass(frozen=True, slots=True)
class CLIConfig:
    query_api_url: str | None = None
    postgres_reference: str | None = None
    proxmox_endpoint: str | None = None
    proxmox_authentication_reference: str | None = None
    proxmox_source_system_id: str | None = None
    authority_reference: str = "dexter:authority:local-operator"

    @classmethod
    def from_environment(cls) -> "CLIConfig":
        return cls(
            _env("DEXTER_QUERY_API_URL"),
            _env("DEXTER_POSTGRES_REFERENCE"),
            _env("DEXTER_PROXMOX_ENDPOINT"),
            _env("DEXTER_PROXMOX_AUTH_REFERENCE"),
            _env("DEXTER_PROXMOX_SOURCE_SYSTEM_ID"),
            _env("DEXTER_AUTHORITY_REFERENCE") or "dexter:authority:local-operator",
        )


@dataclass(slots=True)
class CLIRuntime:
    query_service: QueryClient
    ingestion_service: EvidenceIngestionService | None = None
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    identity_generator: Callable[[], Any] = uuid4
    config: CLIConfig | None = None
    proxmox_connector: ProxmoxConnector | None = None
    evidence_repository: EvidenceRepository | None = None

    def __post_init__(self) -> None:
        if (
            self.ingestion_service is None
            and self.proxmox_connector is not None
            and self.evidence_repository is not None
        ):
            self.ingestion_service = EvidenceIngestionService(
                self.proxmox_connector, self.evidence_repository
            )


class QueryAPIClient:
    """Standard-library client for an already-running read-only Query API."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def health(self) -> bool:
        try:
            with urlopen(f"{self.base_url}/health", timeout=5) as response:
                return json.loads(response.read()).get("status") == "healthy"
        except (OSError, ValueError, HTTPError, URLError):
            return False

    def query(self, request: QueryRequest) -> QueryResponse:
        params = urlencode(
            {
                "request_identity": request.request_id,
                "requested_timestamp": _timestamp(request.requested_at),
                "authority_reference": request.authority_reference,
                "version": request.version,
                "revision": request.revision,
            }
        )
        try:
            url = f"{self.base_url}/{request.requested_resource.strip('/')}?{params}"
            with urlopen(url, timeout=10) as response:
                payload = json.loads(response.read())
        except (OSError, ValueError, HTTPError, URLError) as exc:
            raise CLIError("Query API is unavailable", ExitCode.UNAVAILABLE) from exc
        return query_response_from_dict(payload)


def default_runtime() -> CLIRuntime:
    config = CLIConfig.from_environment()
    service = (
        QueryAPIClient(config.query_api_url)
        if config.query_api_url
        else QueryService(GovernedDataRepository(EmptyEvidenceRepository()))
    )
    return CLIRuntime(query_service=service, config=config)


runtime_factory: Callable[[], CLIRuntime] = default_runtime
app = typer.Typer(help="Read-only operator interface for Dexter.")
evidence_app = typer.Typer(help="Query governed Evidence.")
assessment_app = typer.Typer(help="Query governed Assessments.")
question_app = typer.Typer(help="Query governed Questions.")
answer_app = typer.Typer(help="Query governed Answers.")
ingest_app = typer.Typer(help="Run governed read-only ingestion.")
app.add_typer(evidence_app, name="evidence")
app.add_typer(assessment_app, name="assessments")
app.add_typer(question_app, name="questions")
app.add_typer(answer_app, name="answers")
app.add_typer(ingest_app, name="ingest")


def _runtime(ctx: typer.Context) -> CLIRuntime:
    if ctx.obj is None:
        ctx.obj = runtime_factory()
    return ctx.obj


def _env(name: str) -> str | None:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None


def _format(value: str) -> str:
    value = value.strip().lower()
    if value not in {"text", "json"}:
        raise CLIError("format must be text or json", ExitCode.INVALID_INPUT)
    return value


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str | None, name: str) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CLIError(
            f"{name} must be an ISO 8601 timestamp", ExitCode.INVALID_INPUT
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CLIError(f"{name} must include a timezone", ExitCode.INVALID_INPUT)
    return parsed.astimezone(timezone.utc)


def _identity(value: str, kind: str) -> str:
    prefix = f"dexter:{kind}:"
    try:
        valid = value.startswith(prefix) and bool(UUID(value.removeprefix(prefix)))
    except (AttributeError, ValueError):
        valid = False
    if not valid:
        raise CLIError(f"identity must be {prefix}<uuid>", ExitCode.INVALID_INPUT)
    return value


def _request(runtime: CLIRuntime, kind: QueryType, resource: str) -> QueryResponse:
    config = runtime.config or CLIConfig.from_environment()
    if not config.authority_reference or not is_safe_text(config.authority_reference):
        raise CLIError("a safe authority reference is required", ExitCode.INVALID_INPUT)
    request = QueryRequest(
        f"dexter:query-request:{runtime.identity_generator()}",
        kind,
        resource,
        runtime.clock().astimezone(timezone.utc),
        config.authority_reference,
    )
    try:
        return runtime.query_service.query(request)
    except CLIError:
        raise
    except (TypeError, ValueError) as exc:
        raise CLIError(
            "governed query validation failed", ExitCode.INVALID_INPUT
        ) from exc

    except Exception as exc:
        raise CLIError("query dependency is unavailable", ExitCode.UNAVAILABLE) from exc


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _json(value: Any) -> str:
    if hasattr(value, "__dataclass_fields__"):
        return contract_to_json(value)
    return json.dumps(
        _plain(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _emit(value: Any, output_format: str, *, text: str | None = None) -> None:
    if _format(output_format) == "json":
        typer.echo(_json(value))
    elif text is not None:
        typer.echo(text)
    elif isinstance(value, (tuple, list)):
        typer.echo("\n".join(_json(item) for item in value) if value else "No results.")
    else:
        typer.echo(_json(value))


def _run(action: Callable[[], None]) -> None:
    try:
        action()
    except CLIError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(int(exc.code)) from exc


@app.command()
def version(output_format: str = typer.Option("text", "--format")) -> None:
    """Display the installed Dexter package version."""
    _run(lambda: _emit({"version": __version__}, output_format, text=__version__))


@app.command()
def health(
    ctx: typer.Context, output_format: str = typer.Option("text", "--format")
) -> None:
    """Check the configured query dependency."""

    def action() -> None:
        runtime = _runtime(ctx)
        check = getattr(runtime.query_service, "health", None)
        if callable(check):
            healthy, detail = bool(check()), None
        else:
            values = _request(runtime, QueryType.STATUS, "/status").returned_objects
            healthy = bool(values) and values[0].get("status") == "HEALTHY"
            detail = values[0].get("detail") if values else None
        status_value = "healthy" if healthy else "unhealthy"
        _emit({"status": status_value}, output_format, text=str(detail or status_value))
        if not healthy:
            raise CLIError("query dependency is unhealthy", ExitCode.FAILURE)

    _run(action)


@app.command()
def status(
    ctx: typer.Context, output_format: str = typer.Option("text", "--format")
) -> None:
    """Display governed system status."""
    _run(
        lambda: _emit(
            _request(_runtime(ctx), QueryType.STATUS, "/status").returned_objects,
            output_format,
        )
    )


def _list(
    ctx: typer.Context, kind: QueryType, resource: str, output_format: str
) -> None:
    _emit(_request(_runtime(ctx), kind, resource).returned_objects, output_format)


@evidence_app.command("list")
def evidence_list(
    ctx: typer.Context,
    source: str | None = typer.Option(None, "--source"),
    evidence_type: str | None = typer.Option(None, "--evidence-type"),
    start: str | None = typer.Option(None, "--start"),
    end: str | None = typer.Option(None, "--end"),
    limit: int | None = typer.Option(None, "--limit"),
    output_format: str = typer.Option("text", "--format"),
) -> None:
    """List governed Evidence with deterministic optional filters."""

    def action() -> None:
        beginning, ending = _parse_timestamp(start, "start"), _parse_timestamp(
            end, "end"
        )
        if beginning and ending and ending < beginning:
            raise CLIError(
                "end timestamp cannot precede start timestamp", ExitCode.INVALID_INPUT
            )
        if limit is not None and limit <= 0:
            raise CLIError("limit must be positive", ExitCode.INVALID_INPUT)
        kind = None
        if evidence_type:
            try:
                kind = EvidenceType(evidence_type)
            except ValueError as exc:
                raise CLIError(
                    "evidence type is not supported", ExitCode.INVALID_INPUT
                ) from exc
        values = list(
            _request(_runtime(ctx), QueryType.EVIDENCE, "/evidence").returned_objects
        )
        if source:
            values = [x for x in values if x.get("source_system") == source]
        if kind:
            values = [x for x in values if x.get("evidence_type") == kind.value]
        if beginning:
            values = [
                x
                for x in values
                if _parse_timestamp(
                    str(x.get("observation_timestamp")), "observation_timestamp"
                )
                >= beginning
            ]
        if ending:
            values = [
                x
                for x in values
                if _parse_timestamp(
                    str(x.get("observation_timestamp")), "observation_timestamp"
                )
                <= ending
            ]
        _emit(tuple(values[:limit] if limit is not None else values), output_format)

    _run(action)


def _show(
    ctx: typer.Context,
    kind: QueryType,
    resource: str,
    identity: str,
    identity_kind: str,
    output_format: str,
) -> None:
    canonical = _identity(identity, identity_kind)
    values = _request(_runtime(ctx), kind, f"/{resource}/{canonical}").returned_objects
    if not values:
        raise CLIError(f"{identity_kind} not found", ExitCode.NOT_FOUND)
    _emit(values[0], output_format)


@evidence_app.command("show")
def evidence_show(
    ctx: typer.Context,
    identity: str,
    output_format: str = typer.Option("text", "--format"),
) -> None:
    """Show one governed Evidence record."""
    _run(
        lambda: _show(
            ctx, QueryType.EVIDENCE, "evidence", identity, "evidence", output_format
        )
    )


@assessment_app.command("list")
def assessment_list(
    ctx: typer.Context, output_format: str = typer.Option("text", "--format")
) -> None:
    """List governed Assessments."""
    _run(lambda: _list(ctx, QueryType.ASSESSMENT, "/assessments", output_format))


@assessment_app.command("show")
def assessment_show(
    ctx: typer.Context,
    identity: str,
    output_format: str = typer.Option("text", "--format"),
) -> None:
    """Show one governed Assessment."""
    _run(
        lambda: _show(
            ctx,
            QueryType.ASSESSMENT,
            "assessments",
            identity,
            "assessment",
            output_format,
        )
    )


@question_app.command("list")
def question_list(
    ctx: typer.Context, output_format: str = typer.Option("text", "--format")
) -> None:
    """List governed Questions."""
    _run(lambda: _list(ctx, QueryType.QUESTION, "/questions", output_format))


@answer_app.command("list")
def answer_list(
    ctx: typer.Context, output_format: str = typer.Option("text", "--format")
) -> None:
    """List governed Answers."""
    _run(lambda: _list(ctx, QueryType.ANSWER, "/answers", output_format))


@ingest_app.command("proxmox")
def ingest_proxmox(
    ctx: typer.Context, output_format: str = typer.Option("text", "--format")
) -> None:
    """Run explicitly configured, GET-only Proxmox ingestion."""

    def action() -> None:
        runtime, config = (
            _runtime(ctx),
            _runtime(ctx).config or CLIConfig.from_environment(),
        )
        required = {
            "DEXTER_POSTGRES_REFERENCE": config.postgres_reference,
            "DEXTER_PROXMOX_ENDPOINT": config.proxmox_endpoint,
            "DEXTER_PROXMOX_AUTH_REFERENCE": config.proxmox_authentication_reference,
            "DEXTER_PROXMOX_SOURCE_SYSTEM_ID": config.proxmox_source_system_id,
            "DEXTER_AUTHORITY_REFERENCE": config.authority_reference,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise CLIError(
                f"required configuration is missing: {', '.join(missing)}",
                ExitCode.INVALID_INPUT,
            )
        authref = config.proxmox_authentication_reference or ""
        if not authref.startswith("authref:") or not is_safe_text(authref):
            raise CLIError(
                "Proxmox authentication must be a protected authref:",
                ExitCode.INVALID_INPUT,
            )
        if runtime.ingestion_service is None:
            raise CLIError(
                "ingestion dependencies are unavailable", ExitCode.UNAVAILABLE
            )
        service = runtime.ingestion_service
        metadata = getattr(getattr(service, "_connector", None), "metadata", None)
        if metadata is None:
            raise CLIError("Proxmox connector is unavailable", ExitCode.UNAVAILABLE)
        now, capabilities = runtime.clock().astimezone(timezone.utc), tuple(
            metadata.capabilities
        )
        context = ConnectorCollectionContext(
            f"dexter:collection:{runtime.identity_generator()}",
            metadata.connector_id,
            config.proxmox_source_system_id or "",
            capabilities,
            now,
            config.authority_reference,
            f"correlation:cli:{runtime.identity_generator()}",
            authref,
        )
        request = IngestionRequest(
            f"dexter:ingestion-request:{runtime.identity_generator()}",
            metadata.connector_id,
            context,
            capabilities,
            now,
            config.authority_reference,
        )
        result = service.ingest(request)
        _emit(result, output_format)
        if result.status is IngestionStatus.UNSUPPORTED:
            raise CLIError("Proxmox ingestion is unsupported", ExitCode.UNSUPPORTED)
        if result.status is IngestionStatus.FAILED:
            categories = {error.category for error in result.errors}
            unavailable = bool(
                categories
                & {
                    IngestionErrorCategory.CONNECTOR_UNAVAILABLE,
                    IngestionErrorCategory.REPOSITORY_UNAVAILABLE,
                }
            )
            raise CLIError(
                "Proxmox ingestion failed",
                ExitCode.UNAVAILABLE if unavailable else ExitCode.FAILURE,
            )

    _run(action)


@app.command()
def ask(
    ctx: typer.Context,
    question_text: str,
    output_format: str = typer.Option("text", "--format"),
) -> None:
    """Answer from available governed Assessments without an LLM."""

    def action() -> None:
        normalized, runtime = question_text.strip(), _runtime(ctx)
        if not normalized:
            raise CLIError("question text must not be empty", ExitCode.INVALID_INPUT)
        values = _request(
            runtime, QueryType.ASSESSMENT, "/assessments"
        ).returned_objects
        if not values:
            raise CLIError("no supporting assessment exists", ExitCode.NOT_FOUND)
        try:
            assessments = tuple(assessment_from_dict(value) for value in values)
        except (TypeError, ValueError) as exc:
            raise CLIError(
                "available assessments are invalid", ExitCode.FAILURE
            ) from exc
        (
            config,
            now,
        ) = runtime.config or CLIConfig.from_environment(), runtime.clock().astimezone(
            timezone.utc
        )
        question = Question(
            f"dexter:question:{runtime.identity_generator()}",
            (
                QuestionType.WHICH
                if normalized.lower().startswith("which ")
                else QuestionType.WHAT
            ),
            normalized,
            now,
            config.authority_reference,
        )
        answer = QuestionEngine(authority_reference=config.authority_reference).answer(
            question, assessments
        )
        _emit(answer, output_format, text=answer.answer_text)

    _run(action)
