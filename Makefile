# Whitefoot gate — only what a research compiler needs: the compiler builds and
# passes its tests, the behavior corpus and reference model agree, and the
# numbered spec stays append-only. Everything else is guarded by the guidance in
# AGENTS.md/CLAUDE.md, not by machinery. A green gate states only what it exercises.

PY := python3 -B

check: project-state spec-append-only conformance reference compiler
	@echo "== WHITEFOOT GATE GREEN (frontend + evidence); semantics and backend absent =="

# repository invariants: AGENTS.md == CLAUDE.md, single roadmap
project-state:
	$(PY) governance/test_project_state.py
	$(PY) governance/project_state.py

# the one spec protection: released kernel specs are never edited (new version only)
spec-append-only:
	$(PY) governance/spec_append_only.py

conformance:
	cd tests/conformance && $(PY) test_runner.py
	$(PY) tests/conformance/runner.py coverage

reference:
	cd tests/reference && $(PY) test_checker.py -v
	cd tests/reference && $(PY) modelcheck.py 2000

compiler:
	$(MAKE) -C compiler check

conformance-run:
	$(PY) tests/conformance/runner.py run

# one-time: point git at the tracked hooks (spec append-only pre-commit)
install-hooks:
	git config core.hooksPath governance/hooks
	@echo "installed governance/hooks (spec append-only pre-commit)"

.PHONY: check project-state spec-append-only conformance reference compiler conformance-run install-hooks
