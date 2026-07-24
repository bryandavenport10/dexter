# Dexter Foundational Contract Conventions

- **Version:** 1
- **Status:** Canonical
- **Date:** 2026-07-23
- **Artifact:** ARCH-WP-011

## Purpose

This document defines the canonical engineering conventions inherited by every Dexter Contract. A Contract may add domain-specific meanings, obligations, and invariants, but shall not redefine these conventions. Any exception shall be explicit, narrowly scoped, versioned, and justified through Dexter governance.

These conventions are implementation-independent. They reserve no package, class, storage model, transport, API, or runtime behavior.

## Contract philosophy

A Dexter Contract is an explicit, versioned agreement about observable state and meaning at a boundary. Contracts make reality inspectable before building abstractions over it. They define governed state before any side effect is authorized or performed.

All Contract families shall preserve:

- reality before abstraction;
- contracts before side effects;
- governance before execution;
- determinism before optimization;
- explicit Authority;
- explicit Evidence;
- stable Identity;
- Operational Lineage; and
- compatibility over convenience.

A Contract records an assertion; it does not make that assertion true. Authority does not turn a conclusion into Evidence. Validation does not prove operational success. Optional Semantic Lineage shall never gate or replace Dexter-owned Operational Lineage.

## Contract lifecycle

A Contract definition progresses through proposal, adoption, deprecation, and retirement under governance. Adoption gives a definition a Version and compatibility policy. Deprecation warns that a definition or field is planned for retirement; it does not silently change its meaning. Retirement ends support only according to a published migration policy.

A Contract value has a separate domain Lifecycle. Its domain Contract defines allowed states and transitions. Every transition shall produce a new Revision, preserve Identity when the subject remains the same, identify responsible Authority when required, and retain lineage to the prior state. Historical Revisions shall not be rewritten to simulate a transition.

Lifecycle state and Operational State are independent. Lifecycle describes meaningful progression; Operational State describes time-scoped ability to serve an operational purpose. Neither shall substitute for the other.

## Required Contract components

Every Contract definition shall address each component below. A component may be declared not applicable when the domain genuinely does not require it, but shall not be left implicit.

### Identity

Every independently referenceable value shall have a stable, globally unambiguous identifier in a declared namespace. Identity shall be assigned once, remain independent of storage location and mutable content, and survive serialization and Revision. A materially different subject receives a new Identity.

### Contract type

Every serialized value shall identify its Contract type unambiguously. Type names shall have stable, documented meanings and shall not be inferred solely from transport routes, storage locations, or field shape.

### Version

Every value shall identify the Version of the Contract or schema to which it conforms. A Version governs interpretation and compatibility; it is not an update counter or implementation release version.

### Revision

A mutable-in-time subject shall expose a Revision or equivalent ordered revision identity. Each intentional state change creates a distinct Revision without changing the subject's Identity. Revision ordering and predecessor lineage shall be explicit where concurrent or distributed change is possible.

### Timestamps

Contracts shall define every timestamp's meaning. Timestamps shall be timezone-aware, use canonical UTC at serialization boundaries, and have documented precision. Creation time remains stable; update and event times advance only for their defined occurrence. Ordering invariants shall be validated. A missing, unknown, or not-applicable time shall not be replaced with the current time.

### Authority references

When an assertion, Decision, grant, transition, Assessment, or Outcome requires Authority, the Contract shall carry an explicit Reference to the accountable Authority and, where applicable, its scope, delegation basis, and assertion time. Attribution alone shall not imply authorization.

### Evidence references

Contracts that rely on Evidence shall carry typed References to that Evidence, with sufficient provenance and context to identify the offered material. Evidence shall remain separate from Observations, Assessments, Interpretations, Inferences, Decisions, and Outcomes.

### Relationship references

Relationships shall be typed, directed References between stable identities. A Relationship shall define its source, target, and semantics without merging identities or duplicating the referenced subject. References do not prove existence, availability, or Authority.

### Operational state

When operational condition is relevant, the Contract shall define an explicit, bounded set of Operational State values, including unknown condition. Operational State shall be time-scoped and attributable. It shall not be inferred from Lifecycle state.

### Lifecycle state

When a subject progresses through meaningful states, the Contract shall define allowed Lifecycle states and transition invariants. It shall distinguish current state from transition history and shall not equate lifecycle progression with runtime workflow.

### Serialization expectations

The Contract shall define its canonical serialized form, field names, required and optional fields, scalar representations, nullability, timestamp and identifier encoding, and handling of unknown and reserved fields. Round-trip reconstruction shall preserve Contract meaning.

### Validation expectations

The Contract shall specify structural and semantic invariants, failure reporting, and trust boundaries. Validation shall be deterministic, shall not depend on hidden mutable state, and shall not perform side effects.

### Compatibility expectations

The Contract shall declare which producer and consumer Versions may interact, how unknown fields are handled, which fields are reserved, and what migration or deprecation path applies to incompatible change. Compatibility shall be designed before release rather than inferred from implementation behavior.

## Deterministic behavior

Contracts define state. Contracts do not execute behavior.

Given the same Contract value, Contract Version, and declared rules, validation results and canonical serialization shall be identical. Construction, validation, comparison, and serialization shall not initiate network calls, access credentials, read clocks implicitly, mutate external state, schedule work, select providers, or perform runtime side effects.

Runtime components may consume Contracts and act under explicit governance, but that behavior is outside the Contract. Optimizations shall not change meaning, ordering guarantees, validation results, or serialized form.

## Compatibility rules

### Forward compatibility

A compatibility policy shall state whether an older consumer can safely process values from a newer compatible Version. Additive evolution requires older consumers to preserve or deliberately reject unfamiliar information without misinterpreting known fields. Adding a field is not automatically forward compatible.

