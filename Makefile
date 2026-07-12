# xlang verification stack — `make check` runs every layer.
PY=python3 -B
check: spec rules soundness perf parity conformance bootstrap
	@echo "== ALL VERIFICATION LAYERS GREEN =="
spec:                      # layer 1: spec integrity (META rules, ledger coverage)
	$(PY) tools/spec_ci.py
rules:                     # layer 2: rule-keyed checker + stage-0 codegen correctness
	cd prototype/checker && $(PY) test_checker.py -v 2>&1 | tail -2
	cd prototype/democ && $(PY) test_codegen.py
soundness:                 # layer 3: generative model check vs independent oracle
	cd prototype/checker && $(PY) modelcheck.py 10000
perf:                      # layer 4: pinned optimizer-fact effects
	cd prototype/democ && $(PY) perf_regress.py
	$(PY) experiments/port-study/base64/verify.py
parity:                    # layer 5: xlang/facts-off/C/Rust codegen properties + visible debt
	$(PY) tools/test_checked_automation.py
	$(PY) tools/codegen_parity.py --corpus --promotion
corpus:                    # focused proof/codegen corpus; positive + adversarial gates
	$(PY) tools/test_checked_automation.py
	$(PY) tools/codegen_parity.py --corpus --tag bounds
conformance:               # layer 6: spec-anchored rule-keyed conformance suite (source -> verdict)
	$(PY) conformance/runner.py all
bootstrap:                 # layer 7: permanent xlc components compiled by disposable stage 0
	$(MAKE) -C compiler check
examples:                  # smoke: compile & run the demo programs
	cd prototype/democ && $(PY) democ.py examples/ex1.xl --run && $(PY) democ.py examples/ex2.xl --run
.PHONY: check spec rules soundness perf parity corpus conformance bootstrap examples
