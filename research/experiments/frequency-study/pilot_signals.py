#!/usr/bin/env python3
"""Fast, deliberately approximate source signals for the Leg-A pilot.

This is a source triage tool, not a Rust parser.  Its findings are heuristic
candidates for manual inspection; they are never claims of a proven speedup.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable


SCHEMA = "whitefoot.frequency-study.pilot-signals.v1"
LABEL = "heuristic_candidate_not_proven_speedup"
EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        "benches",
        "examples",
        "generated",
        "node_modules",
        "target",
        "tests",
        "vendor",
    }
)

INDEX_LOOP = "index_loop_bounds_candidate"
SCOPED_ALIAS = "scoped_alias_candidate"
SATURATING_RECURRENCE = "serial_saturating_recurrence_candidate"
CHUNKS_EXACT = "expert_chunks_exact_control"
ITERATOR_ZIP = "expert_iterator_zip_control"
GET_UNCHECKED = "expert_get_unchecked_control"
CLASSES = (
    INDEX_LOOP,
    SCOPED_ALIAS,
    SATURATING_RECURRENCE,
    CHUNKS_EXACT,
    ITERATOR_ZIP,
    GET_UNCHECKED,
)


class ScanError(RuntimeError):
    """The scan could not establish a trustworthy source view."""


def _blanked(source: str, start: int, end: int) -> str:
    return "".join("\n" if char == "\n" else " " for char in source[start:end])


def _raw_string(source: str, start: int) -> int | None:
    """Return the end of a Rust raw string beginning at *start*, if any."""

    if start and (source[start - 1].isalnum() or source[start - 1] == "_"):
        return None
    prefix_length = 0
    for prefix in ("br", "cr", "r"):
        if source.startswith(prefix, start):
            prefix_length = len(prefix)
            break
    if not prefix_length:
        return None
    cursor = start + prefix_length
    while cursor < len(source) and source[cursor] == "#":
        cursor += 1
    if cursor >= len(source) or source[cursor] != '"':
        return None
    hashes = source[start + prefix_length : cursor]
    terminator = '"' + hashes
    end = source.find(terminator, cursor + 1)
    if end < 0:
        raise ScanError("unterminated raw string")
    return end + len(terminator)


def _quoted_string(source: str, quote: int) -> int:
    cursor = quote + 1
    while cursor < len(source):
        if source[cursor] == "\\":
            cursor += 2
        elif source[cursor] == '"':
            return cursor + 1
        else:
            cursor += 1
    raise ScanError("unterminated string literal")


def _char_literal(source: str, quote: int) -> int | None:
    """Recognize common Rust character literals without eating lifetimes."""

    cursor = quote + 1
    if cursor >= len(source) or source[cursor] in "\r\n'":
        return None
    if source[cursor] == "\\":
        cursor += 1
        if cursor >= len(source):
            return None
        if source[cursor] == "u" and cursor + 1 < len(source) and source[cursor + 1] == "{":
            close = source.find("}", cursor + 2)
            if close < 0:
                return None
            cursor = close + 1
        elif source[cursor] == "x":
            cursor += 3
        else:
            cursor += 1
    else:
        cursor += 1
    if cursor < len(source) and source[cursor] == "'":
        return cursor + 1
    return None


def strip_comments_and_literals(source: str) -> str:
    """Blank comments and literals while preserving byte offsets and lines."""

    if "\0" in source:
        raise ScanError("NUL byte in Rust source")
    output: list[str] = []
    cursor = 0
    while cursor < len(source):
        if source.startswith("//", cursor):
            end = source.find("\n", cursor + 2)
            if end < 0:
                end = len(source)
            output.append(_blanked(source, cursor, end))
            cursor = end
            continue
        if source.startswith("/*", cursor):
            start = cursor
            cursor += 2
            depth = 1
            while cursor < len(source) and depth:
                if source.startswith("/*", cursor):
                    depth += 1
                    cursor += 2
                elif source.startswith("*/", cursor):
                    depth -= 1
                    cursor += 2
                else:
                    cursor += 1
            if depth:
                raise ScanError("unterminated block comment")
            output.append(_blanked(source, start, cursor))
            continue
        raw_end = _raw_string(source, cursor)
        if raw_end is not None:
            output.append(_blanked(source, cursor, raw_end))
            cursor = raw_end
            continue
        quote = cursor
        if source[cursor] in "bc" and cursor + 1 < len(source) and source[cursor + 1] == '"':
            quote = cursor + 1
        if source[quote] == '"':
            end = _quoted_string(source, quote)
            output.append(_blanked(source, cursor, end))
            cursor = end
            continue
        char_quote = cursor
        if source[cursor] == "b" and cursor + 1 < len(source) and source[cursor + 1] == "'":
            char_quote = cursor + 1
        if source[char_quote] == "'":
            end = _char_literal(source, char_quote)
            if end is not None:
                output.append(_blanked(source, cursor, end))
                cursor = end
                continue
        output.append(source[cursor])
        cursor += 1
    cleaned = "".join(output)
    if len(cleaned) != len(source) or cleaned.count("\n") != source.count("\n"):
        raise AssertionError("source masking lost position information")
    return cleaned


def _closing_brace(code: str, opening: int) -> int:
    depth = 0
    for cursor in range(opening, len(code)):
        if code[cursor] == "{":
            depth += 1
        elif code[cursor] == "}":
            depth -= 1
            if depth == 0:
                return cursor
    raise ScanError(f"unclosed block beginning at byte {opening}")


_LOOP_PATTERNS = (
    # Requiring ``in`` keeps ``impl Trait for Type {`` out of the loop set.
    re.compile(r"\bfor\b[^{};]*\bin\b[^{};]*\{", re.DOTALL),
    re.compile(r"\bwhile\b[^{};]*\{", re.DOTALL),
    re.compile(r"\bloop\s*\{"),
)
_FOR_INDEX_RE = re.compile(
    r"\bfor\s+(?P<index>[A-Za-z_]\w*)\s+in\s+0(?:usize)?\s*\.\."
    r"(?![.=])\s*(?P<sequence>[A-Za-z_]\w*(?:\s*\.\s*[A-Za-z_]\w*)*)"
    r"\s*\.\s*len\s*\(\s*\)\s*\{",
    re.DOTALL,
)
_WHILE_INDEX_RE = re.compile(
    r"\bwhile\s+(?P<index>[A-Za-z_]\w*)\s*(?:<|!=)\s*"
    r"(?P<sequence>[A-Za-z_]\w*(?:\s*\.\s*[A-Za-z_]\w*)*)"
    r"\s*\.\s*len\s*\(\s*\)\s*\{",
    re.DOTALL,
)
_WHILE_REVERSED_RE = re.compile(
    r"\bwhile\s+(?P<sequence>[A-Za-z_]\w*(?:\s*\.\s*[A-Za-z_]\w*)*)"
    r"\s*\.\s*len\s*\(\s*\)\s*>\s*(?P<index>[A-Za-z_]\w*)\s*\{",
    re.DOTALL,
)
_FUNCTION_RE = re.compile(r"\bfn\s+(?P<name>(?:r#)?[A-Za-z_]\w*)[^;(]*\(", re.DOTALL)
_SLICE_PARAMETER_RE = re.compile(
    r"&\s*(?:'[A-Za-z_]\w*\s*)?(?:mut\s*)?\s*\["
)
_RECURRENCE_RE = re.compile(
    r"\b(?P<name>[A-Za-z_]\w*)\s*=\s*(?P=name)\s*\.\s*saturating_add\s*\("
)
_EXPERT_PATTERNS = (
    (CHUNKS_EXACT, re.compile(r"\.\s*chunks_exact(?:_mut)?\s*\("), "chunks_exact chunk iteration"),
    (ITERATOR_ZIP, re.compile(r"\.\s*zip\s*\("), "iterator zip"),
    (GET_UNCHECKED, re.compile(r"\.\s*get_unchecked(?:_mut)?\s*\("), "unchecked indexed access"),
)


def _loops(code: str) -> list[tuple[int, int, int]]:
    loops: list[tuple[int, int, int]] = []
    for pattern in _LOOP_PATTERNS:
        for match in pattern.finditer(code):
            opening = match.end() - 1
            loops.append((match.start(), opening, _closing_brace(code, opening)))
    return sorted(set(loops))


def _matching_parenthesis(code: str, opening: int) -> int:
    depth = 0
    for cursor in range(opening, len(code)):
        if code[cursor] == "(":
            depth += 1
        elif code[cursor] == ")":
            depth -= 1
            if depth == 0:
                return cursor
    raise ScanError(f"unclosed parameter list beginning at byte {opening}")


def _line_and_snippet(source: str, position: int) -> tuple[int, str]:
    line = source.count("\n", 0, position) + 1
    start = source.rfind("\n", 0, position) + 1
    end = source.find("\n", position)
    if end < 0:
        end = len(source)
    snippet = " ".join(source[start:end].strip().split())
    if len(snippet) > 200:
        snippet = snippet[:197] + "..."
    return line, snippet


def analyze_source(source: str, file_name: str) -> list[dict[str, object]]:
    """Return source candidates for one UTF-8 Rust file."""

    code = strip_comments_and_literals(source)
    loops = _loops(code)
    records: list[dict[str, object]] = []
    seen: set[tuple[str, int]] = set()

    def add(class_name: str, position: int, reason: str) -> None:
        key = (class_name, position)
        if key in seen:
            return
        seen.add(key)
        line, snippet = _line_and_snippet(source, position)
        records.append(
            {
                "class": class_name,
                "file": file_name,
                "label": LABEL,
                "line": line,
                "proven_speedup": False,
                "reason": reason,
                "snippet": snippet,
            }
        )

    for pattern, shape in (
        (_FOR_INDEX_RE, "range length guard"),
        (_WHILE_INDEX_RE, "while length guard"),
        (_WHILE_REVERSED_RE, "reversed while length guard"),
    ):
        for match in pattern.finditer(code):
            opening = match.end() - 1
            closing = _closing_brace(code, opening)
            index = match.group("index")
            if re.search(r"\[\s*" + re.escape(index) + r"\s*\]", code[opening + 1 : closing]):
                add(
                    INDEX_LOOP,
                    match.start(),
                    f"{shape} and [{index}] access occur in the same loop",
                )

    for function in _FUNCTION_RE.finditer(code):
        opening_parenthesis = function.end() - 1
        closing_parenthesis = _matching_parenthesis(code, opening_parenthesis)
        parameters = code[opening_parenthesis + 1 : closing_parenthesis]
        slice_count = len(_SLICE_PARAMETER_RE.findall(parameters))
        if slice_count < 2:
            continue
        tail = re.search(r"[;{]", code[closing_parenthesis + 1 :])
        if tail is None or tail.group() == ";":
            continue
        body_open = closing_parenthesis + 1 + tail.start()
        body_close = _closing_brace(code, body_open)
        if any(body_open < loop_start < body_close for loop_start, _, _ in loops):
            add(
                SCOPED_ALIAS,
                function.start(),
                f"function {function.group('name')} has {slice_count} direct slice parameters and a loop",
            )

    for match in _RECURRENCE_RE.finditer(code):
        if not any(opening < match.start() < closing for _, opening, closing in loops):
            continue
        statement_start = max(
            code.rfind(";", 0, match.start()),
            code.rfind("{", 0, match.start()),
            code.rfind("}", 0, match.start()),
        )
        prefix = code[statement_start + 1 : match.start()]
        if re.search(r"\blet(?:\s+mut)?\s*$", prefix):
            continue
        add(
            SATURATING_RECURRENCE,
            match.start(),
            f"{match.group('name')} is assigned from its own saturating_add inside a loop",
        )

    for class_name, pattern, description in _EXPERT_PATTERNS:
        for match in pattern.finditer(code):
            add(
                class_name,
                match.start(),
                f"source already uses {description}; this is a control/expert shape",
            )

    records.sort(key=lambda item: (str(item["file"]), int(item["line"]), str(item["class"]), str(item["snippet"])))
    return records


def _source_files(root: Path) -> tuple[Path, list[Path]]:
    try:
        resolved = root.resolve(strict=True)
    except OSError as error:
        raise ScanError(f"cannot resolve input {root}: {error}") from error
    if resolved.is_file():
        if resolved.suffix != ".rs":
            raise ScanError(f"input file is not Rust source: {root}")
        return resolved.parent, [resolved]
    if not resolved.is_dir():
        raise ScanError(f"input is neither a file nor directory: {root}")

    files: list[Path] = []

    def walk_error(error: OSError) -> None:
        raise ScanError(f"cannot traverse input {root}: {error}") from error

    input_is_src = resolved.name == "src"
    for directory, names, file_names in os.walk(resolved, onerror=walk_error):
        names[:] = sorted(name for name in names if name not in EXCLUDED_DIRECTORIES)
        base = Path(directory)
        relative_parts = base.relative_to(resolved).parts
        in_production_src = input_is_src or "src" in relative_parts
        if in_production_src:
            files.extend(base / name for name in sorted(file_names) if name.endswith(".rs"))
    if not files:
        raise ScanError(f"no Rust source files under {root}")
    return resolved, files


def scan_project(root: str | Path) -> dict[str, object]:
    """Scan a Rust source file or tree and return deterministic JSON data."""

    display_root, files = _source_files(Path(root))
    records: list[dict[str, object]] = []
    line_count = 0
    for path in files:
        relative = path.relative_to(display_root).as_posix()
        try:
            source = path.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeError) as error:
            raise ScanError(f"cannot read UTF-8 Rust source {relative}: {error}") from error
        line_count += source.count("\n") + (1 if source else 0)
        try:
            records.extend(analyze_source(source, relative))
        except ScanError as error:
            raise ScanError(f"cannot safely scan {relative}: {error}") from error
    records.sort(key=lambda item: (str(item["file"]), int(item["line"]), str(item["class"]), str(item["snippet"])))
    counts = Counter(str(record["class"]) for record in records)
    return {
        "candidate_count": len(records),
        "counts_by_class": {class_name: counts[class_name] for class_name in CLASSES},
        "interpretation": {
            "label": LABEL,
            "proven_speedups": False,
            "statement": "Source-only heuristic candidates for manual triage, not proven optimization opportunities or speedups.",
        },
        "records": records,
        "rust_file_count": len(files),
        "scan_scope": {
            "included": "production src/**/*.rs only (including workspace members)",
            "excluded_directory_names": sorted(EXCLUDED_DIRECTORIES),
        },
        "schema": SCHEMA,
        "source_line_count": line_count,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", help="Rust source file or project directory")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        result = scan_project(arguments.root)
    except ScanError as error:
        print(f"pilot_signals: error: {error}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
