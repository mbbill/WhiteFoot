# xlc

This directory contains the production xlang compiler, written in xlang. Python
`prototype/democ` is stage 0 only: it compiles xlc until xlc can compile itself.

The compiler uses fixed-capacity structure-of-arrays tapes backed by primitive
buffers. Token and node counts are bounded from the source size, so bootstrap does
not require a Rust compiler, growable collections, `pool`, or general generics.
`sources.txt` is the deterministic declaration order for the current whole-program
unit.

Current milestone: `src/model.xl` and `src/lexer.xl` implement the permanent token
model and byte lexer. `src/ast.xl`, `src/parser.xl`, and `src/parser_scalar.xl`
build an exact-span, fail-closed scalar AST slice; every AST node owns a distinct token,
so node capacity is bounded by token count. `src/source_names.xl` compares names
byte-for-byte without hashes, and
`src/output.xl` is the capacity-aware byte sink the LLVM emitter will use. `make check`
compiles all of them with stage 0 and exercises their native C ABI. The lexer oracle
normalizes stage 0's obsolete broad dotted-word token to the current closed-suffix
`OPNAME` rule, so fields are `word . word` while only
`.wrap`, `.trap`, `.checked`, `.sat`, and `.strict` remain atomic operation names.
That distinction is intentional: OP-1 reserves every mode word and dotless operation
name from user binding sites, so `value.trap` is never a legal field place.

`lexer_run`, `parser_run`, and their tape structs are internal compiler/test seams.
The parser trusts the lexer's typed token tags and byte classification, while validating
tape lengths, ordered spans, and the unique source-end token before building any AST.
The eventual public ABI is `xlc_compile(source, output, report)`, which owns this whole
pipeline rather than accepting caller-forged token or AST tapes.

Stage 0 is invoked with optimizer facts disabled for xlc builds until xlc's effect
checking is complete. Parsing now expands grammar slice by slice; semantic checking and
LLVM emission follow. The self-hosting fixpoint uses an in-memory library ABI first, so
runtime I/O, a standalone launcher, and drops do not block it.

Bootstrap target:

```text
democ -> xlc0
xlc0  -> xlc1.ll -> xlc1
xlc1  -> xlc2.ll
xlc1.ll == xlc2.ll
```

`PLAN.md` is an older design record. Its feature inventory and `pool` proposal are not
the current implementation plan.