### Backward compatibility

A newer consumer should accept older supported values when their meaning remains valid. New required fields, narrowed value domains, changed defaults, and changed field meanings are incompatible unless a governed migration supplies the missing meaning.

### Unknown fields

Each Contract family shall choose and document one deterministic policy: reject unknown fields, or preserve them losslessly as opaque extension data. Unknown fields shall never be silently interpreted, silently discarded during a purported lossless round trip, or allowed to override known fields. Security and Authority decisions shall not depend on unrecognized fields.

### Reserved fields

Removed field names, identifiers, and enum values shall remain reserved unless a later governed Version explicitly releases them with proof that reuse cannot cause ambiguity. Reserved elements shall not carry new meanings within the same compatibility lineage.

### Extension guidance

Compatible extensions shall use documented extension points or a new Contract family. Extension names shall be namespaced, collision-resistant, deterministic, and optional to core interpretation. Extensions shall not weaken invariants, grant Authority, embed secrets, or change a core field's meaning. Such a change requires a new Version or Contract family.

Compatibility takes precedence over implementation convenience. Consumers shall fail explicitly when safe interpretation is impossible.

## Authority requirements

Every Contract requiring Authority shall reference Authority explicitly. The Reference shall identify who is accountable and the applicable basis or scope. Delegated Authority shall reference its delegation chain or grant. Authority shall not be inferred from possession of a Contract, Worker Claim, credential, network identity, Provider Assignment, or prior behavior.

Authority References are not credentials. Contracts shall record accountable governance without carrying secret material used to authenticate or exercise Authority.

## Evidence requirements

Evidence References shall remain distinguishable from conclusions. Contracts shall preserve which material was offered, its provenance, its relationship to the claim, and its collection or supply context.

An Observation is not its Evidence. An Assessment or Verification result is not its Evidence. An Interpretation or Inference is not a Fact solely because Evidence is referenced. Serialization and Revision shall retain these boundaries so reviewers can inspect the basis without treating a derived conclusion as source material.

## Reference requirements

References shall use stable identifiers or declared locators and retain their type and semantics. Embedding another subject does not replace a Reference when independent Identity or lineage matters.

Protected References shall use opaque handles rather than embedded secrets. Secret Handles identify a controlled resolver without containing secret values, credentials, tokens, or sensitive resolution details. Resolution requires explicit Authority and occurs outside the Contract. Secrets shall not appear in Contract values, Events, logs, Evidence metadata, or serialized domain data.

## Versioning philosophy

- **Version** identifies a defined Contract, schema, protocol, or artifact state and governs compatibility.
- **Revision** identifies a changed recorded state of the same subject while preserving its Identity.
- **Migration** is an explicit, governed transformation between Versions or representations. It shall state source and target Versions, preserve lineage, be deterministic, and report information loss or changed meaning.
- **Deprecation** announces planned withdrawal while retaining current meaning for the documented support period. It is not deletion, migration, or permission to reinterpret existing data.

Contract Version and implementation release version remain independent. An incompatible semantic or structural change requires a new Contract Version; an ordinary subject update requires a new Revision.

## Validation philosophy

Validation evaluates a value against its Contract's structural and semantic rules, including required fields, types, formats, identifier stability, timestamp ordering, allowed states, reference shape, and cross-field invariants. Results shall be explicit and attributable to a known rule set and Contract Version.

Verification independently evaluates operational claims and records against declared criteria and Evidence after Execution. Verification confirms operational correctness or acceptability within its stated scope.

Validation verifies structural correctness. Verification confirms operational correctness. They, their results, and their Authorities shall remain distinct. A valid Contract is not proof that its claims are true, authorized, executed, or successfully verified.

## Serialization philosophy

Each Contract family shall specify one canonical serialization for signing, hashing, equality, exchange, or persistence where byte-level stability is required. Canonical serialization shall define encoding, normalization, timestamp form, numeric form, null handling, and field ordering.

Mappings and sets shall use deterministic ordering where applicable. Collection order shall be preserved only when it has Contract meaning; otherwise the Contract shall define a canonical order. Serialization shall not generate or replace identifiers, timestamps, Authority, Evidence, or defaults from ambient state.

Stable identifiers shall survive serialization, deserialization, migration, and Revision. Equivalent values shall serialize equivalently under the same Version, and deserialization followed by canonical serialization shall not alter their meaning.

## Extension philosophy

New concerns are introduced as new Contract families that inherit these conventions and define only domain-specific identity, states, relationships, invariants, and compatibility rules. Existing Contracts shall not be modified merely to host unrelated future behavior.

A new family shall have a distinct Contract type, initial Version, ownership, purpose, boundary, and extension policy. It may reference existing values by stable Identity but shall not embed or redefine them to bypass boundaries. Shared concepts graduate into these conventions only through governance; family-specific fields do not.

Extensions cannot create runtime behavior. Runtime implementations may later be introduced behind Contract boundaries and shall obey applicable Contracts without making their meaning implementation-dependent.

## Future runtime Contracts

These conventions apply to:

- Submission;
- Admission;
- Pending Job;
- Worker Claim;
- Lease;
- Provider Assignment;
- Execution Attempt;
- Runtime Event;
- Verification;
- Outcome; and
- Operational Learning.

Each family shall inherit this document and add only its domain rules. Together, stable identities and explicit References shall preserve Operational Lineage from Submission through Outcome and into governed Operational Learning.

This document completes the Architecture Foundation. Implementation is now the default activity. No additional architecture work package shall be introduced unless implementation reveals a genuine architectural deficiency requiring documented governance justification.

The next work package is **ENG-WP-047 — Execution Session**.
