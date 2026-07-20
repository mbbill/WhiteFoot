#!/usr/bin/env python3
"""Spec & test governance guard.

The kernel specification and the semantics-bearing test surface are OWNER-GATED.
An agent must obtain the owner's explicit approval for any change to a guarded
surface, record that approval in `governance/APPROVALS.md`, and only then commit.
Approval of a plan or phase is never approval to change the spec.

This guard makes an un-approved guarded change impossible to land silently: it
recomputes the guarded surface, compares it against the approved baseline
(`governance/guard-baseline.json`), and fails `make check` when

  * a numbered kernel spec is added, removed, or edited in place;
  * an existing conformance expected verdict or any case file changes;
  * a frozen oracle digest is changed or regenerated;
  * an existing guarded reference test is removed or rewritten; or
  * the baseline itself was regenerated without a matching logged approval.

Adding new tests or new conformance cases is always allowed. The residual trust
is the honesty of the ask: the owner approves in the session and the approval is
written into the append-only ledger, which the owner audits.

Usage:
  spec_guard.py --check                     verify the working tree (default; `make check`)
  spec_guard.py --regenerate                rewrite the baseline from the working tree
  spec_guard.py --approve --reason "<why>"  regenerate the baseline AND append a ledger entry
"""

from __future__ import annotations

import argparse
import ast
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "governance" / "guard-baseline.json"
APPROVALS = ROOT / "governance" / "APPROVALS.md"

# --- guarded surface configuration -----------------------------------------

KERNEL_SPEC_GLOB = "kernel-spec-v*.md"          # under spec/; fully pinned (exact set)
CONFORMANCE_MANIFEST = ROOT / "conformance" / "manifest.jsonl"
CONFORMANCE_CASES = ROOT / "conformance" / "cases"
ORACLE_FILES = (                                 # frozen digest literals live here
    "tools/codegen_parity.py",
    "tools/test_checked_automation.py",
)
GUARDED_TEST_FILES = (                            # active reference semantics; per-function pin
    "prototype/checker/test_checker.py",
)

HEX_DIGEST = re.compile(r'"([0-9a-f]{64}|[0-9a-f]{40})"')
APPROVAL_BASELINE_LINE = re.compile(r"^- baseline:\s*([0-9a-f]{64})\s*$", re.M)

# The current approved baseline predates the explicit all-files case inventory.
# It already pins every manifested case through ``conformance``, but it omitted
# this one tracked, unmanifested case. Bind the migration to the exact approved
# baseline bytes so it cannot silently apply to a different baseline. The next
# owner-approved regeneration will write ``conformance_case_files`` directly
# and no longer use this compatibility entry.
LEGACY_CASE_FILE_INVENTORIES = {
    "9d4ff925668a3341543d555c5243ef0b74ca5e7e275617ff4808d90c290dc48a": {
        "conformance/cases/pending-const2-item.wf":
            "ae99d9b9b99e02e9c6c5f2af54f0924b7b1a0f5ee0422d29958b01b597adf759",
    },
}

