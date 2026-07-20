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
FORM-2 forbids whitespace before `(`. The descriptor-safe audit covers all 293
protected conformance sources and finds a single space before `(` in 398 of 400
direct function declarations across 291 files. Of the 292 manifested sources,
290 are affected: 276 are runnable, only two expect FORM-2 rejection, and 274
carry another expected result that exact FORM-2 would preempt. Fourteen affected
manifested sources are pending. The remaining affected source is the exact
hash-pinned unmanifested legacy case. The positive FORM-2 fixture itself uses
the forbidden spelling. Those protected files and verdicts cannot be normalized
or changed without the owner's exact approval and governance procedure.

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

## Authored decomposition

`decomposition/*.json` is the authored input to the static catalog. Each file
owns a cohesive specification family. Its clauses tile every exact byte of each
owned rule, while its facets name independent semantic obligations and bind
them to source-index atoms, one pipeline stage, required lanes, and required
evidence classes. The format has no handler, implementation status, witness,
expected verdict, fallback, or editable completion field.

The current reviewed subset contains 34 of 91 rules, 237 exact clauses, 218
facets, and 91 of 200 source atoms. `semantic_catalog.py check-partial` validates
that subset and lists all 57 missing rules. It does not invent their facets or
produce a static catalog. The full `check` command deliberately fails until all
91 rules are authored and every source atom has an exact same-owner trace.

Five exact-byte exclusions are closed in the checker rather than inferred from
marker words: the current deferred portions of FORM-5, FORM-7, and LEX-1; all
of non-normative OWN-9; and only the non-normative prefix of FN-4. Every other
byte must map to a facet.

## Open discrepancies

`facet_discrepancies.py` and its closed predicate registry currently recompute
six non-waivable exact-v0.8 conflicts:

- OP-1's two different dotless operation-name sets;
- FORM-2's spacing rule versus the protected conformance surface;
- FORM-4's `doc` cross-reference versus the indexed production owner;
- FORM-5's required float spelling versus FORM-7's deferral;
- GRAM-1's production/node bijection versus GRAM-7's shared match node; and
- FN-7's `main` return spelling versus the grammar and EX-1.

The eventual sidecar is derived from a complete normalized catalog and exact
authority bytes. It has no status, waiver, or release flag. Release reloads and
recomputes every predicate, and any open record blocks release. During partial
decomposition, the tests use clearly labelled structural-only filler for
missing rules solely to exercise the sidecar contract; those fixtures are not
production catalog data or semantic evidence.

Regenerate the structural index and verify the current facet foundation with:

```sh
python3 -B tools/facet_catalog.py write
python3 -B tools/facet_catalog.py check
python3 -B tools/test_facet_catalog.py
python3 -B tools/test_semantic_catalog.py
python3 -B tools/semantic_catalog.py check-partial
python3 -B tools/test_facet_discrepancies.py
```

The generator accepts only the explicit v0.8 path and exact digest. It never
selects a numerically latest specification and never edits the specification,
conformance sources, expectations, or protected oracle material.
