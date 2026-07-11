# Codegen-parity gate

This gate answers a narrower question than a benchmark: did a compiler change
silently lose a code-generation property that the project has already earned?
It recompiles every input in a temporary directory and checks optimized LLVM
IR, loop-vectorizer remarks, and per-function machine opcode sequences.

Run it with:

```sh
make parity
python3 tools/codegen_parity.py --gate-only
python3 tools/codegen_parity.py --audit-only
python3 tools/codegen_parity.py --case scalar-backend-parity
python3 tools/codegen_parity.py --json
```

The cases live in `codegen-parity.json`. A `gate` case makes the command fail;
an `audit` case reports `DEBT` but exits successfully. Promotion from audit to
gate happens only after the target property is implemented, independently
verified, and expected to remain true. This keeps known debt visible without
encoding today's bad codegen as tomorrow's contract.

The initial coverage is deliberately small and high-signal:

- exact backend opcode parity for one xlang/C/safe-Rust scalar kernel;
- the facts-on/off load-elimination, scoped-alias, and checked-law channels;
- vector-width and trap parity on the real wc chunk classifier;
- the base64 perfect-prover ceiling as non-blocking bounds-elision debt.

This is not a runtime-performance gate. Runtime measurements remain in their
self-contained experiment directories because frequency scaling, corpus state,
and scheduler noise make them unsuitable for an every-change invariant. Add a
runtime gate later only for a stable, dedicated benchmark host.

## Manifest vocabulary

Each variant names a `kind` (`xlang`, `c`, or `rust`), source, optimization
level, and optional function. xlang variants may disable the fact bundle with
`"facts": false`; `"elide_bounds": true` is reserved for the explicitly
labelled ceiling audit. Checks compare `variant.metric` to a literal or another
variant. Supported operators are `eq`, `ne`, `lt`, `le`, `gt`, and `ge`.

The runner currently exposes:

- `raw_ir.alias_scope_uses`, `raw_ir.noalias_uses`,
  `raw_ir.saturating_add_mentions`, `raw_ir.trap_calls`;
- `opt_ir.loads`, `opt_ir.vector_loads`, `opt_ir.trap_calls`;
- `asm.instructions`, `asm.opcodes`, `asm.traps`;
- `remarks.vectorized_loops`, `remarks.max_vector_width`, and
  `remarks.max_interleave`.

Exact opcode parity is intentionally sensitive to a toolchain upgrade. If a
new backend makes all three variants better but different, inspect the diff and
update the gate in the same change; do not weaken it merely to restore green.
