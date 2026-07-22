# Language-change workflow

This is the sole operational guide for changing the Whitefoot language. A
specification update is one coordinated state transition across governance,
the numbered specification, compiler-independent evidence, the compiler, and
live documentation. None of those parts has an independent update lifecycle.

The directories named below contain records, resources, and tools used by this
workflow. Their local READMEs may explain formats and commands, but must not
define a second language-change process.

## Authority

- `docs/roadmap.md` alone defines current status, authorization, and next work.
- The active numbered file selected there is the sole language authority.
- `docs/constitution.md` is project law and `docs/patterns.md` defines writer
  forms.
- `mcts_mem/` records durable design choices, rejected alternatives, and the
  evidence behind them.
- `governance/APPROVALS.md` records explicit owner approval for protected
  changes.
- Compiler behavior, tests, reference models, candidates, and archived records
  never define language behavior.

## Parts of the loop

| Path | Role in a language change |
|---|---|
| `docs/roadmap.md` | Opens the work, names the active specification, and records the result and next work |
| `governance/spec-evolution/` | Holds the one exact successor candidate reviewed by the owner |
| `governance/APPROVALS.md` | Records exact-byte and protected-evidence approval |
| `spec/` | Holds immutable released specifications and supporting derivation evidence |
| `tests/conformance/` | Holds compiler-independent source-to-verdict evidence for the active specification |
| `tests/reference/` | Holds focused independent semantic models where a second implementation catches distinct errors |
| `compiler/` | Implements the active specification through the normal compiler path |
| `docs/patterns.md` and other live docs | Teach and describe the active language |
| `mcts_mem/` | Preserves why a durable design won over real alternatives |
| Root `Makefile` and `governance/hooks/` | Run the repository gate and protect released specification bytes |

`governance/` itself contains only this guide, the approval record, exact
successor candidates, and the tracked hook. Historical transition logs and
superseded review material live under `archive/governance/` and cannot
authorize current work.

## First classify the problem

Start from the active numbered specification, not from compiler behavior or a
test expectation.

- If the active specification already determines the behavior and the compiler
  disagrees, this is a compiler defect. Keep the specification and existing
  expectations unchanged, add the smallest useful regression, and fix the
  normal compiler path.
- If an existing conformance verdict or reference judgment contradicts the
  active specification, this is protected-evidence correction. Stop and obtain
  owner approval before changing or removing it. Do not change the language to
  preserve a bad test.
- If the specification is ambiguous, incomplete, or intentionally needs new
  behavior, enter the complete language-change loop below.
- If the compiler cannot yet implement valid specified behavior, report the
  capability as unsupported. An internal error, timeout, crash, or missing
  feature is never a source-language rejection and never changes an expected
  verdict.

An additive conformance or compiler regression for behavior already fixed by
the active specification does not require a specification version. It must
cite the existing rule and must not alter a protected expectation.

## The complete language-change loop

### 1. Open and bound the change

Confirm that the change unlocks current roadmap work. Consult the relevant live
MCTS node and rejected alternatives. State the smallest coherent semantic
change and the behavior that remains unchanged.

Before drafting, inventory every potentially affected surface and mark it
`change`, `unchanged` with a reason, or `not applicable`:

- grammar, lexical classes, canonical bytes, and syntax-node structure;
- name resolution, typing, ownership, effects, constants, and diagnostics;
- runtime values, traps, ABI behavior, and required safety checks;
- conformance sources, expected verdicts, and runnable/pending/xfail status;
- focused reference-model judgments and mutation tests;
- compiler identities, generated syntax data, frontend, semantics, lowering,
  backend, and runtime;
- writer patterns, examples, derivation evidence, and live documentation; and
- existing protected cases, verdicts, oracle data, or approval boundaries.

This impact inventory is part of the owner-review packet. It is not a new
repository document or a second proposal artifact.

### 2. Draft one successor candidate

A specification proposal and its candidate are one file:

```text
governance/spec-evolution/kernel-spec-vN-candidate.md
```

Copy the active specification and apply the smallest complete change. Update
the version, status, prior-version description, normative rules, examples, and
internal references together. Never edit, rename, or delete a released
`spec/kernel-spec-v*.md` file.

The candidate is non-authoritative and mutable during review. Every byte change
invalidates its earlier hash and review. Do not create a separate
`PROPOSAL.md`, patch document, generated duplicate, or per-version workflow.
Normal compilation and tests remain bound to the installed active
specification; only an explicitly invoked proposal-checking tool may read the
candidate before activation.

### 3. Prepare evidence before approval

Derive the expected behavior change from the candidate before implementing it.
Review every row of the impact inventory, including negative and near-miss
cases that prove required checks remain. Identify every existing conformance or
reference expectation that would need protected modification; do not silently
apply those changes before approval.

