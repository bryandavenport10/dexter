# Dexter Engineering Standard

- **Version:** 1
- **Status:** Adopted
- **Date:** 2026-07-23
- **Artifact:** ARCH-WP-007

## Purpose and scope

The Dexter Engineering Standard (DES) is the canonical engineering handbook
for human contributors and AI engineering agents working in the Dexter
repository. Work packages may reference this document instead of repeating
these policies.

The DES governs how repository changes are proposed, implemented, verified,
reviewed, and released. It does not define runtime behavior. Governed Entity
semantics belong to the contract, and durable architecture decisions belong to
ADRs.

When instructions conflict, preserve the repository and stop for human
direction. A work package may impose stricter requirements than this standard,
but it may not silently weaken an accepted contract, ADR, protection rule, or
approval requirement.

## Repository philosophy

Dexter engineering follows four ordered principles:

1. **Reality before abstraction.** Model demonstrated needs. Do not introduce
   speculative frameworks, empty packages, or generalized machinery without a
   concrete use case.
2. **Contracts before side effects.** Define stable values, validation,
   compatibility, and boundaries before adding I/O or execution mechanisms.
3. **Governance before execution.** Make authority, policy, evidence, and
   admissibility explicit before permitting work to execute.
4. **Human approval before merge.** Automation and AI may prepare and verify a
   change; an authorized human decides whether it enters the protected branch.

Prefer small, reviewable changes with explicit evidence over broad changes
whose correctness depends on assumption. Preserve public behavior unless the
approved work explicitly changes it.

## Repository layout

The current canonical layout is:

```text
.
├── docs/
│   ├── adr/                 # Accepted and proposed architecture decisions
│   ├── engineering/         # Engineering standards and contributor policy
│   └── contract.md          # Governed Entity Contract
├── examples/                # Executable usage examples
├── scripts/                 # Repository verification and maintenance scripts
├── src/dexter_core/         # Shipped Python package
├── tests/                   # Automated tests
├── README.md                # Repository entry point
├── pyproject.toml           # Build, package, dependency, and tool metadata
└── uv.lock                  # Reproducible dependency resolution
```

Do not create a directory merely to reserve a future namespace. Add a package
only when it owns a concrete, reviewed contract or implementation. New layout
decisions must follow accepted ADRs. In particular, the runtime package
architecture and dependency rules are governed by
[`ADR-0001`](../adr/ADR-0001-runtime-package-architecture.md).

## Branch naming conventions

Create one short-lived branch per issue or work package. Use lowercase
kebab-case after a category prefix:

```text
arch/<work-or-decision>
eng/<engineering-change>
feat/<feature>
fix/<defect>
docs/<documentation-change>
hotfix/<urgent-production-fix>
```

Examples include `arch/wp-007-dexter-engineering-standard`,
`feat/submission-contract`, and `fix/entity-validation`. Use `arch/` for
architecture work and ADRs, `eng/` for tooling or engineering practice,
`docs/` for documentation-only changes, and `hotfix/` only for urgent,
release-impacting corrections.

Branches must identify one coherent outcome. Do not combine unrelated cleanup
or opportunistic refactoring with scoped work.

## Work package lifecycle

Every material change follows this lifecycle:

```text
Issue
  ↓
Branch
  ↓
Implementation
  ↓
Verification
  ↓
Commit
  ↓
Human Review
  ↓
Push
  ↓
Pull Request
  ↓
Merge
  ↓
Delete Branch
```

The issue or work package defines scope, acceptance criteria, exclusions, and
required verification. Implementation remains within that scope. Verification
produces evidence before the commit is presented for review. The pre-push human
review confirms that the local commit is appropriate to publish. The pull
request supplies the durable review record and required merge approval.

Do not push when a work package says “commit only.” Do not merge merely because
checks pass. After merge, delete the branch unless it has an explicitly
documented continuing purpose.

## Commit message conventions

Each commit must be focused, buildable, and reviewable. Use an imperative,
present-tense subject that describes the outcome:

```text
Document Dexter engineering standard
Add submission contract validation
Fix entity relationship serialization
```

Subjects should normally be no more than 72 characters, start with a capital
letter, and omit a trailing period. Avoid vague subjects such as “updates,”
“changes,” or “WIP.”

Use a body when the reason, trade-off, compatibility impact, or verification is
not evident from the diff. Reference the issue, work package, or ADR when it
improves traceability. Do not claim tests or completion that were not observed.
Never commit secrets, credentials, generated caches, editor state, or unrelated
changes.

## Pull request requirements

A pull request must:

- identify its issue or work package;
- state the problem and the implemented outcome;
- describe scope and explicit non-goals;
- identify public API, wire-format, dependency, security, or migration impact;
- link new or affected ADRs and contracts;
- list the exact verification commands run and their results;
- disclose skipped checks, known risks, follow-up work, and deviations;
- contain only relevant, reviewable commits; and
- receive all required checks and human approvals before merge.

Authors must review their own diff before requesting review. Review feedback
must be resolved through code or a recorded technical rationale. A later change
that invalidates an approval requires renewed review under repository policy.

## ADR requirements

Create an Architecture Decision Record when a change establishes or materially
alters durable structure, dependency direction, public contracts, data or wire
formats, security boundaries, technology choices, or cross-cutting engineering
policy. Routine implementation within an accepted decision does not need a new
ADR.

ADRs live in `docs/adr/` and use the next sequential `ADR-NNNN` identifier.
Each ADR must include:

- title, status, date, and originating artifact;
- context and problem statement;
- decision drivers and viable alternatives;
- the decision and its boundaries;
- consequences, risks, and rejected alternatives;
- compatibility or migration implications;
- explicit non-goals; and
- verification appropriate to the decision.

Accepted ADRs are authoritative. Supersede them with another reviewed ADR; do
not silently contradict or rewrite their decisions. Historical ADRs remain in
the repository with their status updated and successor linked.

## Testing requirements

Tests are executable contract evidence. Every behavior change requires tests
at the lowest useful boundary, including success, failure, and edge cases.
Defect fixes require a regression test that fails without the fix when
practical. Serialization or public-contract changes require round-trip,
validation, unknown-field, and compatibility coverage appropriate to their
risk.

Tests must be deterministic, isolated, and independent of execution order.
Control time, randomness, external services, and filesystem state explicitly.
Do not weaken, skip, delete, or rewrite a failing test merely to make a change
pass. Update a test only when an approved change intentionally changes the
contract it asserts, and make that reason reviewable.

The baseline verification commands are:

```bash
uv sync
uv run pytest
bash scripts/check.sh
git diff --check
```

Run additional type, build, security, compatibility, or integration checks
when the affected surface requires them. Record any check that cannot be run
and obtain human direction; absence of evidence is not a passing result.

## Documentation requirements

Documentation is part of the change, not deferred cleanup. Update the README,
contracts, examples, API documentation, engineering standard, and ADRs in the
same work package when their claims would otherwise become inaccurate.

Documentation must distinguish current behavior, accepted future architecture,
and speculation. Examples must be executable or otherwise verified. Links and
commands must be repository-relative, current, and reproducible. Do not
duplicate policy when a stable link to this standard is sufficient.

## Verification checklist

Before presenting a change for review, confirm:

- [ ] The diff matches the issue or work package and respects its exclusions.
- [ ] Repository assumptions were inspected and still hold.
- [ ] Public APIs, schemas, and behavior are unchanged unless explicitly
      authorized and documented.
- [ ] Dependency direction and accepted ADR decisions are preserved.
- [ ] New or changed behavior has proportionate automated tests.
- [ ] `uv sync` completes successfully.
- [ ] `uv run pytest` passes.
- [ ] `bash scripts/check.sh` passes.
- [ ] `git diff --check` reports no whitespace errors.
- [ ] Documentation, examples, contract text, and ADRs are consistent.
- [ ] No secrets, caches, build artifacts, or unrelated changes are included.
- [ ] The final diff and repository status were inspected.
- [ ] Verification results and remaining risks are reported truthfully.

