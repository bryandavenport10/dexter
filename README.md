# Dexter Core

Dexter Core is the dependency-free Python foundation for governed entities in Dexter AI. It provides stable identity, lifecycle and operational state, authority, provenance, evidence, relationships, validation, and schema-versioned JSON serialization.

## Requirements and installation

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

For development, install the test extra and run the suite:

```bash
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
```

## Quick start

```python
from datetime import datetime, timezone
from dexter_core import Authority, AuthorityKind, GovernedEntity

entity = GovernedEntity(
    entity_type="dataset",
    name="Customer Reference Data",
    authority=Authority(
        identifier="data-office",
        name="Data Office",
        kind=AuthorityKind.ORGANIZATION,
        asserted_at=datetime.now(timezone.utc),
    ),
)

assert entity.validate().is_valid
print(entity.entity_id)
```

See [`examples/create_entity.py`](examples/create_entity.py) for a complete
serialization round trip and [`docs/contract.md`](docs/contract.md) for
Governed Entity Contract semantics.

## Governance

- [`Dexter Constitution`](docs/governance/DEXTER_CONSTITUTION.md) defines the
  foundational principles governing all Dexter architecture, engineering,
  implementation, behavior, and future federation.
- [`Dexter Engineering Standard`](docs/engineering/DEXTER_ENGINEERING_STANDARD.md)
  governs repository workflow, testing, review, architecture decisions, AI
  engineering, and releases.
- [`Dexter Canonical Vocabulary`](docs/architecture/DEXTER_CANONICAL_VOCABULARY.md)
  is the authoritative terminology reference for architecture, contracts,
  documentation, and engineering work.
- [`Runtime Package Architecture ADR`](docs/adr/ADR-0001-runtime-package-architecture.md)
  defines the canonical future package architecture and dependency boundaries.

## Contracts

- [`Foundational Contract Conventions`](docs/contracts/FOUNDATIONAL_CONTRACT_CONVENTIONS.md)
  defines the canonical identity, versioning, authority, evidence, reference,
  lifecycle, validation, serialization, compatibility, and extension rules
  inherited by every future Dexter contract.
- [`Governed Entity Contract`](docs/contract.md) documents the currently
  implemented governed entity semantics.

## Compatibility

The package version and serialized contract version are independent. `schema_version` identifies the wire contract; version `1.0` is the only version accepted by the built-in validator in this release. Unknown JSON fields fail explicitly instead of being silently discarded.

## Connector framework

## Dexter CLI

The installed `dexter` command is a thin, read-only operator interface to the Query API, governed ingestion service, and Question Engine. It exposes no infrastructure mutation commands and uses no LLM. Text output is the default; pass `--format json` for deterministic canonical JSON.

```bash
dexter version
dexter health
dexter evidence list --format json
dexter evidence show dexter:evidence:<uuid>
dexter ingest proxmox
dexter ask "Which virtual machines show resource pressure?"
```

Query commands use the local empty read-only service by default or `DEXTER_QUERY_API_URL` when configured. Live Proxmox ingestion requires explicit application composition plus these references:

- `DEXTER_POSTGRES_REFERENCE`
- `DEXTER_PROXMOX_ENDPOINT`
- `DEXTER_PROXMOX_AUTH_REFERENCE` using the protected `authref:` convention
- `DEXTER_PROXMOX_SOURCE_SYSTEM_ID`
- `DEXTER_AUTHORITY_REFERENCE`

Configuration values are references, not an embedded secret store. The Proxmox connector remains GET-only, authentication values remain behind protected references, and credentials are never embedded in governed output.

Infrastructure integrations implement the read-only `Connector` protocol in `dexter_core.connectors`. Governed metadata, collection context, result, status, capability, and error contracts remain in `dexter_core.contracts`; transport and normalization behavior remains in connector implementations.

Callers supply a validated collection context and dependency-injected transport. Authentication is represented only by an `authref:` identifier: credentials and secret-bearing URLs must never enter governed output. Connectors declare static capabilities, implement `metadata`, `collect(context)`, and `health(context)`, and expose no write operations. Caller-supplied timestamps make results deterministic.

The Proxmox connector retains legacy `collect()` observation and `ingest()` evidence methods. Passing a context to `collect(context)` uses the governed boundary while preserving its GET-only transport.

## License

Apache License 2.0. See [`LICENSE`](LICENSE).

## Evidence persistence

`PostgreSQLEvidenceRepository` stores validated connector-produced `Evidence` as immutable canonical JSON in PostgreSQL. The application composition root injects a connection factory; the repository owns no global connection and contains no credentials. Call `initialize_schema()` explicitly during deployment setup, then use identity, source, inclusive observation-time window, type, or relationship queries. Results have deterministic observation-time and identity ordering, and duplicate identities are rejected without replacement.


## Query API

`dexter_core.api:create_app` provides a FastAPI application for deterministic, read-only access to evidence, assessments, questions, answers, and repository status. Query endpoints require a canonical `request_identity`, UTC `requested_timestamp`, and `authority_reference`; they expose no write operations. OpenAPI is available at `/openapi.json`.
