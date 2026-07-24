# ADR-0001: Runtime Package Architecture

- **Status:** Accepted
- **Date:** 2026-07-23
- **Artifact:** ARCH-WP-006; refined by ARCH-WP-012

## Context

Dexter Core 0.1.0 is the dependency-free, typed Governed Entity Contract. It provides identity, lifecycle and operational state, authority, provenance, evidence, relationships, validation, and schema-versioned serialization. Dexter will later need a governed execution lifecycle, but no runtime contract or behavior exists today.

Reality precedes abstraction; contracts precede side effects; governance precedes execution.

## Existing repository state

```text
src/dexter_core/
├── entity.py
├── enums.py
├── references.py
├── serialization.py
└── validation.py
```

These flat modules are established foundational primitives. `Authority` is a value in `references.py`; evidence and provenance are references, not subsystems. No prior ADR numbering scheme exists. There is no evidence requiring source reorganization now.

## Problem statement

Submission, admission, pending work, claims, leases, provider assignment, attempts, runtime events, completion, verification, outcomes, and learning are distinct facts and decisions. A durable architecture must prevent their collapse into a dependency hub and prevent foundational entity primitives from depending on workers or infrastructure.

## Decision drivers

- Preserve existing APIs and wire compatibility.
- Keep foundational primitives independent of higher-level domains.
- Admission is not execution; claim is not lease; lease is not assignment; assignment is not execution; completion is not verification; verification is not learning.
- Evidence remains distinguishable from assessment and interpretation.
- Authority is explicit and traceable.
- Operational lineage belongs to Dexter and does not require semantic lineage.
- Protected secrets use references or handles.
- Unknown, unsupported, contradictory, and not-applicable remain distinct.
- Introduce packages only with concrete, reality-tested contracts.

## Options considered

### Option A: single `dexter_core.execution`

One namespace is initially simple but combines decisions, runtime mechanics, verification, and side effects into a dependency hub. Rejected.

### Option B: separated governance and runtime

`governance`, `runtime`, and `verification` clarify major boundaries, but shared immutable contracts would be duplicated or owned by a side-effecting layer; learning and lineage remain ambiguous. Rejected as incomplete.

### Option C: contract-first layered architecture

`contracts`, `governance`, `runtime`, `verification`, and `learning` separate values, decisions, mechanisms, and consumers. Selected, refined with distinct operational lineage and no immediate relocation of existing primitives.

Benefits are explicit ownership, acyclic dependencies, testable contracts, and replaceable adapters. Costs are more namespaces, mapping, and version coordination. The risk is ceremonial layering; packages therefore appear only with real contracts, never as empty reservations.

### Option D: feature slices

Top-level submission, claim, and lease slices improve local cohesion but permit each slice to invent governance, serialization, and authority conventions. Rejected until common contract conventions are established.

## Decision

Adopt a contract-first layered architecture:

```text
foundational primitives
        ↓
contracts
        ↓
governance
        ↓
runtime
        ↓
verification
        ↓
outcomes and learning

operational_lineage observes stable lifecycle facts without becoming a
reverse dependency of lower layers.
```

“Execution” names the end-to-end domain, not a catch-all package. Cross-stage immutable values belong to `contracts`; policy and decisions to `governance`; coordination and I/O to `runtime`; independent evaluation to `verification`; verified-result consumption to `learning`.

### Governed runtime lifecycle

Implementation of Worker Claim, Lease, Provider Assignment, and Execution Attempt revealed that runtime execution is not a single action. It is an observable, governed lifecycle:

```text
Pending Job
    ↓
Worker Claim
    ↓
Lease
    ↓
Provider Assignment
    ↓
Execution Attempt
=========================
Governance Boundary
=========================
    ↓
Execution Session
    ↓
Runtime Events
    ↓
Execution Verification
    ↓
Outcome Tracking
    ↓
Operational Learning
```

The governance boundary separates the contracts that establish permission and scope from the runtime behavior performed under that authority. An **Execution Session** is the governed runtime context created from a valid Execution Attempt. It owns runtime state, may emit Runtime Events, consumes the applicable contracts, and does not replace or redefine them.

**Runtime Events** are observational records of behavior during an Execution Session. Event kinds may include `started`, `heartbeat`, `progress`, `warning`, `paused`, `resumed`, `stdout`, `stderr`, `completed`, `failed`, and `cancelled`. These are illustrative rather than a closed event vocabulary, and this refinement introduces no event implementation.

The governing principle is:

- Contracts establish authority.
- Execution Session performs behavior.
- Runtime Events observe behavior.
- Verification evaluates behavior.
- Learning consumes verified outcomes.

## Package map

Labels describe readiness, not directories to create now.

