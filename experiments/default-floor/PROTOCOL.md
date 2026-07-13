# Default-floor generation protocol

This directory defines a target-independent, benchmark-blind way to obtain and
freeze one default model output. It is deliberately narrower than an agentic
coding loop: one model command, one sequential trajectory, a fixed repair
budget, and machine evaluator feedback only.

## Frozen inputs

Before a run, the operator fixes:

- the complete base prompt;
- model argv as a non-empty JSON array of strings;
- evaluator argv as a non-empty JSON array of strings;
- optional explicitly public model/evaluator metadata objects;
- the non-negative repair budget (additional attempts after round zero);
- the source artifact name and both process timeouts.

The run directory is the pre-registered trajectory identity and must not exist.
`generate.py` creates it atomically and never resumes or overwrites it. Starting
again under another path is a new experiment, not another trajectory of the
same experiment; treating it as the same result violates this protocol.

Raw argv can contain credentials or private wrapper arguments, so it is never
written to the run. `config.json` records canonical argv SHA-256, item count,
and only the operator-supplied public metadata. Anyone reproducing the run can
verify the argv hash without publishing secrets. Credentials must not be placed
in the public metadata object.

Exactly one trajectory is permitted. Round zero receives the base prompt plus
the source-only output contract, without stripping or normalizing the base
prompt bytes. A failed round may produce exactly one next
round, which receives the same base prompt, the immediately preceding source,
and the immediately preceding accepted evaluator JSON. There is no branching,
candidate ranking, sampling pool, human repair, or restart inside a run.

## Model boundary

The model command is executed with `subprocess.run(argv, shell=False)`. The
prompt is supplied on stdin. Stdout is the candidate source byte-for-byte; no
code-fence extraction or answer rewriting occurs. Stderr is archived but never
fed to the evaluator or a repair round.

Every model invocation runs in a newly created, empty temporary working
directory. Path-like argv entries therefore need to be absolute. The directory
is destroyed after the invocation.

Codex CLI does not use its ordinary stdout as a source-only contract. The
included `codex_model_adapter.py` invokes `codex exec --json`, accepts exactly
one event sequence—`thread.started`, `turn.started`, one completed
`agent_message`, then `turn.completed`—and rejects reordered, repeated,
post-completion, tool, non-message, or unexpected events. The complete CLI JSONL and native stderr are archived as
model stderr; only the single message text reaches model stdout. The invocation
is ephemeral, read-only, explicitly fixes its model, reasoning, and service
tier, and ignores user config/rules. A read-only tool attempt
therefore invalidates the run instead of producing a candidate influenced by
workspace inspection.

## Evaluator boundary

The evaluator command is also executed with `shell=False`. The absolute
candidate path is appended to its fixed argv and is always the final argument.
The evaluator receives no stdin and must emit one UTF-8 JSON object on stdout.

Only these top-level machine-feedback channels are accepted:

```json
{
  "compile": {"passed": true, "diagnostics": []},
  "correctness": {"passed": true, "diagnostics": []},
  "proof": {"status": "reported", "sites": []}
}
```

`compile` and `correctness` are required closed objects with boolean `passed`
and optional structured `diagnostics`. A diagnostic requires string `code` and
`message`; it may carry `path`, `line`, `column`, `end_line`, and `end_column`.
`proof` is an optional closed object containing only `passed`, `status`,
structured `diagnostics`, and structured `sites`; a site requires `id` and
`status` and may carry `detail`, `rule`, `path`, `line`, and `column`. Unknown
fields at any of these levels are rejected.

Benchmark/performance-related field names and string contents are rejected
recursively, including timing units, latency, throughput, cycle, duration,
speed, and bandwidth terms. A metrics object such as `wall_ns`, or a diagnostic
message containing a latency result, is therefore a protocol failure and can
never enter a repair prompt.

Evaluator exit failure, invalid JSON, an invalid schema, or forbidden feedback
is a protocol failure, not a candidate failure. It does not consume a repair
decision. Every actual model invocation, including a model/evaluator protocol
failure, receives a `record.json` and one `trace.jsonl` entry. Rejected evaluator
bytes remain only in the hash-addressed raw artifact and are never copied into
accepted evaluator JSON or a repair prompt.

## Trace and freeze rule

Each completed round archives:

- `prompt.txt`: exact prompt bytes supplied to the model;
- `model.raw.txt`: exact model stdout;
- the named source file: exact evaluator candidate bytes;
- `evaluator.json`: validated, canonical machine feedback;
- process stderr/return-code records and a hash-bearing `record.json`.

The same round record is appended to `trace.jsonl`. Artifact hashes are SHA-256.

The first round for which both `compile.passed` and
`correctness.passed` are true is frozen immediately. Proof status does not delay
the correctness freeze. No further model call is permitted. `frozen/` contains:

- the byte-identical source;
- `source.sha256`;
- `trace-manifest.json`, binding the frozen round, source, trace, and config
  hashes, plus all completed round records.

If every allowed round fails correctness, no `frozen/` directory is created and
the result records repair-budget exhaustion.

This protocol creates the candidate only. Benchmarking, comparison against a
shipped implementation, and any later performance work must consume the frozen
hash without reopening generation.
