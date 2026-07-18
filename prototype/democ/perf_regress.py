#!/usr/bin/env python3
"""Regression pin: the noalias load-elimination win must not silently vanish.
Compiles twice_read with/without ownership facts; asserts 1 vs 2 loads at -O2."""
import subprocess, sys, re
from pathlib import Path
def loads(extra):
    subprocess.run([sys.executable, "democ.py", "examples/twice_read.wf", "--asm"] + extra, check=True, capture_output=True)
    return Path("examples/twice_read.s").read_text().count("ldr")
w = loads([]); wo = loads(["--no-facts"])
print(f"loads with facts={w} without={wo}")
assert w == 1 and wo == 2, "PERF REGRESSION: noalias win changed"
print("OK: ownership-fact load elimination intact")

# Second pin [F003 channel]: scoped-alias metadata from ownership provenance.
# The &uniq-struct-of-buffers kernel must (a) carry !alias.scope facts, and
# (b) vectorize at -O2 with ZERO runtime alias guards; the no-facts control
# must do neither. Guards the un-Rust-able delta measured in
# experiments/scoped-alias-channel/.
def asmtext(extra):
    subprocess.run([sys.executable, "democ.py", "examples/soa_kernel.wf", "--asm"] + extra, check=True, capture_output=True)
    return Path("examples/soa_kernel.ll").read_text(), Path("examples/soa_kernel.s").read_text()
fll, fs = asmtext([]); nll, ns_ = asmtext(["--no-facts"])
assert "!alias.scope" in fll and "!alias.scope" not in nll, "PERF REGRESSION: scoped-alias metadata channel changed"
fvec = fs.count("add.2d") + fs.count(".2d,")
nvec = ns_.count("add.2d") + ns_.count(".2d,")
print(f"soa kernel vector adds with facts={fvec} without={nvec}")
assert fvec > 0 and nvec == 0, "PERF REGRESSION: scoped-alias vectorization changed"
print("OK: scoped-alias (F003) vectorization intact")

# Third pin [FN-4 channel]: checked-law reassociation. The proved-law reduction
# must be rewritten to 4 independent accumulators (>= 8 sat-add sites in the
# facts IR); the control keeps the single serial op. Guards the 3.3x delta
# measured in experiments/checked-law-channel/.
sys.path.insert(0, ".")
import democ as _d
_src = Path("examples/sat_reduce.wf").read_text()
_f = _d.compile_program(_src).count("uadd.sat")
_n = _d.compile_program(_src, alias=False).count("uadd.sat")
print(f"sat-reduce uadd.sat sites with facts={_f} without={_n}")
assert _f >= 8 and _n <= 3, "PERF REGRESSION: checked-law reassociation changed"
print("OK: checked-law (FN-4) reassociation intact")

# Fourth pin: willreturn tier soundness. The give-match counterexamples from
# the adversarial review (a loop hidden in a give-match arm; a call to that fn
# from another give-match arm) must NEVER earn willreturn.
_tp = _d.compile_program(Path("examples/totality_pins.wf").read_text())
assert "willreturn" not in _tp, "SOUNDNESS REGRESSION: willreturn on a divergent give-match fn"
print("OK: willreturn tier soundness pins intact")

# Fifth pin [OP-4 PROOF-1]: requesting structured proof accounting must be a
# byte-transparent observation of compilation, never a codegen switch.
_pr_src = Path("../../codegen-corpus/cases/bounds/dominating-guard/01-basic-read-positive.wf").read_text()
_pr_sites = []
_plain = _d.compile_program(_pr_src)
_reported = _d.compile_program(_pr_src, proof_report=_pr_sites)
assert _plain == _reported, "CODEGEN REGRESSION: proof accounting changed emitted IR"
assert len(_pr_sites) == 1 and _pr_sites[0]["status"] == "proved", \
    "PROOF REGRESSION: structured site accounting changed"
print("OK: bounds-proof accounting is byte-transparent")

# Sixth pin [OP-4 PROOF-2]: obligation discovery is body-derived and remains
# identical in the facts-off control; only the old proof marker/codegen state
# may differ.  Reporting itself must remain byte-transparent in both modes.
_p2_src = Path("../../codegen-corpus/cases/bounds/output-capacity-lockstep/p05-complete-groups.wf").read_text()
_p2_facts, _p2_nofacts = [], []
_p2_plain_facts = _d.compile_program(_p2_src, alias=True)
_p2_reported_facts = _d.compile_program(_p2_src, alias=True, proof_report=_p2_facts)
_p2_plain_nofacts = _d.compile_program(_p2_src, alias=False)
_p2_reported_nofacts = _d.compile_program(
    _p2_src, alias=False, proof_report=_p2_nofacts)
assert _p2_plain_facts == _p2_reported_facts \
    and _p2_plain_nofacts == _p2_reported_nofacts, \
    "CODEGEN REGRESSION: PROOF-2 obligation reporting changed emitted IR"
_diag_fields = (
    "obligation", "obligation_status", "obligation_exactness",
    "requirement_relation", "first_missing_fact", "first_failed_premise",
)
_p2_fdiag = [{k: site[k] for k in _diag_fields} for site in _p2_facts]
_p2_ndiag = [{k: site[k] for k in _diag_fields} for site in _p2_nofacts]
assert len(_p2_facts) == 12 and _p2_fdiag == _p2_ndiag, \
    "PROOF REGRESSION: PROOF-2 facts/no-facts diagnostics diverged"
assert all(site["status"] == "proved" and site["obligation_exactness"] == "exact"
           and site["requirement_relation"] == "equivalent" for site in _p2_facts), \
    "PROOF REGRESSION: exact PROOF-2 sites changed"
assert all(site["status"] == "retained" for site in _p2_nofacts), \
    "PROOF REGRESSION: facts-off PROOF-2 sites were elided"
print("OK: PROOF-2 obligations are byte-transparent and facts-independent")
