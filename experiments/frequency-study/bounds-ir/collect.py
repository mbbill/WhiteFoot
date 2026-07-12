#!/usr/bin/env python3
"""Find heuristic surviving Rust bounds checks in optimized textual LLVM IR."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SCHEMA = "xlang.bounds-ir-candidates.v1"
CLASSIFICATION = "heuristic-surviving-bounds-candidate"

_DEFINE_RE = re.compile(r"^\s*define\b")
_FUNCTION_NAME_RE = re.compile(
    r'@(?P<name>"(?:[^"\\]|\\.)*"|[-a-zA-Z$._0-9]+)\s*\('
)
_METADATA_RE = re.compile(r"^!(?P<id>[0-9]+)\s*=\s*(?P<body>.*)$")
_DBG_RE = re.compile(r"!dbg\s+!(?P<id>[0-9]+)")
_LINE_RE = re.compile(r"\bline:\s*(?P<value>[0-9]+)")
_COLUMN_RE = re.compile(r"\bcolumn:\s*(?P<value>[0-9]+)")
_FILENAME_RE = re.compile(r'\bfilename:\s*"(?P<value>(?:[^"\\]|\\.)*)"')
_DIRECTORY_RE = re.compile(r'\bdirectory:\s*"(?P<value>(?:[^"\\]|\\.)*)"')
_OPCODE_RE = re.compile(r"(?:^|\s)(?P<kind>call|invoke)\s")
_TOP_LEVEL_RE = re.compile(
    r'''^\s*(?:
        source_filename\s*=\s*"(?:[^"\\]|\\.)*"|
        target\s+(?:datalayout|triple)\s*=\s*"(?:[^"\\]|\\.)*"|
        module\s+asm\s+"(?:[^"\\]|\\.)*"|
        declare\b.*|
        @(?:(?:"(?:[^"\\]|\\.)*")|[-a-zA-Z$._0-9]+)\s*=\s*\S.*|
        %(?:(?:"(?:[^"\\]|\\.)*")|[-a-zA-Z$._0-9]+)\s*=\s*type\b.*|
        \$(?:(?:"(?:[^"\\]|\\.)*")|[-a-zA-Z$._0-9]+)\s*=\s*comdat\b.*|
        attributes\s+\#[0-9]+\s*=\s*\{.*\}|
        !(?:[0-9]+|[-a-zA-Z$._0-9]+)\s*=\s*(?:distinct\s+)?!.*|
        uselistorder(?:_bb)?\b.*
    )\s*$''',
    re.VERBOSE,
)


def _strip_comment(line: str) -> str:
    """Strip an LLVM comment while preserving semicolons in quoted strings."""

    quoted = False
    index = 0
    while index < len(line):
        character = line[index]
        if quoted and character == "\\":
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
            quoted = not quoted
        elif character == ";" and not quoted:
            return line[:index]
        index += 1
    return line


def _llvm_unescape(value: str) -> str:
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return re.sub(
        r"\\([0-9A-Fa-f]{2})",
        lambda match: chr(int(match.group(1), 16)),
        value,
    )


def _outside_quotes(line: str) -> str:
    """Return a same-width lexical view with quoted contents blanked."""

    result = list(line)
    quoted = False
    index = 0
    while index < len(line):
        character = line[index]
        if quoted:
            result[index] = " "
            if character == "\\":
                if (
                    index + 2 < len(line)
                    and line[index + 1] in "0123456789abcdefABCDEF"
                    and line[index + 2] in "0123456789abcdefABCDEF"
                ):
                    result[index + 1] = result[index + 2] = " "
                    index += 3
                else:
                    if index + 1 < len(line):
                        result[index + 1] = " "
                    index += 2
                continue
            if character == '"':
                quoted = False
        elif character == '"':
            quoted = True
            result[index] = " "
        index += 1
    return "".join(result)


def _parse_global_name(line: str, at: int) -> tuple[str, int] | None:
    index = at + 1
    if index >= len(line):
        return None
    if line[index] == '"':
        index += 1
        start = index
        while index < len(line):
            if line[index] == "\\":
                index += 3 if (
                    index + 2 < len(line)
                    and line[index + 1] in "0123456789abcdefABCDEF"
                    and line[index + 2] in "0123456789abcdefABCDEF"
                ) else 2
                continue
            if line[index] == '"':
                return _llvm_unescape(line[start:index]), index + 1
            index += 1
        return None
    match = re.match(r"[-a-zA-Z$._0-9]+", line[index:])
    if not match:
        return None
    return match.group(0), index + len(match.group(0))


def _direct_call(line: str) -> tuple[str, str] | None:
    """Return (opcode, callee) for a direct call/invoke, excluding decoys."""

    line = _strip_comment(line)
    lexical = _outside_quotes(line)
    opcode = _OPCODE_RE.search(lexical)
    if opcode is None:
        return None

    # A direct callee appears before the argument-list opening parenthesis.
    # Quoted global names are handled from the original line; quoted string
    # contents are invisible in ``lexical``.
    index = opcode.end()
    while index < len(line):
        if lexical[index] == "(":
            return None
        if lexical[index] == "@":
            parsed = _parse_global_name(line, index)
            if parsed is None:
                return None
            name, end = parsed
            while end < len(line) and line[end].isspace():
                end += 1
            if end < len(line) and line[end] == "(":
                return opcode.group("kind"), name
            return None
        index += 1
    return None


def _is_bounds_panic(name: str) -> bool:
    # This spelling is present in both legacy and v0 Rust manglings. Matching
    # only direct callees avoids comments, constants, and metadata strings.
    return "panic_bounds_check" in name


@dataclass(frozen=True)
class Function:
    name: str
    header: str
    body: tuple[tuple[int, str], ...]


def _parse_functions(ir: str) -> list[Function]:
    lines = [_strip_comment(line) for line in ir.splitlines()]
    if not any(line.strip() for line in lines):
        raise ValueError("input is empty or contains only LLVM comments")

    functions: list[Function] = []
    saw_module_construct = False
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if not _DEFINE_RE.match(line):
            if not _TOP_LEVEL_RE.match(line):
                raise ValueError(f"unrecognized top-level LLVM IR at line {index + 1}")
            saw_module_construct = True
            index += 1
            continue

        saw_module_construct = True
        start_line = index + 1
        header_parts = [line]
        while not header_parts[-1].rstrip().endswith("{"):
            index += 1
            if index >= len(lines):
                raise ValueError(
                    f"function definition at line {start_line} has no opening '{{'"
                )
            if _DEFINE_RE.match(lines[index]):
                raise ValueError(f"nested definition at line {index + 1}")
            header_parts.append(lines[index])
        header = " ".join(part.strip() for part in header_parts)
        name_match = _FUNCTION_NAME_RE.search(header)
        if name_match is None:
            raise ValueError(f"malformed function definition at line {start_line}")

        body: list[tuple[int, str]] = []
        index += 1
        while index < len(lines) and lines[index].strip() != "}":
            if _DEFINE_RE.match(lines[index]):
                raise ValueError(f"nested definition at line {index + 1}")
            body.append((index + 1, lines[index]))
            index += 1
        if index >= len(lines):
            raise ValueError(
                f"function {name_match.group('name')!r} from line {start_line} "
                "is missing closing '}'"
            )
        functions.append(
            Function(
                _llvm_unescape(name_match.group("name")), header, tuple(body)
            )
        )
        index += 1

    if not saw_module_construct:
        raise ValueError("input contains no recognizable LLVM IR")
    return functions


class DebugMetadata:
    def __init__(self, ir: str) -> None:
        self.nodes: dict[int, str] = {}
        for line in ir.splitlines():
            match = _METADATA_RE.match(_strip_comment(line))
            if match:
                self.nodes[int(match.group("id"))] = match.group("body")

    def _reference(self, node_id: int, field: str) -> int | None:
        match = re.search(
            rf"\b{re.escape(field)}:\s*!(?P<id>[0-9]+)",
            self.nodes.get(node_id, ""),
        )
        return int(match.group("id")) if match else None

    def _outermost(self, node_id: int) -> int:
        seen: set[int] = set()
        while node_id not in seen:
            seen.add(node_id)
            outer = self._reference(node_id, "inlinedAt")
            if outer is None:
                break
            node_id = outer
        return node_id

    def _file_node(self, node_id: int) -> int | None:
        pending = [node_id]
        seen: set[int] = set()
        while pending:
            current = pending.pop(0)
            if current in seen:
                continue
            seen.add(current)
            body = self.nodes.get(current, "")
            if "!DIFile(" in body:
                return current
            for field in ("file", "scope"):
                target = self._reference(current, field)
                if target is not None:
                    pending.append(target)
        return None

    def location(self, node_id: int, source_root: Path) -> dict[str, object] | None:
        node_id = self._outermost(node_id)
        body = self.nodes.get(node_id)
        if body is None:
            return None
        file_id = self._file_node(node_id)
        if file_id is None:
            return None
        file_body = self.nodes.get(file_id, "")
        filename = _FILENAME_RE.search(file_body)
        if filename is None:
            return None
        directory = _DIRECTORY_RE.search(file_body)
        file_path = Path(_llvm_unescape(filename.group("value")))
        if not file_path.is_absolute():
            base = Path(_llvm_unescape(directory.group("value"))) if directory else source_root
            file_path = base / file_path
        normalized = file_path.resolve(strict=False)
        root = source_root.resolve(strict=False)
        try:
            display_path = normalized.relative_to(root).as_posix()
            first_party = True
        except ValueError:
            display_path = normalized.as_posix()
            first_party = False

        line = _LINE_RE.search(body)
        column = _COLUMN_RE.search(body)
        result: dict[str, object] = {
            "path": display_path,
            "first_party": first_party,
        }
        if line:
            result["line"] = int(line.group("value"))
        if column:
            result["column"] = int(column.group("value"))
        return result


def _debug_location(
    line: str, metadata: DebugMetadata, source_root: Path
) -> dict[str, object] | None:
    match = _DBG_RE.search(_strip_comment(line))
    return metadata.location(int(match.group("id")), source_root) if match else None


def analyze_ir(ir: str, *, ir_file: str, source_root: Path) -> dict[str, object]:
    """Analyze one module. Structural parse failures raise ``ValueError``."""

    if "\x00" in ir:
        raise ValueError("input contains a NUL byte")
    functions = _parse_functions(ir)
    metadata = DebugMetadata(ir)
    candidates: list[dict[str, object]] = []
    unattributed: list[dict[str, object]] = []
    call_count = 0

    for function in functions:
        function_location = _debug_location(function.header, metadata, source_root)
        callsites: list[dict[str, object]] = []
        for llvm_line, line in function.body:
            direct = _direct_call(line)
            if direct is None or not _is_bounds_panic(direct[1]):
                continue
            call_count += 1
            callsite: dict[str, object] = {
                "kind": direct[0],
                "callee": direct[1],
                "llvm_line": llvm_line,
            }
            location = _debug_location(line, metadata, source_root)
            if location is not None:
                callsite["debug_location"] = location
            callsites.append(callsite)

        if not callsites:
            continue
        first_party_locations = [
            callsite["debug_location"]
            for callsite in callsites
            if isinstance(callsite.get("debug_location"), dict)
            and callsite["debug_location"].get("first_party") is True
        ]
        first_party = bool(first_party_locations) or (
            function_location is not None
            and function_location.get("first_party") is True
        )
        record: dict[str, object] = {
            "ir_file": ir_file,
            "function": function.name,
            "classification": CLASSIFICATION,
            "callsite_count": len(callsites),
            "callsites": callsites,
        }
        representative = (
            first_party_locations[0]
            if first_party_locations
            else function_location
        )
        if representative is not None:
            record["debug_location"] = representative
        (candidates if first_party else unattributed).append(record)

    return {
        "llvm_function_count": len(functions),
        "direct_panic_bounds_call_count": call_count,
        "candidates": candidates,
        "unattributed_hits": unattributed,
    }


def _input_files(inputs: Iterable[str]) -> list[Path]:
    files: dict[str, Path] = {}
    for raw in inputs:
        path = Path(raw)
        if not path.exists():
            raise ValueError(f"input does not exist: {path}")
        if path.is_dir():
            for child in path.rglob("*.ll"):
                if child.is_file():
                    files[child.resolve(strict=True).as_posix()] = child
        elif path.is_file() and path.suffix == ".ll":
            files[path.resolve(strict=True).as_posix()] = path
        else:
            raise ValueError(f"input is not a textual .ll file or directory: {path}")
    if not files:
        raise ValueError("inputs contain no textual .ll files")
    return [files[key] for key in sorted(files)]


def analyze_paths(inputs: Iterable[str], *, source_root: Path) -> dict[str, object]:
    root = source_root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"source root is not a directory: {source_root}")
    files = _input_files(inputs)
    candidates: list[dict[str, object]] = []
    unattributed: list[dict[str, object]] = []
    function_count = 0
    call_count = 0
    for path in files:
        try:
            ir = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise ValueError(f"cannot read UTF-8 LLVM IR {path}: {error}") from error
        result = analyze_ir(ir, ir_file=path.resolve().as_posix(), source_root=root)
        function_count += int(result["llvm_function_count"])
        call_count += int(result["direct_panic_bounds_call_count"])
        candidates.extend(result["candidates"])
        unattributed.extend(result["unattributed_hits"])

    return {
        "schema": SCHEMA,
        "classification": CLASSIFICATION,
        "source_root": root.as_posix(),
        "input_file_count": len(files),
        "llvm_function_count": function_count,
        "direct_panic_bounds_call_count": call_count,
        "first_party_candidate_count": len(candidates),
        "unattributed_hit_count": len(unattributed),
        "candidates": candidates,
        "unattributed_hits": unattributed,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="textual .ll files or directories")
    parser.add_argument(
        "--source-root",
        required=True,
        type=Path,
        help="project root used to classify first-party debug locations",
    )
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = analyze_paths(args.inputs, source_root=args.source_root)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    json.dump(
        result,
        sys.stdout,
        indent=2 if args.pretty else None,
        sort_keys=True,
        separators=None if args.pretty else (",", ":"),
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
