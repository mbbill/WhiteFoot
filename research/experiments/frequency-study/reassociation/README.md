# Reassociation source miner

This is a narrow Stage-1 syntax scanner retained for the one-time Rust
opportunity pilot. It emits JSON Lines for source-spelled saturating-add
recurrences and nearby unresolved/excluded shapes. It is not a semantic Rust
analyzer, and a clean result is not evidence that a project contains no
reduction opportunity.

The strict positive shape is deliberately small: a directly sequenced `for`
loop, a source-spelled primitive unsigned scalar initialized to zero, and an
update of the form `acc = acc.saturating_add(item)` whose result is later used.
Calls, macros, ambiguous folds, nested control, escapes, other writes, signed
saturating addition, and manual multi-lane merges are unresolved or excluded.

For this disposable pilot, humans inspect positive and interesting unresolved
records. There is no planned typed semantic-query stage and this tool must not
turn an absence of strict candidates into a prevalence claim.

Run it with:

```sh
cargo run --quiet --offline --locked \
  --manifest-path experiments/frequency-study/reassociation/Cargo.toml -- \
  /path/to/project
```

Run its checks with:

```sh
cargo test --offline --locked \
  --manifest-path experiments/frequency-study/reassociation/Cargo.toml
```

Each record contains a source location, enclosing function, disposition,
class, required law, and reason. Parse or I/O failures become unresolved
records and make the command fail so incomplete input cannot resemble a clean
scan.
