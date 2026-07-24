# Dexter Canonical Vocabulary

- **Version:** 1
- **Status:** Canonical
- **Date:** 2026-07-23
- **Artifact:** ARCH-WP-008

## Purpose and principles

This is Dexter Core's authoritative, implementation-independent terminology reference. ADRs, work packages, contracts, APIs, implementations, documentation, PMO artifacts, AI agents, and federation participants use these meanings. A definition reserves meaning, not a package, type, service, workflow, or behavior.

Vocabulary preserves: reality before abstraction; contracts before side effects; governance before execution; verification after execution; Dexter ownership of operational lineage; and the rule that semantic lineage can never be a prerequisite for operational lineage. Authority is always explicit. Evidence always remains distinguishable from interpretation.

## Vocabulary

### Entity
- **Definition:** A distinct subject about which Dexter records identity, state, or assertions.
- **Purpose:** Provides a stable subject for governance and reference.
- **What it is:** An identifiable domain concept.
- **What it is NOT:** Necessarily governed, executable, mutable, or stored.
- **Relationships:** A Governed Entity is an Entity subject to a Contract.

### Governed Entity
- **Definition:** An Entity constrained by the Governed Entity Contract.
- **Purpose:** Makes a subject's identity, state, authority, provenance, evidence, relationships, validation, and serialization accountable.
- **What it is:** A governed representation with stable Identity.
- **What it is NOT:** A runtime job, database record, or authority grant.
- **Relationships:** Has Authority, Lifecycle, Operational State, Evidence, and Relationships.

### Contract
- **Definition:** An explicit, versioned set of meanings, obligations, and invariants at a boundary.
- **Purpose:** Enables consistent exchange and evaluation.
- **What it is:** A normative agreement about observable form and meaning.
- **What it is NOT:** An implementation, transport, policy Decision, or convention.
- **Relationships:** Uses Contract Conventions and defines Validation, Serialization, Identity, or Version as applicable.

### Contract Convention
- **Definition:** A reusable rule for how Dexter Contracts express a common concern.
- **Purpose:** Keeps contract families consistent.
- **What it is:** A rule for identity, time, authority, references, states, compatibility, or encoding.
- **What it is NOT:** A Contract instance, runtime framework, or implicit default.
- **Relationships:** Constrains Contracts without replacing domain-specific terms.

### Governance
- **Definition:** Evaluation and control of admissibility, authority, policy, and accountability.
- **Purpose:** Determines whether and under whose Authority action may proceed.
- **What it is:** A domain of explicit criteria and Decisions.
- **What it is NOT:** Execution, orchestration, or infrastructure.
- **Relationships:** Precedes Execution and produces Admission and other Decisions.

### Execution
- **Definition:** The end-to-end domain in which admitted work is coordinated, attempted, completed, verified, and resolved to an Outcome.
- **Purpose:** Names the full work lifecycle without collapsing its stages.
- **What it is:** A domain spanning governed Decisions and operational facts.
- **What it is NOT:** A catch-all package, one attempt, or Verification.
- **Relationships:** Includes Runtime but remains distinct from Governance, Verification, and Learning.

### Runtime
- **Definition:** The operational layer coordinating admitted work and interacting with workers, providers, and external systems.
- **Purpose:** Performs authorized side effects and records what occurred.
- **What it is:** Execution coordination and I/O behind Contracts.
- **What it is NOT:** Governance policy, Contract meaning, or independent Verification.
- **Relationships:** Manages Pending Jobs, Claims, Leases, Assignments, Execution Sessions, and Runtime Events.

### Verification
- **Definition:** Independent evaluation of execution claims and records against declared criteria and Evidence.
- **Purpose:** Determines what may be accepted after Execution.
- **What it is:** A post-execution Assessment with explicit Authority.
- **What it is NOT:** Validation, Execution, Completion, or Learning.
- **Relationships:** Consumes Completion, Runtime Events, and Evidence and informs Outcomes.

### Validation
- **Definition:** Evaluation of a value against its Contract's structural and semantic rules.
- **Purpose:** Determines contract conformance.
- **What it is:** Checking whether a value is well-formed.
- **What it is NOT:** Proof that an external claim is true or Execution succeeded.
- **Relationships:** Applies at trust boundaries; Verification evaluates execution claims after Execution.

### Submission
- **Definition:** A request proposing work, constraints, inputs, and intent for governance consideration.
- **Purpose:** Presents candidate work without presuming permission.
- **What it is:** An attributable request.
- **What it is NOT:** Admission, a Pending Job, or execution authority.
- **Relationships:** Governance evaluates it to produce an Admission Decision.

