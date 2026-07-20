# Manual strategy ceiling

Before modifying a compiler, this probe tested whether better machine strategies
were attainable for the exact isolated APIs.

- `periodic_candidate.c` materializes or copies the proven period using ARM
  NEON strategies and a scalar fallback.
- `huffman_candidate.c` decodes a guarded fixed batch from a wide bit window.
- The two JSON files preserve the raw candidate measurements.
- `harness.patch` records the dirty temporary harness delta against historical
  experiment base `40dd2445d54d4714ad2cf8fe22aad741186db5c7`.

The Huffman candidate measured 443.990 million symbols/s versus 414.786 for the
pinned zlib-ng projection. The periodic candidate removed the short-distance
collapse; at already vectorizable distances the harness selected ordinary WF
when it was slightly faster.

This probe answered only “does a competitive strategy exist?” It did not answer
whether a compiler could prove the strategy legal. The later stage-0 prototypes
answer that second question over closed shapes, and their corrected results are
the authoritative compiler-triggered evidence.

These C candidates are not trusted runtime code, standard-library proposals, or
production lowerings.