Work packages may add checks. A required check may be omitted only when a human
explicitly accepts the reason and risk.

## Code review expectations

Review evaluates correctness, not only style. Reviewers should examine:

- agreement with the issue, work package, contracts, and accepted ADRs;
- behavior at failure paths, boundaries, and compatibility surfaces;
- preservation of dependency direction and side-effect boundaries;
- authority, evidence, provenance, security, and data handling;
- test quality and whether verification supports the completion claim;
- documentation accuracy and migration clarity; and
- unnecessary complexity, speculative abstraction, or unrelated scope.

Authors provide evidence and respond directly to concerns. Reviewers identify
blocking issues clearly and avoid expanding scope without opening follow-up
work. No contributor approves their own change as the required human reviewer.

## AI engineering expectations

AI engineering agents are contributors under the same contracts, ADRs,
verification rules, and review requirements as humans. They must:

- inspect repository reality before acting and state consequential assumptions;
- remain within the authorized work package and preserve user-owned changes;
- never bypass, suppress, or misrepresent failing tests;
- never fabricate commands, results, files, commits, review, or completion;
- never merge without explicit human approval;
- stop and request direction when repository assumptions differ materially
  from the work package;
- preserve the dependency direction established by accepted architecture;
- preserve ADR decisions unless explicitly tasked to propose a superseding ADR;
- avoid destructive or external actions not authorized by the task;
- report incomplete verification, uncertainty, and blockers plainly; and
- leave a reviewable diff with no hidden unrelated work.

An agent may make low-risk implementation assumptions within scope. It must not
infer authority for public behavior changes, architectural reversals, releases,
pushes, or merges. Passing automation does not grant approval.

## Repository protection principles

The canonical branch is protected conceptually even when hosting controls are
not available. Apply these principles:

- changes enter the canonical branch through reviewed pull requests;
- required checks and human approval gate merge;
- direct pushes and force pushes to protected branches are prohibited;
- branch deletion, history rewriting, and tag replacement require explicit
  authority;
- least privilege applies to credentials, automation, and release access;
- secrets never enter source, fixtures, logs, commits, or pull requests;
- pinned lock data and reproducible tooling are preserved;
- generated or vendored content records its source and update process; and
- audit history is retained through issues, commits, reviews, ADRs, and release
  records.

Protection is a workflow property as well as a hosting setting. If an automated
control is absent, contributors still follow the rule.

## Definition of Done

A change is done only when:

1. its stated acceptance criteria are satisfied and exclusions respected;
2. implementation and documentation agree with contracts and accepted ADRs;
3. required tests and checks pass with recorded, truthful results;
4. the diff contains no unrelated changes or prohibited artifacts;
5. compatibility, migration, security, and operational impacts are addressed;
6. the commit history is coherent and the pull request is complete;
7. required human review and approval are recorded;
8. the change is merged into the canonical branch; and
9. the short-lived branch is deleted.

A work package that ends at “commit only” is complete for handoff when its
scoped commit and verification evidence are ready; it is not yet repository
Done until review, merge, and branch cleanup occur.

## Release philosophy

Dexter releases reviewed reality, not aspiration. Release the smallest coherent
set of contracts and behavior that is verified, documented, and supportable.
Do not use a release to legitimize incomplete work or speculative APIs.

Package versions and serialized contract versions are independent. Apply
semantic versioning to published packages and explicit, family-specific
versioning to wire contracts. Compatibility claims require tests and migration
guidance; breaking changes require deliberate approval and an appropriate
major-version path.

Every release must be reproducible from an identified commit, pass the required
verification suite, include accurate release notes, and receive human
authorization. Tags and published artifacts are immutable. Urgent hotfixes
follow the same contract, testing, review, and approval requirements, with
scope minimized to the production risk.