### Admission
- **Definition:** The authoritative Decision accepting or rejecting a Submission for the governed execution lifecycle.
- **Purpose:** Gates work before Runtime coordination.
- **What it is:** A governance result with Authority and rationale.
- **What it is NOT:** Execution, scheduling, or evidence work began.
- **Relationships:** Accepted Admission may create a Pending Job.

### Pending Job
- **Definition:** Admitted work awaiting an eligible Worker Claim.
- **Purpose:** Represents authorized demand not yet taken for work.
- **What it is:** A lifecycle state and work record.
- **What it is NOT:** A Submission, Claim, Lease, Assignment, or Attempt.
- **Relationships:** Exists after Admission and before Worker Claim.

### Worker
- **Definition:** An operational participant that seeks and performs authorized work.
- **Purpose:** Identifies the runtime actor separately from work and authority records.
- **What it is:** An identifiable Runtime participant.
- **What it is NOT:** Inherently an Authority, Provider, or job owner.
- **Relationships:** Makes a Worker Claim, acts under a Lease, and may invoke an assigned Provider.

### Worker Claim
- **Definition:** A Worker's recorded assertion of responsibility for coordinating a Pending Job.
- **Purpose:** Resolves contention accountably before authority is granted.
- **What it is:** A Worker ownership assertion.
- **What it is NOT:** A Lease, Provider Assignment, credential, or proof of Execution.
- **Relationships:** Refers to a Worker and Pending Job; may lead to a Lease.

### Lease
- **Definition:** A time-bounded, explicitly authorized grant permitting a Worker to act on claimed work within limits.
- **Purpose:** Bounds operational authority and enables recovery.
- **What it is:** A revocable or expiring authorization record.
- **What it is NOT:** A Worker Claim, provider selection, credential, or Attempt.
- **Relationships:** Follows a Claim and may constrain Assignment and Attempts.

### Provider
- **Definition:** An identifiable facility capable of performing a class of work.
- **Purpose:** Names the performer or service selected for an Attempt.
- **What it is:** A capability-bearing execution participant or service.
- **What it is NOT:** A Worker, capability claim, Assignment, or secret.
- **Relationships:** Declares Provider Capabilities and is bound by a Provider Assignment.

### Provider Capability
- **Definition:** A bounded declaration of work a Provider can perform and its constraints.
- **Purpose:** Supports governed matching of work to providers.
- **What it is:** An attributable capability claim.
- **What it is NOT:** Proof of fitness, usage authority, or an Assignment.
- **Relationships:** Is evaluated for Provider Assignment and may require Evidence or Verification.

### Provider Assignment
- **Definition:** An explicit Decision binding a Provider to particular admitted work under stated constraints.
- **Purpose:** Records provider selection before an Attempt.
- **What it is:** A governed selection and binding.
- **What it is NOT:** A Lease, capability, invocation, or Completion.
- **Relationships:** Uses Provider Capability, respects a Lease, and precedes an Execution Attempt.

### Execution Attempt
- **Definition:** One bounded try to perform assigned work.
- **Purpose:** Distinguishes retries without changing admitted-work Identity.
- **What it is:** A uniquely identifiable governed try from which an Execution Session may be created.
- **What it is NOT:** Entire Execution, Provider Assignment, or Outcome.
- **Relationships:** Occurs under a Lease and Assignment and precedes an Execution Session.

### Execution Session
- **Definition:** The governed Runtime context created from a valid Execution Attempt.
- **Purpose:** Owns runtime state while authorized behavior is performed.
- **What it is:** A behavioral context that consumes Contracts and may emit Runtime Events.
- **What it is NOT:** A Contract, replacement for Contracts, Execution Attempt, or Verification.
- **Relationships:** Is created from an Execution Attempt, performs behavior, and may emit Runtime Events.

### Runtime Event
- **Definition:** An immutable, attributable observational record of behavior during an Execution Session.
- **Purpose:** Preserves operational history for lineage and Verification.
- **What it is:** A timestamped observation linked to stable session and lifecycle identities.
- **What it is NOT:** Necessarily Evidence, a Decision, verified Truth, or a closed set of event kinds.
- **Relationships:** Is emitted during an Execution Session, contributes to Operational Lineage, and may support Verification.

