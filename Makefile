# Whitefoot gate. `make check` runs the fast essential correctness checks on the
# current structure; heavy spec-evolution evidence (grammar + v0.10 candidate)
# is opt-in via `make spec-evolution`. A green gate states only what it exercises.
#
# Every check lives next to what it checks: guards in governance/, catalog and
# lexical checks in tests/, compiler policy in compiler/tools/.

PY := python3 -B

# ---- default: fast essential correctness ----
check: project-state spec-guard spec catalogs lexical-model conformance reference-model compiler
	@echo "== WHITEFOOT GATE GREEN (frontend + evidence); semantics and backend absent =="

project-state:
	$(PY) governance/test_project_state.py
	$(PY) governance/project_state.py

spec-guard:
	$(PY) governance/guard.py --check
	$(PY) governance/test_guard.py

approve-spec:
	$(PY) governance/guard.py --approve --reason "$(REASON)"

spec:
	$(PY) governance/test_spec_derivation.py
	$(PY) governance/spec_derivation.py

catalogs:
	$(PY) tests/spec-catalogs/test_facets.py
	$(PY) tests/spec-catalogs/facets.py check
	$(PY) tests/spec-catalogs/test_semantics.py
	$(PY) tests/spec-catalogs/semantics.py check
	$(PY) tests/spec-catalogs/test_discrepancies.py
	$(PY) tests/spec-catalogs/discrepancies.py check
	$(PY) tests/spec-catalogs/test_identity.py
	$(PY) tests/spec-catalogs/identity.py check

lexical-model:
	$(PY) tests/lexical/test_model_v09.py
	$(PY) tests/lexical/test_observer_v09.py

conformance:
	cd tests/conformance && $(PY) test_runner.py
	$(PY) tests/conformance/runner.py coverage

reference-model:
	cd tests/reference && $(PY) test_checker.py -v
	cd tests/reference && $(PY) modelcheck.py 2000

compiler:
	$(MAKE) -C compiler check

# ---- opt-in: heavy spec-evolution evidence ----
spec-evolution: grammar candidate

grammar:
	cmp -s spec/kernel-spec-v0.9.md governance/spec-evolution/grammar/proposal/kernel-spec-successor-candidate.md
	$(MAKE) -C governance/spec-evolution/grammar check

candidate:
	$(PY) governance/spec-evolution/generate_candidate.py --check
	$(PY) governance/spec-evolution/test_generate_candidate.py
	$(PY) governance/spec-evolution/protected_surface_census.py --check
	$(PY) governance/spec-evolution/test_protected_surface_census.py
	$(PY) governance/spec-evolution/diagnostic_evidence/run.py
	$(PY) -m unittest discover -s governance/spec-evolution/diagnostic_evidence -p 'test_*.py'

conformance-run:
	$(PY) tests/conformance/runner.py run

.PHONY: check project-state spec-guard approve-spec spec catalogs lexical-model conformance reference-model compiler spec-evolution grammar candidate conformance-run
