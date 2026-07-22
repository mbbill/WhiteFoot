# Whitefoot conformance suite

A **spec-anchored, rule-keyed, toolchain-agnostic** test system. It tests the
*language* — `source → verdict` — rather than compiler internals, so the same
suite can validate the future production Rust compiler and any later
replacement.

It is a production artifact of the toolchain. Compiler implementations are
replaceable; the guarantees this suite pins are not.

## Layout
- `cases/<id>.wf` — one canonical Whitefoot program per case (also a FORM-1/2 byte-exact fixture).
- `manifest.jsonl` — one JSON object per case: the rule id(s) it exercises + the expected verdict + status.
- `runner.py` — the coverage tracker plus an intentionally unpopulated
  toolchain **adapter** slot.

## A case
```json
{"id": "reject-own10-dangle", "rules": ["OWN-10"],
 "expect": {"kind": "reject", "rule": "OWN-10"}, "status": "runnable",
 "doc": "Returning a borrow of an own param into a caller region dangles; rejected."}
```
`expect` is one of: `{"kind":"accept"}`, `{"kind":"reject","rule":R}`, `{"kind":"run","exit":N}`,
`{"kind":"trap"}`. For a rejection the runner asserts the **exact cited rule id** (DIAG-1).

`status`:
- **runnable** — the toolchain must produce `expect`; a mismatch is a `FAIL`.
- **pending** — the toolchain can't process the case yet (a construct it doesn't support, or
  it rejects without citing a rule id); skipped, but the case still counts for coverage and
  becomes runnable for free once the toolchain grows.
- **xfail** — `expect` is the *correct spec behavior*, but the current toolchain does **not**
  produce it (a tracked gap). Reported, non-failing. If it starts matching, it flags `XPASS`
  ("fix landed — drop the xfail"). This is how known gaps stay visible instead of forgotten.

## Run
```
python3 conformance/runner.py run        # requires an installed compiler adapter
python3 conformance/runner.py coverage   # which of the spec's rules have a case
python3 conformance/runner.py all -v     # run plus coverage; unavailable before adapter
make conformance                         # current corpus/coverage integrity gate
```

## Adding a case
Write `cases/<id>.wf` in canonical form, add a manifest line tagging the rule(s) and the
expected verdict. Prefer one rule per negative case (so the coverage map is precise). To
close a coverage gap, target a rule from the `untested` list the coverage report prints.

## Plugging in a future compiler

Phase 2 does not install a compiler adapter. After the roadmap's applicable
frontend, semantic, artifact, and lowering entrance gates are satisfied, a
separately authorized integration may replace the `ADAPTER` slot with a
selectable, structured adapter protocol. Semantic expectations stay in this
corpus; compiler capability and failures stay in adapter-owned data. The
corpus is the contract and the implementation behind an adapter is
replaceable.
