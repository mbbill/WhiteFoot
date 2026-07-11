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
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True  # the repository contains historical tracked pyc files
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "codegen-parity.json"
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
            function: str | None) -> dict[str, Any]:
    opt_body = llvm_function(optimized_ir, function)
    asm_body = assembly_function(assembly, function)
    opcodes = assembly_opcodes(asm_body)
    vectors = [(int(width), int(interleave)) for width, interleave in VECTOR_REMARK.findall(remarks)]
    return {
        "raw_ir.alias_scope_uses": sum(
            "!alias.scope" in line for line in raw_ir.splitlines() if not line.lstrip().startswith("!")
        ),
        "raw_ir.noalias_uses": sum(
            "!noalias" in line for line in raw_ir.splitlines() if not line.lstrip().startswith("!")
        ),
        "raw_ir.saturating_add_mentions": raw_ir.count("@llvm.uadd.sat"),
        "raw_ir.trap_calls": raw_ir.count("call void @llvm.trap"),
        "opt_ir.loads": len(re.findall(r"(?m)^\s*%[^\n=]+?=\s*load\b", opt_body)),
        "opt_ir.vector_loads": len(re.findall(r"(?m)=\s*load\s+<\d+\s+x\s+", opt_body)),
        "opt_ir.trap_calls": opt_body.count("call void @llvm.trap"),
        "asm.instructions": len(opcodes),
        "asm.opcodes": opcodes,
        "asm.traps": sum(opcode in {"brk", "ud2", "udf", "trap"} for opcode in opcodes),
        "remarks.vectorized_loops": len(vectors),
        "remarks.max_vector_width": max((width for width, _ in vectors), default=0),
        "remarks.max_interleave": max((interleave for _, interleave in vectors), default=0),
    }


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
        raw_ir = democ.compile_program(
            source.read_text(),
            alias=bool(variant.get("facts", True)),
            elide_bounds=bool(variant.get("elide_bounds", False)),
        )
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
    return metrics(raw_ir, optimized_ir, asm_path.read_text(), compiled.stderr, variant.get("function"))


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


def run_case(case: dict[str, Any], build: Path, democ: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": case["id"],
        "mode": case["mode"],
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
        print(f"\n== {result['id']} [{result['mode']}] ==")
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
    parser.add_argument("--json", action="store_true", help="emit the complete machine-readable report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = json.loads(args.manifest.read_text())
        selected = validate_manifest(manifest)
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
        print(json.dumps({"schema": 1, "results": results}, indent=2, sort_keys=True))
    else:
        print_report(results)
    return int(any(not item["passed"] and item["mode"] == "gate" for item in results))


if __name__ == "__main__":
    raise SystemExit(main())
