# percent-decode shipped-Rust baseline

This directory contains only the frozen Rust baseline. It does not contain the
xlang generation harness, protocol, generated source, or benchmark.

## Locked dependency

- crate: `percent-encoding = 2.3.2`
- Cargo requirement: exact `=2.3.2`
- default features: enabled (`std`, which enables `alloc`)
- crates.io checksum:
  `9b4f627cb1b25917193a259e49bdad08f671f8d9708acfd5fe0a8c1455d87220`
- upstream commit anchor:
  [`91377f48bf35011d042aa5abef9e7f2a0a625aaa`](https://github.com/servo/rust-url/tree/91377f48bf35011d042aa5abef9e7f2a0a625aaa/percent_encoding)

The published crate's `.cargo_vcs_info.json` records that commit with
`"dirty": true`. The Git commit is therefore only a source anchor; the
crates.io checksum and committed `Cargo.lock` are authoritative for the exact
published artifact.

## Frozen adapter

The safe helper `decode_into(out, src)` performs only three operations:

1. require caller-owned output capacity of at least `src.len()`;
2. consume the public `percent_encoding::percent_decode(src)` iterator;
3. write each yielded byte sequentially and return the produced length.

It does not reproduce, inspect, or specialize the crate's decoding algorithm.
The timed Rust path and the differential-correctness preflight both call
`decode_into` directly. Only the xlang variants cross the benchmark's C ABI.

Valid `%HH` escapes contract from three bytes to one. Ordinary bytes and
invalid or truncated escapes are preserved according to the upstream iterator.
Bytes after the returned output prefix remain untouched.

## Verification

With the locked crate already present in the Cargo cache:

```sh
cargo test --locked --offline
cargo build --release --locked --offline
```

The tests cover valid upper- and lowercase escapes, binary decoded bytes,
ordinary input, invalid and truncated escapes, pre-write capacity rejection,
suffix preservation, exact-capacity binary output, and empty slices.
