# Dexter Constitution

- **Version:** 1
- **Status:** Adopted
- **Date:** 2026-07-23
- **Artifact:** ARCH-WP-009

## Purpose

Dexter exists to make consequential action governable. It provides a basis for
representing identity, authority, evidence, decisions, behavior, outcomes, and
lineage without obscuring who acted, what occurred, or why a conclusion was
reached.

This Constitution defines the enduring principles from which Dexter's
architecture, engineering, implementation, behavior, governance, and future
federation derive. It governs principles, not implementation. All subordinate
standards, decisions, contracts, work packages, and systems shall remain
consistent with it.

## Mission

Dexter's mission is to enable reliable, accountable work by humans,
automation, and AI under explicit authority, evidence-based reasoning, and
verifiable operational lineage.

## Vision

Dexter seeks to enable systems that can coordinate and evolve across changing
implementations without surrendering human authority, operational truth,
traceability, or reproducibility. Such systems shall exchange evidence and
outcomes while retaining local governance, provenance, and accountability.

## Core principles

1. **Reality before abstraction.** Dexter shall model demonstrated reality
   before introducing generalized concepts or speculative structure.
2. **Contracts before side effects.** Stable meaning, boundaries, and
   invariants shall be established before actions that affect external state.
3. **Governance before execution.** Admissibility, authority, and
   accountability shall be explicit before execution proceeds.
4. **Evidence before conclusion.** Conclusions shall identify the evidence,
   criteria, and reasoning that support them.
5. **Verification before learning.** Execution claims shall be independently
   evaluated before their outcomes influence future behavior.
6. **Human authority over autonomous execution.** Autonomous capability shall
   remain bounded by explicit human authority and accountable human governance.
7. **Operational lineage before optimization.** Dexter shall preserve the
   accountable record of work before optimizing how work is performed.
8. **Incremental engineering over speculative complexity.** Dexter shall
   evolve through the smallest coherent, verified changes supported by
   demonstrated need.

These principles impose a one-way dependency:

```text
principles
    ↓
architecture
    ↓
engineering
    ↓
implementation
    ↓
behavior
    ↓
verified behavior
    ↓
learning
```

Optimization shall never reverse this dependency direction. No learned,
optimized, or implementation-specific behavior may redefine the principles,
architecture, or engineering obligations from which it derives.

## Foundational invariants

The following shall remain true regardless of implementation:

- Every meaningful action, assertion, decision, and conclusion shall be
  attributable.
- Authority shall always be explicit, bounded, and traceable to its basis.
- Attribution shall not be treated as authorization.
- Evidence shall remain distinguishable from observation, assessment,
  interpretation, inference, and fact.
- Unknown shall not silently become known, false, unsupported, contradictory,
  or not applicable.
- Contradiction shall be preserved with its supporting evidence until
  resolved by an attributable decision.
- Operational lineage shall remain preserved and owned by Dexter.
- Verification shall remain distinct from execution.
- Learning shall consume verified outcomes, not raw claims or unverified
  behavior.
- Protected references shall not expose protected values. A reference or
  handle shall never be treated as the protected value or as proof of
  authority.
- Contracts shall remain explicit, versioned, deterministic, and independent
  of incidental infrastructure.
- Governance decisions shall remain distinguishable from the actions they
  authorize.
- Claims of completion shall not constitute verified completion.
- Semantic lineage shall never be a prerequisite for operational correctness
  or operational lineage.
- Human authority shall remain superior to delegated autonomous authority.

## Human governance

Human operators are the ultimate governing authorities for Dexter. Under
applicable organizational policy, authorized humans shall:

- approve architecture and constitutional interpretation;
- approve merges and releases;
- approve grants, limits, and delegation of authority;
- define acceptable risk and adjudicate unresolved contradiction;
- ensure that autonomous operation remains observable and interruptible; and
- remain accountable for operational decisions made under their authority.

Automation may inform, prepare, enforce, or record a decision. It shall not
convert those functions into authority that no human explicitly granted.

## AI responsibilities

AI engineering contributors shall operate as bounded contributors, not
governing authorities. They shall:

- preserve repository integrity and remain within granted scope;
- inspect available reality before acting;
- reject or surface contradictory assumptions rather than silently choosing
  among them;
- stop and disclose uncertainty when it prevents a trustworthy result;
- never fabricate evidence, execution, verification, approval, or completion;
- never bypass, suppress, or misrepresent verification;
- document consequential assumptions and distinguish them from facts;
- preserve accepted architectural decisions and constitutional dependency
  direction; and
- defer authority-sensitive decisions to accountable humans.

Capability does not imply permission. Successful execution does not imply
correctness, approval, or authority.

## Decision philosophy

Dexter shall prefer decisions grounded in:

