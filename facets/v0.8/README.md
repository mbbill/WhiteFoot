# Exact-v0.8 facet foundation

This directory is bound to `spec/kernel-spec-v0.8.md`, SHA-256
`d04336f7fa8d1a6a0f03fe58a17f972b658217a73a3dff91a906b4ba295328a8`.
It is compiler-independent.

`source.json` is a generated structural index. It accounts for exact source
atoms and their zero-based half-open byte spans:

- 91 line-start rule definitions;
- 57 productions in the four GRAM-2 through GRAM-5 fences;
- two additional inline productions owned by EFF-1;
- 44 OP-1 table rows containing 84 name occurrences and 83 unique spellings;
- four DIAG-3 report rows; and
- the opaque exact-byte PRE-1 and EX-1 payloads.

These are integrity facts, not semantic facets and not compiler progress. A rule
can carry several independent premises and transitions; some operation semantics
live outside the OP-1 table. No tool may infer semantic completeness by counting
these atoms.

The index also exposes two different source sets without interpreting them: the
OP-1 table contains 51 distinct dotless operation identifiers, while the
following dotless parenthetical lists 20. Call resolution itself is explicit:
an IDENT names a table operation wherever the table defines that spelling. The
ambiguity is which dotless identifiers the next sentence makes RESERVED against
user declarations and bindings. A future numbered specification requires exact
owner approval; v0.8 must not be silently rewritten.

There is also an open protected-surface discrepancy outside the source index.
FORM-2 forbids whitespace before `(`, while a mechanical audit found the form
`fn name (` in 272 of 293 conformance source files, including 271 manifested
cases. Of those manifested cases, 259 are runnable and only two expect FORM-2
rejection, leaving at least 257 runnable expected verdicts that exact FORM-2
would preempt. The positive FORM-2 fixture itself uses the forbidden spelling.
Those protected files and verdicts cannot be normalized or changed without the
owner's exact approval and governance procedure.

The permanent boundary is:

1. this generated structural index;
2. an authored semantic decomposition containing only abstract facet ownership,
   source-atom references, required pipeline lanes, and evidence classes;
3. a generated static catalog binding those inputs;
4. a separate machine-checked discrepancy sidecar; and
5. a compiler-owned capability overlay containing shared handlers and concrete
   evidence, with completeness derived rather than asserted.

Compiler production code must not dispatch on facet IDs or consult capability
metadata to decide language behavior. Open discrepancies cannot waive an
obligation and block affected facet closure and release.

Regenerate and verify the structural index with:

```sh
python3 -B tools/facet_catalog.py write
python3 -B tools/facet_catalog.py check
python3 -B tools/test_facet_catalog.py
```

The generator accepts only the explicit v0.8 path and exact digest. It never
selects a numerically latest specification and never edits the specification,
conformance sources, expectations, or protected oracle material.
