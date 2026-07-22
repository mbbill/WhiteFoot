# Ownership reference-model resources

This directory supplies independent semantic evidence used by the complete
language-change workflow in `governance/README.md`. It models only the
ownership/effect subset described in `checker.py`, using a toy AST so compiler
and model bugs are less likely to share an implementation.

The model does not define the language, parse Whitefoot source, or claim full
v0.11 coverage. When the model, compiler, and active numbered specification
disagree, the specification is authoritative and the discrepancy is classified
through the central workflow.

## Resources

- `checker.py` implements the focused ownership/effect judgments.
- `oracle.py` provides the independent comparison surface.
- `test_checker.py` holds examples, regressions, and mutation checks.
- `modelcheck.py` explores bounded generated states.

The resource should remain narrow. Do not copy compiler data structures into
it or grow it into a second compiler. A replacement may retire this Python
implementation only if it preserves every still-relevant judgment, regression,
bounded-state check, mutation check, and unique counterexample.

Changing or removing an existing reference judgment is protected work governed
by `governance/README.md`. Add a new model judgment only when its independence
can catch a distinct class of semantic error.

## Tools

From the repository root:

```sh
make reference
```