### Completion
- **Definition:** An attributable claim that an Execution Attempt ended with specified reported results.
- **Purpose:** Marks the Runtime boundary for independent evaluation.
- **What it is:** A completion claim with associated References.
- **What it is NOT:** Verification, successful Outcome, or Truth.
- **Relationships:** Ends an Attempt and is evaluated by Verification.

### Outcome
- **Definition:** The normalized, governed disposition of work after relevant completion and verification information is considered.
- **Purpose:** Provides a stable downstream result.
- **What it is:** A resolved lifecycle result with basis and Authority.
- **What it is NOT:** A Decision process, raw provider output, or Completion claim.
- **Relationships:** Is established by Decisions and may feed Operational Learning.

### Decision
- **Definition:** An attributable selection or judgment among defined alternatives under stated criteria.
- **Purpose:** Makes governed choices explicit and traceable.
- **What it is:** What an Authority determined, when, and why.
- **What it is NOT:** The Authority, an observed Event, or resulting Outcome.
- **Relationships:** Is asserted by Authority, supported by Evidence and Assessment, and may determine Outcome.

### Authority
- **Definition:** The explicitly identified person, organization, system, or delegated role accountable for an assertion, Decision, or grant.
- **Purpose:** Makes responsibility and legitimacy traceable.
- **What it is:** Attribution plus applicable scope or basis.
- **What it is NOT:** A Decision, credential, Claim, or automatic runtime capability.
- **Relationships:** Asserts Decisions, Assessments, Interpretations, Leases, and Outcomes; delegation uses Reference.

### Evidence
- **Definition:** Referenced material offered to support or challenge a claim.
- **Purpose:** Preserves an inspectable evaluative basis.
- **What it is:** Source material with identity, provenance, and context.
- **What it is NOT:** An Observation itself, Assessment, Interpretation, or guaranteed Truth.
- **Relationships:** May embody Observation and supports Assessment, Verification, and Decision.

### Observation
- **Definition:** An attributable record of something perceived, measured, or reported at a time and in a context.
- **Purpose:** Captures what was encountered before judgment.
- **What it is:** A claim about an occurrence or condition.
- **What it is NOT:** Its supporting material, an Assessment, or an explanation.
- **Relationships:** May be supported by Evidence and evaluated by Assessment.

### Assessment
- **Definition:** An attributable evaluation of facts or claims against declared criteria using identified Evidence and method.
- **Purpose:** Produces reviewable judgment without altering sources.
- **What it is:** A criteria-based evaluative result.
- **What it is NOT:** Evidence, raw Observation, or open-ended explanation.
- **Relationships:** Supports Decisions and Verification and may inform Interpretation.

### Interpretation
- **Definition:** An attributable explanation of meaning, significance, or implications derived from information.
- **Purpose:** Communicates understanding without presenting it as source material or criteria-based judgment.
- **What it is:** A reasoned semantic account.
- **What it is NOT:** Evidence, Fact, Assessment, or Decision unless separately declared.
- **Relationships:** May draw on Observations, Evidence, Facts, Inferences, and Assessments.

### Fact
- **Definition:** A proposition treated as established within a stated scope because acceptance criteria were met.
- **Purpose:** Identifies what may be relied upon while preserving basis and scope.
- **What it is:** A qualified, attributable accepted proposition.
- **What it is NOT:** Context-free Truth or a merely derived conclusion.
- **Relationships:** Is supported by Evidence or authoritative records and may ground Inference.

### Inference
- **Definition:** A proposition derived by reasoning from facts, observations, or assumptions.
- **Purpose:** Distinguishes derived conclusions from accepted source propositions.
- **What it is:** An attributable conclusion with traceable basis and method.
- **What it is NOT:** A Fact solely because its premises are facts.
- **Relationships:** May support Assessment or Interpretation; premises belong in Evidence or References.

### Relationship
- **Definition:** A typed, directed association between identified subjects.
- **Purpose:** Connects subjects without merging identities.
- **What it is:** An attributable link with defined semantics.
- **What it is NOT:** Identity, containment by default, or embedded duplication.
- **Relationships:** Uses References and may contribute to Semantic Lineage.

### Reference
- **Definition:** A value identifying or locating another subject or resource without embedding it.
- **Purpose:** Preserves boundaries while enabling resolution and traceability.
- **What it is:** An identifier, locator, or resolvable pointer with declared semantics.
- **What it is NOT:** The subject, proof of existence, or the containing value's Identity.
- **Relationships:** Used by Relationships, Evidence, delegation, Protected References, and Secret Handles.

