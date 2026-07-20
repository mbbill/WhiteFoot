# Whitefoot repository foundation gate.
#
# Phase 2 has no active compiler yet. `make check` validates the durable
# specification, governance, reference model, and conformance data. The Rust
# compiler gate is added as the first Phase-2 implementation step; until then a
# compiler or release claim is intentionally unavailable.

PY=python3 -B

check: project-state spec-guard spec reference-model conformance
	@echo "== REPOSITORY FOUNDATION GATE GREEN; NO ACTIVE COMPILER =="

project-state:
	$(PY) tools/test_verify_project_state.py
	$(PY) tools/verify_project_state.py

spec-guard:
	$(PY) tools/spec_guard.py --check
	$(PY) tools/test_spec_guard.py

approve-spec:
	$(PY) tools/spec_guard.py --approve --reason "$(REASON)"

spec:
	$(PY) tools/spec_ci.py

reference-model:
	cd prototype/checker && $(PY) test_checker.py -v
	cd prototype/checker && $(PY) modelcheck.py 10000

conformance:
	$(PY) conformance/runner.py coverage

conformance-run:
	$(PY) conformance/runner.py run

release-check:
	@echo "release gate unavailable: Phase 2 has no active Rust compiler"
	@false

.PHONY: check project-state spec-guard approve-spec spec reference-model conformance conformance-run release-check
