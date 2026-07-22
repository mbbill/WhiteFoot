# Bounds-elision ceiling snapshots

This directory records an intermediate question: if every implicit bounds check
inside the two kernels disappeared, would the existing scalar strategy become
competitive?

The answer was no.

At match length 258, selected medians were:

| Distance | Bounds-elided WF GiB/s | zlib-ng GiB/s |
|---:|---:|---:|
| 1 | 2.325 | 31.663 |
| 2 | 0.893 | 29.686 |
| 8 | 3.250 | 27.407 |

The Huffman ceiling reached 383.257 million symbols/s versus 415.582 for
zlib-ng, or 0.922x.

`*-baseline.llvm.txt` preserves the ordinary facts-on LLVM. The
`*-bounds-elided.llvm.txt` files preserve the experimental all-bounds-proved
ceiling. The JSON files contain the raw measurements.

No generator script survived with this temporary directory. These files are
therefore evidence snapshots, not a fully self-contained reproduction. Their
purpose is diagnostic: contracts and check removal alone do not synthesize
period materialization or multi-symbol word decoding.