| Path | Status | Responsibility |
| --- | --- | --- |
| Existing flat modules | **EXISTING** | Foundational entity values, validation, and v1 wire format. |
| `contracts/` | **INTRODUCE NEXT** | Pure execution-domain values and wire contracts; begin with conventions and submission. |
| `contracts/submission.py` | **INTRODUCE NEXT** | Canonical request, constraints, reference/handle inputs, idempotency identity. |
| `contracts/admission.py`, `pending.py`, `claim.py`, `lease.py` | **RESERVED** | Immutable decisions and lifecycle facts. |
| `contracts/provider.py`, `attempt.py`, `events.py`, `completion.py` | **RESERVED** | Capabilities/assignments, attempts, observational event records, completion claims. |
| `contracts/verification.py`, `outcome.py` | **RESERVED** | Verification claims/results and normalized outcomes. |
| `governance/` | **RESERVED** | Pure policy evaluation and authoritative admission decisions; no execution I/O. |
| `runtime/` | **RESERVED** | Execution Session state and behavior, pending coordination, claim/lease mechanics, provider adapters, workers, and event emission/capture. |
| `verification/` | **RESERVED** | Independent evaluation of completion claims against evidence and policy. |
| `operational_lineage/` | **RESERVED** | Dexter-owned lifecycle correlation and append-only projection. |
| `learning/` | **DEFERRED** | Consume verified outcomes and operational lineage, not raw claims. |
| `semantic_lineage/` | **DEFERRED** | Optional meaning/derivation graph, separate from operational lineage. |
| `authority/`, `evidence/` | **DEFERRED** | Resolution/storage adapters only if current primitives prove insufficient. |
| `execution/` catch-all | **REJECTED** | Collapses lifecycle layers and side-effect boundaries. |
| Combined `lineage/` | **REJECTED** | Obscures operational versus semantic ownership. |

No empty packages are created. A pending job is admitted work awaiting claim; a claim is worker ownership assertion; a lease is time-bounded authority to act; an assignment binds a provider; an attempt is one try; a completion claim is unverified.

## Responsibility matrix

| Concept | Canonical owner |
| --- | --- |
| Entity identity | Existing `entity.py` |
| References, relationships, provenance, evidence | Existing `references.py`; future adapters resolve references |
| Authority declarations | Existing primitive; decisions carry authority reference/snapshot |
| Submission | `contracts.submission` |
| Admission | Contract in `contracts.admission`; evaluation in `governance.admission` |
| Pending jobs | `contracts.pending` |
| Claims and leases | Contracts in `contracts`; coordination in `runtime` |
| Provider capabilities and assignments | `contracts.provider`; discovery/invocation in `runtime` |
| Execution attempts | `contracts.attempt` |
| Execution Sessions | Runtime, created from valid Execution Attempts and consuming applicable contracts |
| Runtime Events | Observational records in `contracts`; emission/capture in `runtime` |
| Completion claims | `contracts.completion`; emitted by `runtime` |
| Verification claims and outcomes | `contracts.verification`; decisions in `verification` |
| Normalized outcomes | `contracts.outcome`; produced after verification |
| Operational lineage | `operational_lineage` |
| Semantic lineage | Optional `semantic_lineage` |
| Learning | `learning`, consuming verified outcomes |

## Architectural answers and terminology

`dexter_core.execution` will not be a catch-all. Canonical lifecycle values live in focused `contracts` modules. Admission evaluation belongs to governance; claim/lease coordination, provider interaction, Execution Sessions, and event capture to runtime; verification logic to verification. Execution Attempts establish bounded, governed tries; they are not themselves the runtime context that performs behavior.

Authority is a combination: a universal foundational declaration/reference, an explicit decision property, and potentially a later domain package for resolution and policy. No new authority package is warranted today. An authority declaration identifies an asserter; it does not itself grant runtime capability.

Assessment is distinct from interpretation. Assessment evaluates facts against declared criteria and records authority, evidence, method/version, and result. Interpretation assigns meaning or explanation and is separately attributable. Neither overwrites evidence.

Universal Dexter Core primitives are stable identity, typed references, authority attribution, timestamps, schema identity, validation reports, explicit state vocabularies, and serialization conventions. Provider SDK types, queue messages, database models, scheduler state, commands, credentials, application policy, and UI concepts are application-specific.

All higher layers may reference `GovernedEntity`, preferably by stable identifier where sufficient. The entity, enum, reference, validation, and entity-serialization modules must never import contracts, governance, runtime, verification, lineage, or learning.

## Dependency rules and prohibited coupling

