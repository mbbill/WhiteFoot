# Archived stage-0 compiler prototypes

These are two independent feasibility patches against historical base commit
`40dd2445d54d4714ad2cf8fe22aad741186db5c7`. They are deliberately stored under
the experiment instead of being applied to `prototype/democ` or production
`wfc`.

- `periodic/democ.patch` corresponds to temporary commit
  `ee7a02b71a681b382c6c147fd9fd57ee5e4f5659`.
- `guarded-bit-window/democ.patch` corresponds to temporary commit
  `f3c3e042dde8dc400456943ec658187b2f9f6b3d`.

The commits were developed separately. Their patches are not a combined
compiler design and should not be applied to current `main`.

Each directory contains baseline and optimized LLVM snapshots. The periodic
directory also preserves the focused stage-0 test that originally lived beside
`democ.py`. The guarded focused test remains at
`../../test_guarded_bit_window.py` because its runner imports it from the
experiment.

To replay a prototype, use a disposable worktree at the recorded historical
base, apply only one patch, place its focused tests at their recorded paths, and
run the corresponding top-level experiment runner. Do not use the patch as a
production implementation plan: both paths bypass the required body-derived
obligation and proof-report architecture.

The patches remain valuable because they preserve the exact answer to two
feasibility questions:

1. Can checked AST structure select periodic expansion without changing the WF
   source? Yes, using an exact recognizer and external target helper.
2. Can a closed checked Huffman shape select a guarded word window without
   changing the WF source? Yes, using a digest/table certificate and direct LLVM
   emitter.

The limitations and required production replacement are detailed in
`../DESIGN-HANDOFF.md`.