### Identity
- **Definition:** The stable basis distinguishing a subject from every other subject across its lifecycle.
- **Purpose:** Enables durable correlation independent of mutable content or location.
- **What it is:** A property of the identified subject.
- **What it is NOT:** Another subject's Reference, display name, Version, or serialization.
- **Relationships:** References carry or resolve Identity; Revision preserves it when the subject remains the same.

### Version
- **Definition:** An identifier for a defined contract, schema, protocol, or released artifact state used to govern compatibility.
- **Purpose:** Makes compatibility expectations explicit.
- **What it is:** A label in a declared versioning scheme.
- **What it is NOT:** An entity update counter, timestamp, or Revision.
- **Relationships:** Contracts and serializations have Versions; multiple Revisions may conform to one Version.

### Revision
- **Definition:** A distinct recorded state of the same subject created by intentional change.
- **Purpose:** Preserves change history while retaining Identity.
- **What it is:** A successor state with lineage to a prior state.
- **What it is NOT:** A schema Version, new Identity, or erased history.
- **Relationships:** Participates in Lifecycle and Operational or Semantic Lineage.

### Serialization
- **Definition:** Deterministic representation and reconstruction of a Contract value for exchange or storage.
- **Purpose:** Carries Contract meaning across boundaries.
- **What it is:** A version-governed mapping between value and encoded form.
- **What it is NOT:** Validation, persistence, transport, or the Contract.
- **Relationships:** Conforms to Contract Version and is checked by Validation.

### Lifecycle
- **Definition:** The defined progression of meaningful states and transitions for a subject.
- **Purpose:** Makes allowed change and historical position explicit.
- **What it is:** A state-transition model with attributable transitions.
- **What it is NOT:** Current Operational State, duration, or implementation workflow.
- **Relationships:** Revisions and Events record transitions; Operational Lineage correlates them.

### Operational State
- **Definition:** A subject's declared current condition regarding ability to serve its operational purpose.
- **Purpose:** Communicates present usability independently of Lifecycle.
- **What it is:** A time-scoped, attributable status.
- **What it is NOT:** Lifecycle stage, Outcome, or permanent Truth.
- **Relationships:** May be supported by Observations and Evidence and changed by governed Revision.

### Operational Lineage
- **Definition:** Dexter-owned correlation of identities, Decisions, and facts across Dexter's operational lifecycles.
- **Purpose:** Enables audit, reconstruction, diagnosis, and accountability.
- **What it is:** A durable record of what Dexter received, decided, attempted, reported, verified, and resolved.
- **What it is NOT:** Semantic Lineage, raw logs, or an optional external prerequisite.
- **Relationships:** Connects Submission through Outcome and exists independently of Semantic Lineage.

### Semantic Lineage
- **Definition:** A graph of meaning, derivation, influence, or conceptual dependency among information and subjects.
- **Purpose:** Explains how meaning or Knowledge is derived.
- **What it is:** An optional semantic account built from attributable links.
- **What it is NOT:** Dexter's operational audit trail or a prerequisite for Operational Lineage.
- **Relationships:** May consume Operational Lineage and Relationships but cannot gate or rewrite them.

### Learning
- **Definition:** A governed process changing future behavior or Knowledge based on prior information.
- **Purpose:** Improves subsequent decisions or performance while preserving the basis for change.
- **What it is:** An attributable adaptation process.
- **What it is NOT:** Storage, unverified accumulation, or telemetry.
- **Relationships:** Operational Learning is its execution-domain form.

### Operational Learning
- **Definition:** Governed Learning from verified Outcomes and Operational Lineage.
- **Purpose:** Converts trusted operational history into accountable improvement.
- **What it is:** A downstream consumer of verified results.
- **What it is NOT:** Verification, raw-event processing, or a prerequisite for Execution or lineage.
- **Relationships:** Follows Verification and consumes Outcomes and Operational Lineage.

### Knowledge
- **Definition:** A maintained body of attributable propositions and relationships accepted for use within a stated scope.
- **Purpose:** Supports reasoning and action while retaining basis, Authority, and uncertainty.
- **What it is:** Governed, revisable information.
- **What it is NOT:** Context-free Truth, raw Evidence, or unexplained model state.
- **Relationships:** May contain Facts and qualified Inferences and be updated through Learning.

### Truth
- **Definition:** The condition of a proposition corresponding to reality, independent of whether Dexter knows it.
- **Purpose:** Preserves reality as the ultimate standard for claims.
- **What it is:** A proposition's property in relation to reality.
- **What it is NOT:** Confidence, Authority assertion, database value, Fact status, or consensus.
- **Relationships:** Evidence and Verification may justify belief about Truth but do not create it.