1. observed reality;
2. attributable evidence;
3. explicit authority and criteria;
4. repeatable evaluation;
5. clear operational lineage; and
6. incremental, reversible evolution where practicable.

A decision shall state enough context to determine what was decided, by whose
authority, from which evidence, under which criteria, and with what unresolved
uncertainty. Convenience, novelty, and optimization shall not outweigh
correctness, accountability, or traceability.

## Truth model

Dexter reasons from evidence, not assumption. The following distinctions are
constitutional:

- **Observation** records what was perceived, measured, or reported, together
  with its source and context.
- **Evidence** is attributable material offered to support or challenge a
  claim.
- **Assessment** evaluates evidence against declared criteria and method.
- **Interpretation** explains meaning or significance and remains attributable
  to its interpreter.
- **Fact** is a proposition accepted as established within an explicit scope
  and basis.
- **Inference** is a conclusion derived from stated premises and reasoning; it
  is not silently promoted to fact.
- **Truth** is what is actually the case, independent of whether Dexter has
  observed or established it.
- **Unknown** states that the available basis is insufficient to determine a
  proposition.
- **Contradiction** states that applicable claims or evidence cannot all be
  true together under the stated interpretation.

Recording an assertion does not establish truth. Confidence does not replace
evidence. Absence of evidence does not establish the opposite proposition.
Unknown and contradiction are valid, durable states and shall not be collapsed
for convenience.

## Governance philosophy

Governance exists to determine whether action is admissible, by whose
authority, within which limits, and with what accountability. It protects:

- correctness by requiring explicit criteria and decisions;
- traceability by retaining attribution, evidence, and lineage;
- reproducibility by making inputs, rules, and outcomes reviewable; and
- accountability by binding authority to decisions and consequences.

Governance shall precede execution and remain distinguishable from it.
Controls shall be proportionate to consequence, but no reduction in process
may make authority or accountability implicit.

## Architecture philosophy

Architecture translates constitutional principles into durable boundaries,
responsibilities, dependency direction, and invariants. It precedes
implementation because implementation choices are valid only within an
accepted structure.

Architecture shall separate meanings that carry different authority,
evidence, or trust. It shall prevent lower-level mechanisms from redefining
the contracts and governance they serve. Architecture shall change only in
response to demonstrated need and explicit, reviewable decisions.

## Engineering philosophy

Engineering translates accepted architecture into reviewable plans,
contracts, implementation, verification, and operational evidence. It shall
preserve architectural boundaries, avoid speculative complexity, and make
claims only to the extent supported by observed results.

Implementation follows engineering. Passing checks supports a claim of
conformance; it does not override architecture, grant authority, or establish
that untested behavior is correct. Failures and uncertainty shall be retained
as evidence, not hidden to produce apparent completion.

## Federation philosophy

Future federation shall preserve constitutional properties across independent
participants. Federated Dexter systems shall:

- respect each participant's local authority and governance;
- preserve provenance across every exchange and transformation;
- exchange attributable evidence rather than unsupported conclusions;
- retain attribution for actions, assertions, decisions, and outcomes;
- make trust boundaries and assumptions explicit;
- represent unknown and contradiction without forced agreement;
- avoid interpreting interoperability as delegated authority; and
- preserve each participant's ability to verify received claims.

Federation shall not erase local accountability, create implicit global
authority, or require participants to surrender operational lineage. This
Constitution defines no federation protocol.

## Relationship to future systems

Dexter may collaborate with external automation, AI agents, federated Dexter
nodes, and semantic systems. Every such relationship shall use explicit
boundaries, authority, provenance, evidence, and attribution. External claims
shall remain subject to local governance and verification.

AI agents and automation remain bounded actors. Federated nodes remain
independently governed participants. Semantic systems may enrich meaning,
discovery, and derivation, but they are optional consumers or contributors.
Future semantic systems shall not become prerequisites for Dexter's
operational correctness, governance, verification, or operational lineage.

## Amendment philosophy

Constitutional change shall be exceptional, deliberate, and traceable. An
amendment requires:

- explicit review and approval by accountable humans;
- architectural justification showing why subordinate change is insufficient;
- analysis of affected invariants, decisions, contracts, and obligations; and
- a durable repository record linking rationale, review, and adoption.

An amendment shall not be inferred from implementation, convention,
optimization, or repeated exception. Subordinate artifacts shall be reconciled
explicitly after an amendment. Historical constitutional states and their
reasons shall remain traceable.

## Closing statement

Dexter commits to explicit authority, attributable action, evidence-based
reasoning, preserved operational lineage, independent verification, and human
accountability. Its architecture shall derive from principles, its engineering
from architecture, its implementation from engineering, its behavior from
implementation, and its learning only from verified behavior. Dexter may
evolve in form; these commitments shall govern what remains true.
