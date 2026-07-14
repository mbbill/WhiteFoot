- Design patterns are a closed, taught catalog (PATTERNS.md): the language forces a curated subset of architectures at program scale, exactly as it forces one loop form and one conditional at statement scale.
- The catalog's acceptance test is two-fold: complete (every task is modelable inside the blessed patterns; a gap is a recorded finding) and efficient (each blessed pattern names the fact channel or machine property behind its speed).
- Patterns are taught up front in the writer material; a writer discovering mid-design that a familiar architecture is unrepresentable is classified as a documentation defect, not a writer error.
- The blessed patterns are the fact-channel feeders: command-buffer writes feed the effect-attribute channel, struct-of-arrays pools feed the scoped-alias channel, declared-law reductions feed the checked-law channel, boolean-dataflow classifiers feed width-16 vectorization.

## Facts

- 2026-07-09 rationale: owner ruling D6 — human languages must accommodate incoming patterns or be rejected by their users; xlang has no installed base to appease (D0a), so it may make radical restrictions provided the completeness and efficiency tests hold; the recorded trigger was the deep-write review, with the ruling that the command-buffer idiom must be doctrine, not folklore. (sourced)
- 2026-07-11 statement: catalog entries are earned from a measurement or a review, never taste — the command-buffer pattern from the no-reborrow deep-write wall, the struct-of-arrays pool validated by the binary-trees port, the branchless i1 classifier from the width-16 result, traps-to-the-boundary from the wc counter case, and the exact-capacity/recoverable-shortage contract from the check-accounting review. (sourced)
- 2026-07-09 statement: the known-gaps section is itself doctrine — gaps are findings recorded next to the patterns (in-place mutation during traversal, shared memo writes during read traversals, borrows stored in data), each with a blessed encoding or a carded relief valve, never silent. (sourced)
- 2026-07-13 rationale: for the data-structure floor, COMPLETE requires representative held-out structures to be implementable by ordinary no-unsafe libraries through public checked mechanisms without asymptotic regression, unavoidable pathological storage, or standard-library-only raw privilege; it does not promise global optimality for every unforeseen structure. (sourced)

## Moves

- 2026-07-09 (fd298d47) replaced [[unconstrained-architecture]]: human languages must let writers carry familiar patterns in or be rejected; xlang's writers are AI under D0a with no installed base to appease, so a closed taught catalog can be forced — provided it stays complete (every task modelable) and efficient (blessed patterns hit the fast paths) (sourced)