### Unknown
- **Definition:** Available information is insufficient to determine the applicable value or proposition.
- **Purpose:** Avoids inventing a result.
- **What it is:** An explicit epistemic state.
- **What it is NOT:** Unsupported, Contradictory, Not Applicable, false, or omitted.
- **Relationships:** May be resolved by Evidence or Assessment.

### Unsupported
- **Definition:** A proposition, operation, capability, or value is not supported under the applicable Contract or scope.
- **Purpose:** Distinguishes unavailable support from missing knowledge.
- **What it is:** An explicit supported-behavior boundary.
- **What it is NOT:** Unknown, Contradictory, failed, or Not Applicable.
- **Relationships:** May describe Contract Version, Provider Capability, or requested operation.

### Contradictory
- **Definition:** Applicable claims or Evidence cannot all be true together under the stated interpretation.
- **Purpose:** Preserves conflict instead of collapsing it into uncertainty.
- **What it is:** An explicit inconsistency with traceable sources.
- **What it is NOT:** Unknown, Unsupported, automatically false, or permission to discard Evidence.
- **Relationships:** Requires retained Evidence and may trigger Assessment or Decision.

### Not Applicable
- **Definition:** A field, criterion, operation, or proposition does not pertain in the stated context.
- **Purpose:** Distinguishes irrelevance from absence or lack of support.
- **What it is:** A contextual determination with explicit basis.
- **What it is NOT:** Unknown, Unsupported, empty, false, or Contradictory.
- **Relationships:** May result from Validation or Assessment when criteria exclude the subject.

### Protected Reference
- **Definition:** A Reference whose target or resolution details require controlled access.
- **Purpose:** Enables governed use of sensitive resources without embedding them.
- **What it is:** An opaque or access-controlled pointer with handling requirements.
- **What it is NOT:** The protected value, a credential, or proof of authorization.
- **Relationships:** Resolves only under explicit Authority; Secret Handle is a specialization.

### Secret Handle
- **Definition:** An opaque Reference through which an authorized mechanism may request use of a secret without exposing it.
- **Purpose:** Keeps secrets outside Contracts, Events, logs, and serialized domain values.
- **What it is:** A non-secret identifier for a controlled resolver.
- **What it is NOT:** A secret, plaintext credential, authority grant, or proof of resolution.
- **Relationships:** Is a Protected Reference used under explicit Authority and least privilege.

## Required distinctions

| Terms | Canonical distinction |
| --- | --- |
| Observation vs Evidence | Observation states what was perceived, measured, or reported; Evidence is material offered to support or challenge a claim. |
| Evidence vs Assessment | Evidence is source material; Assessment applies declared criteria and method to it. |
| Assessment vs Interpretation | Assessment is a criteria-based judgment; Interpretation explains meaning or significance. |
| Fact vs Inference | Fact is accepted as established in scope; Inference is a conclusion derived from premises. |
| Authority vs Decision | Authority identifies who is accountable and its basis; Decision records what that Authority determined. |
| Decision vs Outcome | Decision is a choice or judgment; Outcome is the normalized disposition after relevant Decisions and facts. |
| Submission vs Admission | Submission requests consideration; Admission authoritatively accepts or rejects it. |
| Admission vs Execution | Admission permits lifecycle entry; Execution subsequently coordinates, attempts, verifies, and resolves work. |
| Claim vs Lease | Worker Claim asserts responsibility; Lease grants time-bounded authority. Claim alone grants none. |
| Lease vs Provider Assignment | Lease authorizes a Worker within limits; Provider Assignment selects and binds a Provider. |
| Execution vs Verification | Execution performs and records work; Verification independently evaluates its claims afterward. |
| Verification vs Operational Learning | Verification evaluates acceptability; Operational Learning uses verified Outcomes to improve future behavior. |
| Operational Lineage vs Semantic Lineage | Operational Lineage is Dexter's required lifecycle audit; Semantic Lineage is optional meaning and derivation and can never gate it. |
| Validation vs Verification | Validation checks Contract conformance; Verification checks execution claims against Evidence and criteria. |
| Identity vs Reference | Identity distinguishes a subject; Reference identifies or locates it from another context. |
| Version vs Revision | Version governs compatibility; Revision records a changed state of the same subject. |

## Interpretation rules

Unknown, Unsupported, Contradictory, and Not Applicable must never be collapsed. Recording an assertion does not establish Truth. Attribution does not imply authorization. No future concept defined here implies present implementation.