For a grammar or syntax change, run the compiler-sharing verifier:

```sh
cargo run --manifest-path compiler/Cargo.toml --bin whitefoot-grammar -- \
  governance/spec-evolution/kernel-spec-vN-candidate.md
```

The verifier uses the production frontend contract and fails closed on a
structural difference it cannot validate. Extend that shared native path when
the proposed grammar genuinely requires it; do not create an independent
parser or a script fork for the new version. Proposal tooling may inspect the
candidate, but it must not switch normal compilation to unapproved semantics.

Review the complete candidate for internal consistency, retained safety
checks, constitutional conflicts, MCTS conflicts, diagnostic determinism, and
the full derived-material impact. Implementation convenience is not evidence
for language behavior.

### 4. Obtain exact owner approval

Present one review packet containing:

- the candidate path, complete SHA-256, and concise semantic delta;
- the completed impact inventory;
- grammar-verifier and other independent evidence;
- every requested protected verdict, status, reference, or oracle change; and
- any remaining limitation or unsupported compiler capability.

Owner approval covers only the exact candidate bytes and explicitly listed
protected changes. A direction, plan, partial excerpt, or earlier hash is not
approval. If any candidate byte or protected-change boundary changes, return to
this step.

After explicit approval, append the exact artifact or change boundary, hash,
reason, and evidence pointer to `governance/APPROVALS.md`. Record a durable
design choice in `mcts_mem/` only when a real alternative existed; keep
approval bookkeeping and implementation activity out of the tree.

### 5. Activate the approved language as one repository change

Copy the approved candidate byte-for-byte to the new immutable
`spec/kernel-spec-vN.md`. In the same cohesive activation change:

1. switch `docs/roadmap.md` and every active specification identity to the new
   numbered file and digest;
2. update compiler syntax data, frontend, semantic rules, diagnostics,
   lowering, backend, and runtime wherever the impact inventory requires it;
3. update conformance sources, manifest expectations, statuses, coverage
   annotations, and active-spec identity;
4. update focused reference models, their tests, and mutation checks;
5. update writer patterns, examples, derivation evidence, and live docs; and
6. append the approval and MCTS records required by the approved change.

The specification may describe a capability the research compiler does not yet
support only when the roadmap says so explicitly. Such a gap remains an
unsupported compiler capability; conformance expectations still state the
language result and may not be rewritten as rejection. Moving an existing case
from runnable to pending or xfail is a protected weakening and must be part of
the owner's approval boundary.

Approved and installed candidates remain in `governance/spec-evolution/` as
compact exact-byte review evidence. A rejected or abandoned candidate that was
never installed moves to `archive/governance/spec-evolution/`; active source,
builds, tests, and tools must not depend on it.

### 6. Verify and close the loop

First prove that the installed specification is the approved object:

```sh
cmp governance/spec-evolution/kernel-spec-vN-candidate.md \
  spec/kernel-spec-vN.md
```

Then run the relevant component checks and the complete repository gate:

```sh
make -C compiler check
make conformance
make reference
make check
```

Run the exact grammar-candidate check as well when grammar or syntax changed.
Inspect the final diff against every impact-inventory row. A green gate proves
only the behavior it exercises; it does not excuse an omitted derived update.

Commit the activation as one cohesive state transition. Record completed
status and exact next work in `docs/roadmap.md`. Do not leave the repository in
a committed state where the active spec, compiler identity, conformance
identity, or reference material name different language versions.

## Resource boundaries

- `spec/` contains released specification resources and their derivation or
  reconciliation evidence. It contains no mutable current plan or per-version
  update script.
- `tests/conformance/` contains cases, the manifest, the compiler-independent
  runner, and tests of that tooling. It contains no language-design decision,
  compiler special case, or independent release process.
- `tests/reference/` contains narrow independent models and their tests. It is
  not a second compiler and cannot settle a disagreement with the spec.
- `governance/` contains the workflow resources listed above. Do not create a
  directives log, second how-to, free-standing proposal, or generated approval
  database.
- New scripts are not the workflow. Prefer the existing native compiler and
  root gates; a genuinely compiler-independent conformance tool must remain
  version-neutral and have an explicit caller.

## Checks and hooks

Install the tracked append-only hook once per worktree:

```sh
make install-hooks
```

The hook invokes `make spec-append-only-staged`. The ordinary repository gate
invokes `make repository-invariants` and `make spec-append-only` alongside the
compiler-independent evidence and compiler checks. These mechanisms protect
specific invariants; responsibility for completing the whole loop remains with
the person or agent changing the language.