1. Imports follow the layer direction; reverse imports are prohibited.
2. `contracts` depends only on foundations and the standard library. Shared values move downward to neutral modules rather than create cycles.
3. `governance` depends on foundations/contracts, never runtime. Runtime consumes admission decisions; it does not make authoritative admission policy.
4. `runtime` depends on foundations, contracts, and governance interfaces/decision values, never concrete verification or learning services.
5. `verification` consumes contracts, evidence references, completion claims, and runtime facts through contracts—not worker/provider implementations.
6. `learning` consumes verified outcomes and lineage projections. Raw events and completion claims are not verified truth.
7. Operational lineage correlates stable facts; lower layers do not depend on its storage. Semantic lineage may consume operational lineage but never gate it.
8. Evidence and secrets use immutable references, digests, or opaque handles, never embedded payloads/plaintext.
9. Persistence schemas, transports, SDK types, and framework types never become canonical contracts.
10. Prevent circular dependencies through import rules, consumer-owned protocols, identifiers instead of object graphs, and import-boundary tests when packages appear.

## Purity and side-effect boundaries

Foundations, every `contracts` module, governance decision models, and verification result models are pure and deterministic. They may construct, normalize, validate, serialize, and evaluate explicit inputs; they may not access clocks, randomness, networks, filesystems, subprocesses, queues, databases, or providers. Callers supply identifiers and timestamps.

Only runtime services/adapters, evidence resolvers, lineage persistence adapters, verification evidence-retrieval adapters, and learning persistence/training adapters may create side effects. They sit behind explicit interfaces and emit contract-defined facts. Governance may use application adapters to fetch policy, but canonical decision functions remain deterministic.

## Authority model implications

Every admission decision, lease issuance, assignment, completion claim, verification result, and outcome identifies its asserting authority and assertion time. Delegation is traceable by reference. Claims, leases, and provider credentials imply no broader authority. Credentials are opaque handles.

## Evidence and lineage implications

Evidence references supporting reality. Assessment applies criteria; interpretation explains meaning. All are distinct and attributable. Contradictory evidence is retained explicitly, not collapsed into unknown.

Dexter owns operational lineage. Stable correlation identifiers connect submissions, decisions, claims, leases, assignments, attempts, events, completion claims, verification, and outcomes. Semantic lineage is optional and cannot rewrite or become a prerequisite for operational lineage.

## Serialization compatibility implications

The existing `GovernedEntity` schema `1.0`, JSON shape, public imports, and strict unknown-field behavior remain unchanged. Each new contract family receives its own `contract_type` and schema version rather than sharing entity or global versions.

Each family defines deterministic codecs, required/optional fields, enum values, unknown-field policy, and compatibility fixtures. Readers reject unsupported major versions and preserve unknown, unsupported, contradictory, and not-applicable. Additive changes require a documented reader policy; breaking changes require a new major contract version and migration path. Transports and storage adapt to canonical contracts, never the reverse.

## Consequences

Lifecycle ordering and trust transitions become visible; current imports stay stable; runtime mechanisms remain replaceable. Costs are extra namespaces, mapping, and version coordination.

## Risks

Premature contracts, excessive module granularity, hidden I/O in governance, event/outcome drift, and lineage conflation are principal risks. Mitigations are one concrete contract per work package, consolidation only within layers, pure-function tests, compatibility fixtures, stable correlation IDs, and distinct lineage names.

## Rejected alternatives

Options A, B, and D are rejected above. Moving current primitives into `contracts` now is also rejected because it creates compatibility work without solving a present defect. Empty package reservation is rejected because it implies APIs without reality-tested contracts.

## Migration strategy

1. Do not move or re-export v0.1.0 modules now.
2. Establish common contract conventions before creating `contracts`.
3. Introduce each package with its first reviewed concrete type and tests.
4. Preserve public imports and entity wire compatibility. Later consolidation adds compatibility re-exports before deprecation; removal requires a planned major release.
5. Add import-boundary and per-family compatibility tests as layers appear.
6. Keep application adapters outside pure contract modules.

## Future work sequence

The implementation roadmap following the completed Worker Claim, Lease, Provider Assignment, and Execution Attempt contracts is:

1. **ENG-WP-047 — Execution Session**
2. **ENG-WP-048 — Runtime Events**
3. **ENG-WP-049 — Execution Verification**
4. **ENG-WP-050 — Outcome Tracking**
5. **ENG-WP-051 — Operational Learning**

Each step validates terminology against observed requirements before the next layer.

## Explicit non-goals

This ADR implements no submissions, admission, pending jobs, claims, leases, providers, attempts, workers, queues, schedulers, databases, APIs, commands, events, verification, outcomes, lineage storage, learning, integrations, authentication, authorization, or secret storage. It creates no placeholder code, dependency, public behavior change, or source reorganization.

## Verification performed

Acceptance verification uses `uv sync`, `uv run pytest`, `bash scripts/check.sh`, `git diff --check`, and package metadata inspection. Exact results are recorded in the completion report and commit.
