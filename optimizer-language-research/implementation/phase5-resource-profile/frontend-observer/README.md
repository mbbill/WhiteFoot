# Predecessor frontend topology observer

Status: DEPENDENT DEBUGGING CROSS-CHECK ONLY.

This binary calls the active exact-v0.9 Rust frontend. It rewrites input paths
to deterministic evidence-local logical paths and reports a small set of
predecessor counts. `projected_mixed_elements` is calculated as
`production_nodes - 1 + terminals`; the binary does not observe successor
`MixedElement` storage.

It does not observe ResourceProfile v1, lexical or syntax work, tree depth,
parser-stack high water, list members, expected terminals, tree-byte charges,
resolver roles, or resolution. Its private predecessor limits are safety caps,
not proposed profile values. A cap hit is an observer failure and may never be
used to remove a workload from the demand set.

Because this tool depends on production v0.9 crates, it is neither of the two
independent resource-profile evidence routes. Its current JSON lacks ordered
input-byte identities and is transient debugging output, not an approval
receipt. Any large or hostile run also requires the external process supervisor
defined by the eventual host-class evidence.
