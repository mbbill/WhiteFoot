# Raw DEFLATE default-shape experiment

This directory contains an exploratory test of whether the current Whitefoot
writer surface naturally produces competitive code for a real compression
scenario. It is preregistered only when `PROTOCOL.md` says so.

The unit under test is a complete one-shot raw RFC 1951 decoder. It is not a
zlib port: wrappers, checksums, dictionaries, streaming continuation, I/O, and
the zlib ABI are excluded. The frozen Whitefoot candidate is compared with the
ordinary public raw-inflate path of a pinned zlib-ng release.

`PROTOCOL.md` is authoritative. No candidate generation or timing is valid
while that file says `DRAFT` or contains an unresolved placeholder.

The experiment is independent of the completed D9 default-floor series. It
does not add a third result to that series or alter either frozen campaign.

No correctness-green candidate or score was produced before the investigation
was redirected to two core inflate kernels. The resulting measurements,
compiler feasibility prototypes, proof analysis, and deferred pickup plan are
preserved in `../zlib-core-kernels/`. This draft harness remains historical
infrastructure and does not supersede that result.
