#!/usr/bin/env python3
"""Deterministic code-generation parity gate for xlang.

The runner compiles every variant in a temporary directory, extracts stable
IR/assembly properties, and evaluates the relations in codegen-parity.json.
Cases marked "audit" are reported but never make the command fail.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import operator
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True  # keep parity runs from polluting the workspace with caches
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "codegen-parity.json"
CORPUS_ROOT = ROOT / "codegen-corpus/cases"
CLANG = Path("/usr/bin/clang") if Path("/usr/bin/clang").exists() else Path("clang")
VECTOR_REMARK = re.compile(
    r"vectorized loop \(vectorization width: (\d+), interleaved count: (\d+)\)"
)
OPS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "lt": operator.lt,
    "le": operator.le,
    "gt": operator.gt,
    "ge": operator.ge,
}


class HarnessError(RuntimeError):
    pass


def load_democ():
    path = ROOT / "prototype/democ/democ.py"
    spec = importlib.util.spec_from_file_location("xlang_democ", path)
    if spec is None or spec.loader is None:
        raise HarnessError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        rendered = " ".join(command)
        detail = result.stderr.strip() or result.stdout.strip()
        raise HarnessError(f"command failed ({rendered}):\n{detail}")
    return result


def llvm_function(text: str, function: str | None) -> str:
    if not function:
        return text
    start = re.compile(rf'^define\b.*@"?{re.escape(function)}"?\(', re.MULTILINE).search(text)
    if not start:
        raise HarnessError(f"LLVM function @{function} not found")
    pos = start.start()
    end = text.find("\n}", pos)
    if end < 0:
        raise HarnessError(f"unterminated LLVM function @{function}")
    return text[pos : end + 2]


def assembly_function(text: str, function: str | None) -> str:
    if not function:
        return text
    label = re.compile(rf"^_?{re.escape(function)}:\s*(?:[#;/].*)?$", re.MULTILINE)
    match = label.search(text)
    if not match:
        raise HarnessError(f"assembly function {function} not found")
    lines = text[match.start() :].splitlines()
    out = []
    for index, line in enumerate(lines):
        if index and re.match(r"\s*\.globl\s+", line):
            break
        out.append(line)
        if index and re.match(r"\s*\.size\s+_?" + re.escape(function) + r"\b", line):
            break
        if index and line.strip() == ".cfi_endproc":
            break
    return "\n".join(out)


def assembly_opcodes(body: str) -> list[str]:
    opcodes: list[str] = []
    for raw in body.splitlines():
        line = raw.split(";", 1)[0].split("//", 1)[0].strip()
        if not line or line.startswith((".", "#")) or line.endswith(":"):
            continue
        token = line.split(None, 1)[0]
        if re.match(r"^[A-Za-z][A-Za-z0-9_.]*$", token):
            opcodes.append(token.lower())
    return opcodes


def metrics(raw_ir: str, optimized_ir: str, assembly: str, remarks: str,
            function: str | None, proof_report: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    raw_body = llvm_function(raw_ir, function)
    opt_body = llvm_function(optimized_ir, function)
    asm_body = assembly_function(assembly, function)
    opcodes = assembly_opcodes(asm_body)
    vectors = [(int(width), int(interleave)) for width, interleave in VECTOR_REMARK.findall(remarks)]
    ir_vector_widths = [int(width) for width in re.findall(r"<(\d+)\s+x\s+[^>]+>", opt_body)]
    bounds = None if proof_report is None else [
        site for site in proof_report if function is None or site["function"] == function
    ]
    if bounds is None:
        proof_metrics = {
            "proof.bounds_sites": None,
            "proof.eligible": None,
            "proof.proved": None,
            "proof.retained": None,
            "proof.ceiling": None,
            "proof.partition_ok": None,
            "proof.dominating_guard": None,
            "proof.masked_index": None,
            "proof.remainder_guard": None,
            "proof.remainder_tail": None,
            "proof.proved_targets": None,
            "proof.retained_targets": None,
            "proof.sites": None,
        }
    else:
        def target_counts(status: str) -> dict[str, int]:
            counts: dict[str, int] = {}
            for site in bounds:
                if site["status"] == status:
                    target = site["target"]
                    counts[target] = counts.get(target, 0) + 1
            return dict(sorted(counts.items()))

        proof_metrics = {
            "proof.bounds_sites": len(bounds),
            "proof.eligible": len(bounds),
            "proof.proved": sum(site["status"] == "proved" for site in bounds),
            "proof.retained": sum(site["status"] == "retained" for site in bounds),
            "proof.ceiling": sum(site["status"] == "ceiling" for site in bounds),
            "proof.partition_ok": len(bounds) == sum(
                site["status"] in {"proved", "retained", "ceiling"} for site in bounds
            ),
            "proof.dominating_guard": sum(
                site["proof"] == "dominating-guard" for site in bounds
            ),
            "proof.masked_index": sum(site["proof"] == "masked-index" for site in bounds),
            "proof.remainder_guard": sum(site["proof"] == "remainder-guard" for site in bounds),
            "proof.remainder_tail": sum(site["proof"] == "remainder-tail" for site in bounds),
            "proof.proved_targets": target_counts("proved"),
            "proof.retained_targets": target_counts("retained"),
            "proof.sites": bounds,
        }
    return {
        "raw_ir.alias_scope_uses": sum(
            "!alias.scope" in line for line in raw_body.splitlines() if not line.lstrip().startswith("!")
        ),
        "raw_ir.noalias_uses": sum(
            "!noalias" in line for line in raw_body.splitlines() if not line.lstrip().startswith("!")
        ),
        "raw_ir.saturating_add_mentions": raw_body.count("@llvm.uadd.sat"),
        "raw_ir.trap_calls": raw_body.count("call void @llvm.trap"),
        "opt_ir.loads": len(re.findall(r"(?m)^\s*%[^\n=]+?=\s*load\b", opt_body)),
        "opt_ir.vector_loads": len(re.findall(r"(?m)=\s*load\s+<\d+\s+x\s+", opt_body)),
        "opt_ir.vector_ops": sum(
            bool(re.search(r"<\d+\s+x\s+[^>]+>", line)) for line in opt_body.splitlines()
        ),
        "opt_ir.max_vector_width": max(ir_vector_widths, default=0),
        "opt_ir.saturating_add_mentions": opt_body.count("@llvm.uadd.sat"),
        "opt_ir.trap_calls": opt_body.count("call void @llvm.trap"),
        "asm.instructions": len(opcodes),
        "asm.opcodes": opcodes,
        "asm.traps": sum(opcode in {"brk", "ud2", "udf", "trap"} for opcode in opcodes),
        "remarks.vectorized_loops": len(vectors),
        "remarks.max_vector_width": max((width for width, _ in vectors), default=0),
        "remarks.max_interleave": max((interleave for _, interleave in vectors), default=0),
        **proof_metrics,
    }


def tool_version(command: list[str]) -> str | None:
    try:
        result = run(command)
    except HarnessError:
        return None
    return (result.stdout.strip() or result.stderr.strip()).splitlines()[0]


def environment_report() -> dict[str, str | None]:
    return {
        "architecture": platform.machine(),
        "system": platform.system(),
        "clang": tool_version([str(CLANG), "--version"]),
        "rustc": tool_version([shutil.which("rustc") or "rustc", "--version"]),
        "python": platform.python_version(),
    }


def validate_proof_report(report: list[dict[str, Any]]) -> None:
    by_function: dict[str, list[dict[str, Any]]] = {}
    for site in report:
        if not isinstance(site.get("function"), str) or not site["function"]:
            raise HarnessError(f"invalid proof-site function: {site!r}")
        if not isinstance(site.get("site"), int) or site["site"] < 0:
            raise HarnessError(f"invalid proof-site ordinal: {site!r}")
        if site.get("kind") not in {"const", "buffer", "buffer-field"}:
            raise HarnessError(f"invalid proof-site target kind: {site!r}")
        if not isinstance(site.get("target"), str) or not site["target"]:
            raise HarnessError(f"invalid proof-site target: {site!r}")
        if site.get("index") is not None and not isinstance(site["index"], str):
            raise HarnessError(f"invalid proof-site index: {site!r}")
        by_function.setdefault(site.get("function"), []).append(site)
        if site.get("status") not in {"proved", "retained", "ceiling"}:
            raise HarnessError(f"unknown proof-site status: {site!r}")
        if site.get("proof") not in {
                None, "dominating-guard", "masked-index", "remainder-guard", "remainder-tail"}:
            raise HarnessError(f"unknown bounds proof reason: {site!r}")
        if site["status"] == "proved" and site["proof"] is None:
            raise HarnessError(f"proved bounds site lacks a proof reason: {site!r}")
        if site["status"] == "retained" and site["proof"] is not None:
            raise HarnessError(f"retained bounds site carries an elision proof: {site!r}")
    for function, sites in by_function.items():
        ordinals = [site.get("site") for site in sites]
        if ordinals != list(range(len(sites))):
            raise HarnessError(f"non-contiguous bounds-site ordinals in {function}: {ordinals}")


def compile_variant(case_id: str, variant: dict[str, Any], build: Path, democ: Any) -> dict[str, Any]:
    name = variant["name"]
    kind = variant["kind"]
    source = (ROOT / variant["source"]).resolve()
    if not source.is_file() or ROOT not in source.parents:
        raise HarnessError(f"invalid source path for {case_id}/{name}: {source}")
    stem = re.sub(r"[^A-Za-z0-9_.-]", "-", f"{case_id}-{name}")
    raw_ir_path = build / f"{stem}.raw.ll"
    opt_ir_path = build / f"{stem}.opt.ll"
    asm_path = build / f"{stem}.s"
    level = str(variant.get("opt", "O2"))
    if not re.fullmatch(r"O[0-3sz]", level):
        raise HarnessError(f"invalid optimization level {level!r}")

    if kind == "xlang":
        proof_report: list[dict[str, Any]] = []
        raw_ir = democ.compile_program(
            source.read_text(),
            alias=bool(variant.get("facts", True)),
            elide_bounds=bool(variant.get("elide_bounds", False)),
            proof_report=proof_report,
        )
        validate_proof_report(proof_report)
        raw_ir_path.write_text(raw_ir)
        input_path = raw_ir_path
    elif kind == "c":
        input_path = source
    elif kind == "rust":
        rustc = shutil.which("rustc")
        if not rustc:
            raise HarnessError("rustc not found")
        run([rustc, "-C", f"opt-level={level[1:]}", "--emit", "asm", str(source), "-o", str(asm_path)])
        run([rustc, "-C", f"opt-level={level[1:]}", "--emit", "llvm-ir", str(source), "-o", str(opt_ir_path)])
        optimized_ir = opt_ir_path.read_text()
        return metrics(optimized_ir, optimized_ir, asm_path.read_text(), "", variant.get("function"))
    else:
        raise HarnessError(f"unknown variant kind {kind!r}")

    remark_flags = [
        "-Rpass=loop-vectorize",
        "-Rpass-missed=loop-vectorize",
        "-Rpass-analysis=loop-vectorize",
    ]
    compiled = run([str(CLANG), f"-{level}", *remark_flags, "-S", str(input_path), "-o", str(asm_path)])
    run([str(CLANG), f"-{level}", "-S", "-emit-llvm", str(input_path), "-o", str(opt_ir_path)])
    optimized_ir = opt_ir_path.read_text()
    if kind == "c":
        raw_ir = optimized_ir
    return metrics(raw_ir, optimized_ir, asm_path.read_text(), compiled.stderr,
                   variant.get("function"), proof_report if kind == "xlang" else None)


def resolve(reference: str, variants: dict[str, dict[str, Any]]) -> Any:
    name, separator, metric = reference.partition(".")
    if not separator or name not in variants or metric not in variants[name]:
        raise HarnessError(f"unknown metric reference {reference!r}")
    return variants[name][metric]


def compact(value: Any) -> str:
    if isinstance(value, list):
        preview = ",".join(str(item) for item in value[:8])
        suffix = ",…" if len(value) > 8 else ""
        return f"[{len(value)} items: {preview}{suffix}]"
    return repr(value)


def evaluate(check: dict[str, Any], variants: dict[str, dict[str, Any]]) -> tuple[bool, Any, Any]:
    operation = check.get("op", "eq")
    if operation not in OPS:
        raise HarnessError(f"unknown comparison operator {operation!r}")
    left = resolve(check["left"], variants)
    right = resolve(check["right"], variants) if "right" in check else check["value"]
    return bool(OPS[operation](left, right)), left, right


def validate_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if manifest.get("schema") != 1:
        raise HarnessError("manifest schema must be 1")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise HarnessError("manifest must contain at least one case")
    case_ids: set[str] = set()
    for case in cases:
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id or case_id in case_ids:
            raise HarnessError(f"invalid or duplicate case id {case_id!r}")
        case_ids.add(case_id)
        if case.get("mode") not in {"gate", "audit"}:
            raise HarnessError(f"{case_id}: mode must be 'gate' or 'audit'")
        variants = case.get("variants")
        if not isinstance(variants, list) or not variants:
            raise HarnessError(f"{case_id}: at least one variant is required")
        names = [variant.get("name") for variant in variants]
        if any(not isinstance(name, str) or not name for name in names) or len(names) != len(set(names)):
            raise HarnessError(f"{case_id}: variant names must be non-empty and unique")
        for variant in variants:
            if variant.get("kind") not in {"xlang", "c", "rust"}:
                raise HarnessError(f"{case_id}/{variant.get('name')}: invalid kind")
            if not isinstance(variant.get("source"), str):
                raise HarnessError(f"{case_id}/{variant.get('name')}: source is required")
        checks = case.get("checks")
        if not isinstance(checks, list) or not checks:
            raise HarnessError(f"{case_id}: at least one check is required")
        for check in checks:
            if not isinstance(check.get("left"), str) or (("right" in check) == ("value" in check)):
                raise HarnessError(f"{case_id}: each check needs left and exactly one of right/value")
            if check.get("op", "eq") not in OPS:
                raise HarnessError(f"{case_id}: invalid comparison operator {check.get('op')!r}")
    return cases


def load_corpus_cases() -> list[dict[str, Any]]:
    """Translate compact family manifests into ordinary parity-harness cases."""
    cases: list[dict[str, Any]] = []
    if not CORPUS_ROOT.is_dir():
        return cases
    for manifest_path in sorted(CORPUS_ROOT.rglob("cases.json")):
        family_manifest = json.loads(manifest_path.read_text())
        if family_manifest.get("schema") != 1 or not isinstance(family_manifest.get("cases"), list):
            raise HarnessError(f"invalid corpus family manifest: {manifest_path}")
        family = family_manifest.get("family")
        if not isinstance(family, str) or not family:
            raise HarnessError(f"corpus family is required: {manifest_path}")
        family_tags = family_manifest.get("tags", [])
        if not isinstance(family_tags, list) or not all(isinstance(tag, str) for tag in family_tags):
            raise HarnessError(f"corpus family tags must be strings: {manifest_path}")
        measurement = family_manifest.get("measurement", {})
        function = measurement.get("function")
        if not function:
            function = "probe" if family == "bounds/dominating-guard" else None
        if not function:
            raise HarnessError(f"corpus measurement function is required: {manifest_path}")
        if measurement.get("metric") != "proof.sites":
            raise HarnessError(f"unsupported corpus proof metric in {manifest_path}")
        for entry in family_manifest["cases"]:
            source_name = entry.get("source")
            if not isinstance(source_name, str):
                raise HarnessError(f"corpus source is required: {manifest_path}")
            source_path = (manifest_path.parent / source_name).resolve()
            if not source_path.is_file() or ROOT not in source_path.parents:
                raise HarnessError(f"invalid corpus source: {source_path}")
            expected = entry.get("expected", {})
            classification = expected.get("proof_classification", expected.get("classification"))
            if classification not in {"proved", "elided", "retained", "checked", "mixed"}:
                raise HarnessError(f"invalid proof classification for {source_path}")
            is_positive = classification in {"proved", "elided"}
            expected_sites = expected.get("bounds_sites")
            if not isinstance(expected_sites, int) or expected_sites < 1:
                raise HarnessError(f"expected.bounds_sites is required for {source_path}")
            maturity = entry.get("maturity")
            if maturity not in {"explore", "audit", "gate"}:
                raise HarnessError(f"invalid corpus maturity for {source_path}")
            mode = "gate" if maturity == "gate" else "audit"
            entry_tags = entry.get("tags")
            if not isinstance(entry_tags, list) or not entry_tags \
                    or not all(isinstance(tag, str) for tag in entry_tags):
                raise HarnessError(f"corpus case tags must be non-empty strings: {source_path}")
            stem = entry.get("id", source_path.stem)
            case_id = "corpus." + family.replace("/", ".") + "." + stem
            relative_source = str(source_path.relative_to(ROOT))
            checks = []
            checks.extend([
                {
                    "label": "facts enumerate every expected bounds site",
                    "left": "facts.proof.eligible",
                    "op": "eq",
                    "value": expected_sites,
                },
                {
                    "label": "facts-off enumerates the same bounds sites",
                    "left": "nofacts.proof.eligible",
                    "op": "eq",
                    "value": expected_sites,
                },
                {
                    "label": "proof status partition is complete",
                    "left": "facts.proof.partition_ok",
                    "op": "eq",
                    "value": True,
                },
            ])
            if is_positive:
                checks.extend([
                    {
                        "label": "facts prove the eligible access sites",
                        "left": "facts.proof.proved",
                        "op": "eq",
                        "value": expected_sites,
                    },
                    {
                        "label": "facts leave no eligible site checked",
                        "left": "facts.proof.retained",
                        "op": "eq",
                        "value": 0,
                    },
                    {
                        "label": "facts-off retains exactly the proved sites",
                        "left": "nofacts.proof.retained",
                        "op": "eq",
                        "value": expected_sites,
                    },
                ])
            elif classification == "mixed":
                proved_sites = expected.get("proved_sites")
                retained_sites = expected.get("retained_sites")
                if not isinstance(proved_sites, int) or not isinstance(retained_sites, int) \
                        or proved_sites < 1 or retained_sites < 1 \
                        or proved_sites + retained_sites != expected_sites:
                    raise HarnessError(f"invalid mixed proof counts for {source_path}")
                checks.extend([
                    {
                        "label": "mixed case proves exactly its eligible subset",
                        "left": "facts.proof.proved",
                        "op": "eq",
                        "value": proved_sites,
                    },
                    {
                        "label": "mixed case retains exactly its unsafe subset",
                        "left": "facts.proof.retained",
                        "op": "eq",
                        "value": retained_sites,
                    },
                    {
                        "label": "facts-off retains every mixed-case site",
                        "left": "nofacts.proof.retained",
                        "op": "eq",
                        "value": expected_sites,
                    },
                ])
            else:
                checks.extend([
                    {
                        "label": "near-miss proves no access site",
                        "left": "facts.proof.proved",
                        "op": "eq",
                        "value": 0,
                    },
                    {
                        "label": "near-miss retains the dynamic sites",
                        "left": "facts.proof.retained",
                        "op": "eq",
                        "value": expected_sites,
                    },
                    {
                        "label": "facts do not overgeneralize beyond the control",
                        "left": "nofacts.proof.retained",
                        "op": "eq",
                        "value": expected_sites,
                    },
                ])
            cases.append({
                "id": case_id,
                "mode": mode,
                "maturity": maturity,
                "tags": sorted(set(family_tags + entry_tags)),
                "description": entry.get("hypothesis", family_manifest.get("hypothesis", "")),
                "variants": [
                    {
                        "name": "facts",
                        "kind": "xlang",
                        "source": relative_source,
                        "function": function,
                        "opt": measurement.get("opt", "O2"),
                    },
                    {
                        "name": "nofacts",
                        "kind": "xlang",
                        "source": relative_source,
                        "function": function,
                        "facts": False,
                        "opt": measurement.get("opt", "O2"),
                    },
                ],
                "checks": checks,
            })
    return cases


def run_case(case: dict[str, Any], build: Path, democ: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": case["id"],
        "mode": case["mode"],
        "maturity": case.get("maturity", case["mode"]),
        "tags": case.get("tags", []),
        "description": case.get("description", ""),
        "variants": {},
        "checks": [],
    }
    try:
        for variant in case["variants"]:
            result["variants"][variant["name"]] = compile_variant(case["id"], variant, build, democ)
        for check in case["checks"]:
            passed, left, right = evaluate(check, result["variants"])
            result["checks"].append({
                "label": check.get("label", check["left"]),
                "passed": passed,
                "left": left,
                "op": check.get("op", "eq"),
                "right": right,
            })
    except Exception as error:  # preserve a useful per-case report for compiler/checker failures
        result["error"] = str(error)
    result["passed"] = "error" not in result and all(check["passed"] for check in result["checks"])
    return result


def print_report(results: list[dict[str, Any]]) -> None:
    for result in results:
        label = result["mode"]
        if result["maturity"] != result["mode"]:
            label += f"/{result['maturity']}"
        print(f"\n== {result['id']} [{label}] ==")
        if result["description"]:
            print(result["description"])
        if "error" in result:
            marker = "FAIL" if result["mode"] == "gate" else "DEBT"
            print(f"  {marker}: {result['error']}")
            continue
        for check in result["checks"]:
            if check["passed"]:
                marker = "PASS"
            else:
                marker = "FAIL" if result["mode"] == "gate" else "DEBT"
            print(
                f"  {marker}: {check['label']} "
                f"({compact(check['left'])} {check['op']} {compact(check['right'])})"
            )
    gate_failures = sum(not item["passed"] and item["mode"] == "gate" for item in results)
    audit_debts = sum(not item["passed"] and item["mode"] == "audit" for item in results)
    print(f"\ncodegen parity: {gate_failures} gate failure(s), {audit_debts} known audit debt(s)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--case", action="append", dest="cases", help="run only this case id")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--gate-only", action="store_true")
    group.add_argument("--audit-only", action="store_true")
    parser.add_argument("--corpus", action="store_true", help="append discovered codegen-corpus families")
    parser.add_argument("--tag", action="append", dest="tags", help="run cases carrying this corpus tag")
    parser.add_argument("--json", action="store_true", help="emit the complete machine-readable report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = json.loads(args.manifest.read_text())
        selected = validate_manifest(manifest)
        if args.corpus:
            selected = selected + load_corpus_cases()
            # Validate the translated cases too; this also catches duplicate or
            # malformed generated definitions before any compiler is invoked.
            selected = validate_manifest({"schema": 1, "cases": selected})
        if args.tags:
            wanted_tags = set(args.tags)
            selected = [case for case in selected if wanted_tags.issubset(set(case.get("tags", [])))]
        if args.cases:
            wanted = set(args.cases)
            selected = [case for case in selected if case["id"] in wanted]
            missing = wanted - {case["id"] for case in selected}
            if missing:
                raise HarnessError(f"unknown case(s): {', '.join(sorted(missing))}")
        if args.gate_only:
            selected = [case for case in selected if case["mode"] == "gate"]
        if args.audit_only:
            selected = [case for case in selected if case["mode"] == "audit"]
        democ = load_democ()
        with tempfile.TemporaryDirectory(prefix="xlang-codegen-parity-") as temporary:
            build = Path(temporary)
            results = [run_case(case, build, democ) for case in selected]
    except (OSError, KeyError, ValueError, HarnessError) as error:
        print(f"codegen parity harness error: {error}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"schema": 1, "environment": environment_report(), "results": results},
                         indent=2, sort_keys=True))
    else:
        print_report(results)
    return int(any(not item["passed"] and item["mode"] == "gate" for item in results))


if __name__ == "__main__":
    raise SystemExit(main())
