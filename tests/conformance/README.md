# Compiler-independent conformance resources

This directory supplies the source-to-verdict evidence used by the complete
language-change workflow in `governance/README.md`. It tests the language rather
than compiler internals, but it is not an independent authority or release
process. The active numbered specification alone determines every expected
result.

## Resources

- `cases/<id>.wf` is one canonical Whitefoot source program and FORM-1/2 byte
  fixture.
- `manifest.jsonl` maps each case to the rule or rules it exercises, its
  expected result, and its current execution status. It also contains explicit
  coverage annotations for specification properties that no source program can
  exercise.
- `runner.py` validates active-spec identity, reports rule coverage, and owns
  the intentionally explicit compiler-adapter slot.
- `test_runner.py` tests the corpus plumbing and active-spec binding.

A case entry has this shape:

```json
{"id": "reject-own10-dangle", "rules": ["OWN-10"],
 "expect": {"kind": "reject", "rule": "OWN-10"},
 "status": "runnable",
 "doc": "Returning a borrow of an own param into a caller region dangles; rejected."}
```

`expect` is one of:

- `{"kind":"accept"}`;
- `{"kind":"reject","rule":R}`;
- `{"kind":"run","exit":N}`; or
- `{"kind":"trap"}`.

A rejection expectation includes the exact rule identifier required by
DIAG-1. Compiler failure, timeout, crash, or missing capability is never a
rejection verdict.

`status` describes execution availability, not language meaning:

- `runnable` means the current adapter must produce `expect`;
- `pending` means the compiler cannot yet execute the case;
- `xfail` preserves the correct expectation while exposing a known compiler
  mismatch, and an unexpected match is reported as `XPASS`.

Changing an existing expectation, removing a case, or weakening runnable
status is protected work governed by `governance/README.md`. An additive case
for behavior already fixed by the active specification may land with ordinary
compiler work when it cites the existing rule and changes no protected result.

## Tools

From the repository root:

```sh
make conformance
python3 -B tests/conformance/runner.py coverage
make conformance-run
```

`make conformance` checks the corpus tooling and coverage. `make
conformance-run` requires an installed compiler adapter and fails explicitly
while the adapter slot is empty. Any future adapter must drive source through
the normal compiler command path; no stable adapter protocol or second
semantic implementation is required here.
