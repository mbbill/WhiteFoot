- `buffer<T>` is a runtime-length heap value that crosses function boundaries as a by-value pointer-plus-length pair; element writes through an exclusive buffer parameter are caller-visible through the shared data pointer.
- v0 buffers hold copy primitives only; aggregate data lays out as parallel per-field buffers (struct-of-arrays), and there is no AoS form yet.
- Result and Option lower to a two-word tag-plus-payload aggregate.
- Const items are immutable program-lifetime rodata lowered to private constant globals; a const-array index is a bounds-checked access into the global and its length is static.
- Growable and keyed collections are not kernel constructs: they are future library structures over `buffer<T>`, and the arena-index-pool pattern with slot recycling is rejected as a collection basis.

## Facts

- 2026-07-10 rationale: owner review — struct-of-arrays is doctrine-blessed and usually the faster layout, but AoS (`buffer` of pod structs) is a genuine need with a named path: a copy-struct tier (a struct of copy fields may be declared copy), carded as smaller than the blocked affine-element cluster. (sourced)
- 2026-07-10 (9d44262b) pitfall: `buffer<Bool>` had never typechecked (the element type was hard-coded to primitives) and sized elements at 4 bytes; fixed structurally and to 1 byte per element in the same audit that finished the i1 lowering. (code)
- 2026-07-08 statement: the greenlit graph-substrate design (unimplemented, gated on a pending storage owner ruling) is a heap-owned single-owner `pool<T>` plus a region-free typed copy `handle<T>`: append-only by default so the well-typed slot-recycling use-after-free is unrepresentable and access is a bare bounds check; generational per-element free is a census-gated opt-in; cross-pool misuse of a same-typed handle is honestly a memory-safe logic bug, outside the safety theorems — the typed handle still beats a bare integer index. (sourced)
- 2026-07-10 statement: slot-recycling rejection has a doctrine consequence — a node is an index into append-only columns and indices never recycle; this is what replaces both pointer-linked heap nodes and free-list arenas (pattern P2). (sourced)
