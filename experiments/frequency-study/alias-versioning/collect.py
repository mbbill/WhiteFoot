#!/usr/bin/env python3
"""Calibration-only detector for LLVM loop-vectorizer alias memchecks.

The public entry point is ``analyze_ir``.  The command-line default compiles
the existing scoped-alias Rust benchmark into a temporary optimized LLVM IR
file, analyzes it, and writes one JSON document to stdout.  No generated IR is
kept in the repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
CALIBRATION_SOURCE = REPO_ROOT / "experiments/scoped-alias-channel/rust_kernels.rs"
EXPECTED_CALIBRATION_LOOPS = 2
SCHEMA = "xlang.alias-versioning-calibration.v1"
EXPECTED_CALIBRATION_FINGERPRINT = {
    "raw_vector_memcheck_block_count": 2,
    "validated_alias_versioned_loop_count": 2,
    "first_party_alias_versioned_loop_count": 2,
    "rejected_memcheck_count": 0,
    "conflict_predicate_count": 26,
    "pointer_comparison_count": 52,
}

_DEFINE_RE = re.compile(r"^\s*define\b")
_FUNCTION_NAME_RE = re.compile(r"@(?P<name>\"(?:[^\"\\]|\\.)*\"|[^\s(]+)\s*\(")
_BLOCK_RE = re.compile(
    r'^\s*(?P<label>"(?:[^"\\]|\\.)*"|[-a-zA-Z$._0-9]+):\s*(?:;.*)?$'
)
_SUCCESSOR_RE = re.compile(r'label\s+%(?P<label>"(?:[^"\\]|\\.)*"|[-a-zA-Z$._0-9]+)')
_METADATA_RE = re.compile(r"^!(?P<id>[0-9]+)\s*=\s*(?P<body>.*)$")
_DBG_RE = re.compile(r"!dbg\s+!(?P<id>[0-9]+)")
_FIELD_REF_RE = re.compile(r"\b(?P<field>scope|file|inlinedAt):\s*!(?P<id>[0-9]+)")
_LINE_RE = re.compile(r"\bline:\s*(?P<line>[0-9]+)")
_COLUMN_RE = re.compile(r"\bcolumn:\s*(?P<column>[0-9]+)")
_FILENAME_RE = re.compile(r'\bfilename:\s*"(?P<value>(?:[^"\\]|\\.)*)"')
_DIRECTORY_RE = re.compile(r'\bdirectory:\s*"(?P<value>(?:[^"\\]|\\.)*)"')
_FOUND_CONFLICT_RE = re.compile(r"^\s*%found\.conflict[^=]*=\s*and\s+i1\b")
_POINTER_COMPARE_RE = re.compile(r"^\s*%[^=]+\s*=\s*icmp\s+\w+\s+ptr\b")
_TOP_LEVEL_IR_RE = re.compile(
    r'''^\s*(?:
        source_filename\s*=\s*"(?:[^"\\]|\\.)*"|
        target\s+(?:datalayout|triple)\s*=\s*"(?:[^"\\]|\\.)*"|
        declare\b.*@(?:"(?:[^"\\]|\\.)*"|[-a-zA-Z$._0-9]+)\s*\(.*\).*$|
        module\s+asm\s+"(?:[^"\\]|\\.)*"|
        @(?:"(?:[^"\\]|\\.)*"|[-a-zA-Z$._0-9]+)\s*=\s*\S.*|
        %(?:"(?:[^"\\]|\\.)*"|[-a-zA-Z$._0-9]+)\s*=\s*type\b.*|
        \$(?:"(?:[^"\\]|\\.)*"|[-a-zA-Z$._0-9]+)\s*=\s*comdat\b.*|
        attributes\s+\#[0-9]+\s*=\s*\{.*\}|
        !(?:[0-9]+|[-a-zA-Z$._0-9]+)\s*=\s*(?:distinct\s+)?!.*|
        uselistorder(?:_bb)?\b.*
    )\s*$''',
    re.VERBOSE,
)


def _strip_llvm_comment(line: str) -> str:
    """Remove an LLVM ``;`` comment without cutting a quoted token/string."""

    in_quote = False
    index = 0
    while index < len(line):
        character = line[index]
        if in_quote and character == "\\":
            # LLVM normally escapes bytes as ``\XX``.  Skipping the escaped
            # byte (or the next character for a malformed escape) prevents an
            # escaped quote from changing the lexical state.
            if (
                index + 2 < len(line)
                and line[index + 1] in "0123456789abcdefABCDEF"
                and line[index + 2] in "0123456789abcdefABCDEF"
            ):
                index += 3
            else:
                index += 2
            continue
        if character == '"':
            in_quote = not in_quote
        elif character == ";" and not in_quote:
            return line[:index]
        index += 1
    return line


def _llvm_unquote(value: str) -> str:
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    # LLVM strings use two hexadecimal digits after a backslash for escaped
    # bytes.  Rust paths and symbols in this fixture are ASCII, but decoding
    # this small subset makes path handling deterministic for spaces, quotes,
    # and backslashes as well.
    def replace_hex(match: re.Match[str]) -> str:
        return chr(int(match.group(1), 16))

    return re.sub(r"\\([0-9A-Fa-f]{2})", replace_hex, value)


@dataclass(frozen=True)
class Block:
    label: str
    lines: tuple[str, ...]

    @property
    def successors(self) -> tuple[str, ...]:
        values: list[str] = []
        for line in self.lines:
            for match in _SUCCESSOR_RE.finditer(line):
                label = _llvm_unquote(match.group("label"))
                if label not in values:
                    values.append(label)
        return tuple(values)


@dataclass(frozen=True)
class Function:
    name: str
    blocks: tuple[Block, ...]


def _parse_functions(ir: str) -> list[Function]:
    functions: list[Function] = []
    # Keep every later structural and instruction matcher on the same lexical
    # view.  In particular, a comment cannot contribute a CFG successor,
    # debug attachment, or predicate-looking instruction.
    lines = [_strip_llvm_comment(line) for line in ir.splitlines()]
    if not any(line.strip() for line in lines):
        raise ValueError("input is empty or contains only LLVM comments")

    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if not _DEFINE_RE.match(line):
            if _TOP_LEVEL_IR_RE.match(line):
                index += 1
                continue
            raise ValueError(f"unrecognized top-level LLVM IR at line {index + 1}")

        function_line = index + 1
        header_parts = [line]
        while not header_parts[-1].strip().endswith("{"):
            index += 1
            if index >= len(lines):
                raise ValueError(
                    f"function definition at line {function_line} has no opening '{{'"
                )
            continuation = lines[index]
            if _DEFINE_RE.match(continuation):
                raise ValueError(
                    f"nested function definition at line {index + 1} before "
                    f"function from line {function_line} opened"
                )
            if continuation.strip() and _TOP_LEVEL_IR_RE.match(continuation):
                raise ValueError(
                    f"top-level construct at line {index + 1} interrupts "
                    f"function header from line {function_line}"
                )
            header_parts.append(continuation)
        header = " ".join(header_parts)
        name_match = _FUNCTION_NAME_RE.search(header)
        if not name_match:
            raise ValueError(f"malformed function definition at line {function_line}")
        name = _llvm_unquote(name_match.group("name"))

        blocks: list[Block] = []
        block_labels: set[str] = set()
        current_label: str | None = None
        current_lines: list[str] = []
        closed = False
        index += 1
        while index < len(lines):
            body_line = lines[index]
            if body_line.strip() == "}":
                closed = True
                break
            if _DEFINE_RE.match(body_line):
                raise ValueError(
                    f"nested function definition at line {index + 1} before "
                    f"function {name!r} closes"
                )
            block_match = _BLOCK_RE.match(body_line)
            if block_match:
                if current_label is not None:
                    blocks.append(Block(current_label, tuple(current_lines)))
                next_label = _llvm_unquote(block_match.group("label"))
                if next_label in block_labels:
                    raise ValueError(
                        f"duplicate block label {next_label!r} in function {name!r} "
                        f"at line {index + 1}"
                    )
                block_labels.add(next_label)
                current_label = next_label
                current_lines = []
            elif current_label is not None:
                current_lines.append(body_line)
            index += 1
        if not closed:
            raise ValueError(
                f"function {name!r} from line {function_line} is missing closing '}}'"
            )
        if current_label is not None:
            blocks.append(Block(current_label, tuple(current_lines)))
        functions.append(Function(name, tuple(blocks)))
        index += 1
    return functions


class DebugMetadata:
    def __init__(self, ir: str) -> None:
        self.nodes: dict[int, str] = {}
        for line in ir.splitlines():
            line = _strip_llvm_comment(line)
            match = _METADATA_RE.match(line)
            if match:
                self.nodes[int(match.group("id"))] = match.group("body")

    def _reference(self, node_id: int, field: str) -> int | None:
        body = self.nodes.get(node_id, "")
        for match in _FIELD_REF_RE.finditer(body):
            if match.group("field") == field:
                return int(match.group("id"))
        return None

    def _outermost_location(self, node_id: int) -> int:
        seen: set[int] = set()
        while node_id not in seen:
            seen.add(node_id)
            outer = self._reference(node_id, "inlinedAt")
            if outer is None:
                return node_id
            node_id = outer
        return node_id

    def _file_node(self, node_id: int) -> int | None:
        seen: set[int] = set()
        while node_id not in seen:
            seen.add(node_id)
            body = self.nodes.get(node_id, "")
            if "!DIFile(" in body:
                return node_id
            file_ref = self._reference(node_id, "file")
            if file_ref is not None:
                return file_ref
            scope_ref = self._reference(node_id, "scope")
            if scope_ref is None:
                return None
            node_id = scope_ref
        return None

    def resolve_location(self, node_id: int) -> dict[str, object] | None:
        node_id = self._outermost_location(node_id)
        body = self.nodes.get(node_id, "")
        line_match = _LINE_RE.search(body)
        if not line_match:
            return None
        column_match = _COLUMN_RE.search(body)
        scope_ref = self._reference(node_id, "scope")
        file_node = self._file_node(scope_ref) if scope_ref is not None else None
        if file_node is None:
            return None
        file_body = self.nodes.get(file_node, "")
        filename_match = _FILENAME_RE.search(file_body)
        if not filename_match:
            return None
        directory_match = _DIRECTORY_RE.search(file_body)
        filename = _llvm_unquote(filename_match.group("value"))
        directory = _llvm_unquote(directory_match.group("value")) if directory_match else ""
        path = Path(filename) if os.path.isabs(filename) else Path(directory) / filename
        return {
            "path": str(path.resolve(strict=False)),
            "line": int(line_match.group("line")),
            "column": int(column_match.group("column")) if column_match else 0,
        }


def _reachable_vector_bodies(start: Iterable[str], blocks: dict[str, Block]) -> list[str]:
    pending = list(start)
    seen: set[str] = set()
    bodies: set[str] = set()
    # The parsed function is finite, and ``seen`` guarantees termination even
    # for cyclic CFGs.  A fixed visit cap would silently turn a sufficiently
    # deep, valid CFG into a negative result.
    while pending:
        label = pending.pop()
        if label in seen:
            continue
        seen.add(label)
        if label.startswith("vector.body"):
            bodies.add(label)
            continue
        block = blocks.get(label)
        if block is not None:
            pending.extend(block.successors)
    return sorted(bodies)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def _portable_location(
    location: dict[str, object] | None, source_root: Path | None
) -> tuple[dict[str, object] | None, bool | None]:
    if location is None:
        return None, None
    path = Path(str(location["path"]))
    first_party = _is_within(path, source_root) if source_root is not None else None
    result = dict(location)
    if source_root is not None and first_party:
        result["path"] = path.resolve(strict=False).relative_to(
            source_root.resolve(strict=False)
        ).as_posix()
    return result, first_party


def analyze_ir(ir: str, source_root: Path | None = None) -> dict[str, object]:
    """Return a deterministic summary of loop-vectorizer memcheck blocks.

    A block is counted as a validated alias-versioned loop only when its label
    starts with LLVM's ``vector.memcheck`` convention and one of its CFG
    successors reaches a ``vector.body`` block.  Merely mentioning the token in
    a comment or metadata is not enough.
    """

    functions = _parse_functions(ir)
    metadata = DebugMetadata(ir)
    loops: list[dict[str, object]] = []
    rejected: list[dict[str, str]] = []
    raw_memchecks = 0

    for function in functions:
        block_map = {block.label: block for block in function.blocks}
        for block in function.blocks:
            if not block.label.startswith("vector.memcheck"):
                continue
            raw_memchecks += 1
            vector_bodies = _reachable_vector_bodies(block.successors, block_map)
            if not vector_bodies:
                rejected.append(
                    {
                        "function": function.name,
                        "memcheck_block": block.label,
                        "reason": "no-reachable-vector-body",
                    }
                )
                continue

            debug_id: int | None = None
            for line in reversed(block.lines):
                match = _DBG_RE.search(line)
                if match:
                    debug_id = int(match.group("id"))
                    break
            location = metadata.resolve_location(debug_id) if debug_id is not None else None
            portable_location, first_party = _portable_location(location, source_root)
            loops.append(
                {
                    "function": function.name,
                    "memcheck_block": block.label,
                    "successors": list(block.successors),
                    "vector_body_blocks": vector_bodies,
                    "conflict_predicate_count": sum(
                        bool(_FOUND_CONFLICT_RE.match(line)) for line in block.lines
                    ),
                    "pointer_comparison_count": sum(
                        bool(_POINTER_COMPARE_RE.match(line)) for line in block.lines
                    ),
                    "debug_location": portable_location,
                    "first_party": first_party,
                }
            )

    loops.sort(key=lambda item: (str(item["function"]), str(item["memcheck_block"])))
    rejected.sort(key=lambda item: (item["function"], item["memcheck_block"]))
    first_party_loops = [loop for loop in loops if loop["first_party"] is True]
    return {
        "llvm_function_count": len(functions),
        "raw_vector_memcheck_block_count": raw_memchecks,
        "validated_alias_versioned_loop_count": len(loops),
        "first_party_alias_versioned_loop_count": len(first_party_loops),
        "conflict_predicate_count": sum(
            int(loop["conflict_predicate_count"]) for loop in loops
        ),
        "pointer_comparison_count": sum(
            int(loop["pointer_comparison_count"]) for loop in loops
        ),
        "loops": loops,
        "rejected_memchecks": rejected,
    }


def _calibration_fingerprint(analysis: dict[str, object]) -> dict[str, int]:
    """Select every calibrated fact whose drift invalidates the detector."""

    return {
        "raw_vector_memcheck_block_count": int(
            analysis["raw_vector_memcheck_block_count"]
        ),
        "validated_alias_versioned_loop_count": int(
            analysis["validated_alias_versioned_loop_count"]
        ),
        "first_party_alias_versioned_loop_count": int(
            analysis["first_party_alias_versioned_loop_count"]
        ),
        "rejected_memcheck_count": len(analysis["rejected_memchecks"]),
        "conflict_predicate_count": int(analysis["conflict_predicate_count"]),
        "pointer_comparison_count": int(analysis["pointer_comparison_count"]),
    }


def _calibration_result(analysis: dict[str, object]) -> dict[str, object]:
    observed = _calibration_fingerprint(analysis)
    return {
        # Retain these two scalar fields for readers of the v1 calibration
        # report while making the full fingerprint authoritative.
        "expected_first_party_alias_versioned_loop_count": EXPECTED_CALIBRATION_LOOPS,
        "observed_first_party_alias_versioned_loop_count": observed[
            "first_party_alias_versioned_loop_count"
        ],
        "expected_fingerprint": dict(EXPECTED_CALIBRATION_FINGERPRINT),
        "observed_fingerprint": observed,
        "matches_expected": observed == EXPECTED_CALIBRATION_FINGERPRINT,
    }


def _toolchain_info(rustc: str) -> dict[str, str]:
    completed = subprocess.run(
        [rustc, "--version", "--verbose"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    values: dict[str, str] = {}
    first = completed.stdout.splitlines()[0]
    values["version"] = first
    for line in completed.stdout.splitlines()[1:]:
        if ": " in line:
            key, value = line.split(": ", 1)
            if key in {"commit-hash", "commit-date", "host", "release", "LLVM version"}:
                values[key.replace(" ", "_")] = value
    return values


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def calibration_report(rustc: str = "rustc") -> dict[str, object]:
    if shutil.which(rustc) is None:
        raise RuntimeError(f"rust compiler not found: {rustc}")
    if not CALIBRATION_SOURCE.is_file():
        raise RuntimeError(f"calibration source not found: {CALIBRATION_SOURCE}")

    compile_args = [
        rustc,
        "--edition=2021",
        "-C",
        "opt-level=3",
        "-C",
        "codegen-units=1",
        "-C",
        "debuginfo=line-tables-only",
        "--emit=llvm-ir",
    ]
    with tempfile.TemporaryDirectory(prefix="xlang-alias-versioning-") as temporary:
        ir_path = Path(temporary) / "calibration.ll"
        command = [*compile_args, "-o", str(ir_path), str(CALIBRATION_SOURCE)]
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "calibration compilation failed with exit "
                f"{completed.returncode}:\n{completed.stderr.strip()}"
            )
        analysis = analyze_ir(ir_path.read_text(), source_root=REPO_ROOT)

    return {
        "schema": SCHEMA,
        "mode": "calibration-only",
        "input": {
            "path": CALIBRATION_SOURCE.relative_to(REPO_ROOT).as_posix(),
            "sha256": _sha256(CALIBRATION_SOURCE),
        },
        "toolchain": _toolchain_info(rustc),
        "compile": {
            "arguments": [
                "rustc",
                "--edition=2021",
                "-C",
                "opt-level=3",
                "-C",
                "codegen-units=1",
                "-C",
                "debuginfo=line-tables-only",
                "--emit=llvm-ir",
            ],
            "working_directory": ".",
            "generated_ir_retained": False,
        },
        "analysis": analysis,
        "calibration": _calibration_result(analysis),
    }


def _analysis_report(ir_path: Path, source_root: Path | None) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "mode": "ir-analysis",
        "input": {
            "path": str(ir_path),
            "sha256": _sha256(ir_path),
        },
        "analysis": analyze_ir(ir_path.read_text(), source_root=source_root),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ir",
        type=Path,
        help="analyze an existing optimized LLVM IR file instead of running calibration",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        help="root used to mark and relativize first-party debug locations",
    )
    parser.add_argument("--rustc", default="rustc", help="rustc executable for calibration")
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON")
    parser.add_argument(
        "--allow-calibration-drift",
        action="store_true",
        help="return success even if the calibration count differs from the expected two loops",
    )
    args = parser.parse_args(argv)

    try:
        if args.ir is not None:
            if not args.ir.is_file():
                parser.error(f"IR file does not exist: {args.ir}")
            report = _analysis_report(args.ir, args.source_root)
        else:
            if args.source_root is not None:
                parser.error("--source-root is only valid with --ir")
            report = calibration_report(args.rustc)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    json.dump(report, sys.stdout, indent=2 if args.pretty else None, sort_keys=True)
    sys.stdout.write("\n")
    if (
        args.ir is None
        and not args.allow_calibration_drift
        and not bool(report["calibration"]["matches_expected"])
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
