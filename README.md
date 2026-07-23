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

## Compatibility

The package version and serialized contract version are independent. `schema_version` identifies the wire contract; version `1.0` is the only version accepted by the built-in validator in this release. Unknown JSON fields fail explicitly instead of being silently discarded.

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