FIX_HINT = (
    "obtain the owner's approval for the exact delta, then record it with "
    "`make approve-spec REASON=\"...\"` (see governance/APPROVALS.md)"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --- surface computation ----------------------------------------------------

def spec_surface() -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted((ROOT / "spec").glob(KERNEL_SPEC_GLOB)):
        rel = str(path.relative_to(ROOT))
        out[rel] = sha256_bytes(path.read_bytes())
    return out


def conformance_surface() -> dict[str, str]:
    out: dict[str, str] = {}
    if not CONFORMANCE_MANIFEST.is_file():
        return out
    for line in CONFORMANCE_MANIFEST.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        obj = json.loads(stripped)
        if "id" in obj:
            key = obj["id"]
            canon = json.dumps(
                {field: obj.get(field) for field in ("id", "rules", "expect", "status")},
                sort_keys=True,
                separators=(",", ":"),
            )
            case_file = CONFORMANCE_CASES / f"{obj['id']}.wf"
            case_bytes = case_file.read_bytes() if case_file.is_file() else b""
            out[key] = sha256_bytes(canon.encode("utf-8") + b"\0" + case_bytes)
        else:
            # coverage annotation (keyed by rule) or any other manifest line
            canon = json.dumps(obj, sort_keys=True, separators=(",", ":"))
            key = f"rule:{obj['rule']}" if "rule" in obj else "line:" + sha256_bytes(
                stripped.encode("utf-8")
            )[:16]
            out[key] = sha256_bytes(canon.encode("utf-8"))
    return out


def conformance_case_files_surface() -> dict[str, str]:
    """Hash every regular file below the protected conformance case tree."""
    out: dict[str, str] = {}
    if not CONFORMANCE_CASES.is_dir():
        return out
    for path in sorted(CONFORMANCE_CASES.rglob("*")):
        if path.is_file():
            rel = path.relative_to(ROOT).as_posix()
            out[rel] = sha256_bytes(path.read_bytes())
    return out


def oracle_surface() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for rel in ORACLE_FILES:
        path = ROOT / rel
        if not path.is_file():
            out[rel] = []
            continue
        text = path.read_text(encoding="utf-8")
        out[rel] = sorted(set(HEX_DIGEST.findall(text)))
    return out


def _test_functions(source: str) -> dict[str, str]:
    tree = ast.parse(source)
    out: dict[str, str] = {}

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qualname = prefix + child.name
                segment = ast.get_source_segment(source, child) or ""
                out[qualname] = sha256_bytes(segment.encode("utf-8"))
                walk(child, qualname + ".")
            elif isinstance(child, ast.ClassDef):
                walk(child, prefix + child.name + ".")
            else:
                walk(child, prefix)

    walk(tree, "")
    return out


def tests_surface() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for rel in GUARDED_TEST_FILES:
        path = ROOT / rel
        out[rel] = _test_functions(path.read_text(encoding="utf-8")) if path.is_file() else {}
    return out


def build_surface() -> dict:
    return {
        "kernel_specs": spec_surface(),
        "conformance": conformance_surface(),
        "conformance_case_files": conformance_case_files_surface(),
        "oracles": oracle_surface(),
        "tests": tests_surface(),
    }


# --- comparison (pure; unit-tested) -----------------------------------------

def diff_surface(baseline: dict, live: dict) -> list[str]:
    """Return human-readable violations. Empty list means the tree is compliant."""
    violations: list[str] = []

    base_specs = baseline.get("kernel_specs", {})
    live_specs = live.get("kernel_specs", {})
    for path, digest in base_specs.items():
        if path not in live_specs:
            violations.append(f"kernel spec removed without approval: {path}")
        elif live_specs[path] != digest:
            violations.append(
                f"numbered kernel spec edited in place (bump version + rename instead): {path}"
            )
    for path in live_specs:
        if path not in base_specs:
            violations.append(f"new numbered kernel spec added without approval: {path}")

    base_conf = baseline.get("conformance", {})
    live_conf = live.get("conformance", {})
    for case_id, digest in base_conf.items():
        if case_id not in live_conf:
            violations.append(f"conformance case removed without approval: {case_id}")
        elif live_conf[case_id] != digest:
            violations.append(
                f"conformance expected verdict or case source changed without approval: {case_id}"
            )

    base_case_files = baseline.get("conformance_case_files", {})
    live_case_files = live.get("conformance_case_files", {})
    for path, digest in base_case_files.items():
        if path not in live_case_files:
            violations.append(f"conformance case file removed without approval: {path}")
        elif live_case_files[path] != digest:
            violations.append(f"conformance case file changed without approval: {path}")

    base_oracle = baseline.get("oracles", {})
    live_oracle = live.get("oracles", {})
    for rel, values in base_oracle.items():
        present = set(live_oracle.get(rel, []))
        for value in values:
            if value not in present:
                violations.append(
                    f"frozen oracle digest changed or removed in {rel}: {value[:16]}..."
                )

    base_tests = baseline.get("tests", {})
    live_tests = live.get("tests", {})
    for rel, funcs in base_tests.items():
        live_funcs = live_tests.get(rel, {})
        for qualname, digest in funcs.items():
            if qualname not in live_funcs:
                violations.append(f"guarded test removed without approval: {rel}::{qualname}")
            elif live_funcs[qualname] != digest:
                violations.append(f"guarded test rewritten without approval: {rel}::{qualname}")

    return violations


# --- modes ------------------------------------------------------------------

def load_baseline() -> dict | None:
    if not BASELINE.is_file():
        return None
    raw = BASELINE.read_bytes()
    baseline = json.loads(raw.decode("utf-8"))
    if "conformance_case_files" not in baseline:
        digest = sha256_bytes(raw)
        legacy_inventory = LEGACY_CASE_FILE_INVENTORIES.get(digest)
        if legacy_inventory is None:
            raise ValueError(
                "approved baseline predates the all-files conformance inventory "
                "and has no exact migration pin"
            )
        baseline["conformance_case_files"] = dict(legacy_inventory)
    return baseline


def write_baseline(surface: dict) -> str:
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE.write_text(
        json.dumps(surface, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return sha256_bytes(BASELINE.read_bytes())


def latest_logged_baseline() -> str | None:
    if not APPROVALS.is_file():
        return None
    found = APPROVAL_BASELINE_LINE.findall(APPROVALS.read_text(encoding="utf-8"))
    return found[-1] if found else None


def cmd_check() -> int:
    try:
        baseline = load_baseline()
    except ValueError as error:
        print(f"spec-guard: invalid governance baseline: {error}", file=sys.stderr)
        return 1
    if baseline is None:
        print(
            "spec-guard: missing governance/guard-baseline.json; "
            "seed it with `make approve-spec REASON=...`",
            file=sys.stderr,
        )
        return 1

    violations = diff_surface(baseline, build_surface())

    logged = latest_logged_baseline()
    actual = sha256_bytes(BASELINE.read_bytes())
    if logged is None:
        violations.append(
            "governance/APPROVALS.md has no logged baseline; every guarded change "
            "needs a recorded owner approval"
        )
    elif logged != actual:
        violations.append(
            "governance/guard-baseline.json does not match the latest logged approval "
            "in governance/APPROVALS.md (baseline regenerated without a recorded approval)"
        )

    if violations:
        print("spec-guard: OWNER-GATED surface changed without approval:", file=sys.stderr)
        for violation in violations:
            print(f"  - {violation}", file=sys.stderr)
        print(f"  fix: {FIX_HINT}", file=sys.stderr)
        return 1

    print(
        "spec-guard: kernel spec, conformance verdicts and case files, oracle digests, "
        "and reference tests match the approved baseline"
    )
    return 0


def cmd_regenerate() -> int:
    digest = write_baseline(build_surface())
    print(f"spec-guard: baseline regenerated; sha256={digest}")
    print("append a `- baseline: <sha256>` line to governance/APPROVALS.md to authorize it")
    return 0


def cmd_approve(reason: str) -> int:
    if not reason or not reason.strip():
        print("spec-guard: --approve requires a non-empty --reason", file=sys.stderr)
        return 2
    digest = write_baseline(build_surface())
    today = datetime.date.today().isoformat()
    if not APPROVALS.is_file():
        print("spec-guard: missing governance/APPROVALS.md", file=sys.stderr)
        return 1
    entry = (
        f"\n## {today} — approval\n"
        f"- owner: approved in session\n"
        f"- reason: {reason.strip()}\n"
        f"- baseline: {digest}\n"
    )
    with APPROVALS.open("a", encoding="utf-8") as handle:
        handle.write(entry)
    print(f"spec-guard: baseline regenerated and approval logged; sha256={digest}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Spec & test governance guard.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="verify the working tree (default)")
    group.add_argument("--regenerate", action="store_true", help="rewrite the baseline")
    group.add_argument("--approve", action="store_true", help="regenerate and log an approval")
    parser.add_argument("--reason", default="", help="approval reason (with --approve)")
    args = parser.parse_args()

    if args.regenerate:
        return cmd_regenerate()
    if args.approve:
        return cmd_approve(args.reason)
    return cmd_check()


if __name__ == "__main__":
    raise SystemExit(main())
