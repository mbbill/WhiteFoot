# Codegen corpus format

The corpus is organized into compact `cases.json` family manifests discovered
recursively under `cases/`. Each family states one optimization hypothesis and
a named-function metric; its nearby `.xl` sources vary one premise at a time.
Adding a family never requires editing one central manifest.

Every positive proof case has near-identical negative controls. The facts-on
and facts-off variants are synthesized by the runner, so generated manifests
cannot accidentally compare different source programs. Proof classification
uses raw IR from the named function: optimized assembly is recorded separately
because LLVM may independently remove the same check.

```text
codegen-corpus/
  schema.json
  cases/
    bounds/
      dominating-guard/
        cases.json
        01-basic-read-positive.xl
        05-wrong-buffer-negative.xl
      masked-index/
        cases.json
        p01-mask3-table4.xl
        n02-oversized-mask.xl
```

Run all families or select a tag:

```sh
make corpus
python3 tools/codegen_parity.py --corpus --tag proof-1
```

## Field policy

- Family `tags` are inherited by every contained case. Case tags add the
  polarity, mutation shape, or specific premise under test.
- `maturity` is `explore`, `audit`, or `gate`. Explore cases collect evidence;
  audit cases describe a known target without blocking; gate cases are earned
  invariants and may fail verification.
- `hypothesis` must name the causal property being tested, not merely say that
  one variant should be faster.
- `proof_classification` is `proved`/`elided` for positive cases and
  `retained`/`checked` for near-misses. Silently proving a near-miss is a
  blocking soundness failure.

Paths in `source` are relative to the fragment containing them and must remain
inside the repository. Source and recipes are tracked; generated IR, assembly,
objects, binaries, and expanded metamorphic cases are temporary artifacts.

Promotion is deliberate: an `explore` case becomes `audit` once its target is
understood, and becomes `gate` only after the property is implemented, verified
against adversarial near-misses, and stable on the supported toolchain.
