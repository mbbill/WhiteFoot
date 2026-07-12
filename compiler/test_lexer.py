#!/usr/bin/env python3
"""Compile the first self-hosted xlc component and compare it with stage 0."""

import ctypes
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "compiler"
sys.path[:0] = [str(ROOT / "prototype" / "democ"), str(ROOT / "prototype" / "checker")]

import democ


TOK_END = 0
TOK_WORD = 1
TOK_OP_NAME = 2
TOK_TYPE_ID = 3
TOK_REGION_ID = 4
TOK_LABEL = 5
TOK_NUMBER = 6
TOK_STRING = 7
TOK_ARROW = 8
TOK_FAT_ARROW = 9
TOK_AMP = 10
TOK_AMP_UNIQ = 11
TOK_SYMBOL = 12

LEX_CLEAN = 0
LEX_UNKNOWN_BYTE = 1
LEX_INVALID_STRING = 2
LEX_UNTERMINATED_STRING = 3
LEX_INVALID_REGION_ID = 4
LEX_INVALID_LABEL = 5
LEX_COMMENT = 6
LEX_CAPACITY = 7

KIND_POISON = 0x55555555
KIND_GUARD = 0x66666666
OFFSET_POISON = 0x7777777777777777
OFFSET_GUARD = 0x8888888888888888


class Buffer(ctypes.Structure):
    _fields_ = [("data", ctypes.c_void_p), ("length", ctypes.c_uint64)]


class TokenTape(ctypes.Structure):
    _fields_ = [
        ("kinds", Buffer),
        ("starts", Buffer),
        ("ends", Buffer),
        ("count", ctypes.c_uint64),
        ("status", ctypes.c_int32),
        ("error_start", ctypes.c_uint64),
        ("error_end", ctypes.c_uint64),
    ]


def compiler_source():
    paths = [HERE / line.strip() for line in (HERE / "sources.txt").read_text().splitlines()
             if line.strip()]
    return "\n\n".join(path.read_text().rstrip("\n") for path in paths) + "\n"


def build_library(directory):
    source = compiler_source()
    ir = democ.compile_program(source, alias=False)
    forbidden_facts = [marker for marker in (
        " noalias",
        " readonly",
        " dereferenceable(",
        " willreturn",
        "!alias.scope",
        "!noalias",
        " memory(",
    )
                       if marker in ir]
    if forbidden_facts:
        raise AssertionError(f"stage-0 safety boundary leaked optimizer facts: {forbidden_facts}")
    ll = directory / "lexer.ll"
    lib = directory / ("lexer.dylib" if sys.platform == "darwin" else "lexer.so")
    ll.write_text(ir)
    cc = "/usr/bin/clang" if Path("/usr/bin/clang").exists() else "clang"
    command = [cc, "-O2"]
    command += ["-dynamiclib"] if sys.platform == "darwin" else ["-shared", "-fPIC"]
    command += [str(ll), "-o", str(lib)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f"clang rejected self-hosted lexer IR:\n{result.stderr}")
    loaded = ctypes.CDLL(str(lib))
    loaded.lexer_run.argtypes = [Buffer, ctypes.POINTER(TokenTape)]
    loaded.lexer_run.restype = None
    return loaded


def run_lexer(library, data):
    capacity = len(data) + 1
    source_storage = (ctypes.c_uint8 * max(1, len(data)))()
    for index, byte in enumerate(data):
        source_storage[index] = byte
    kinds = (ctypes.c_int32 * capacity)()
    starts = (ctypes.c_uint64 * capacity)()
    ends = (ctypes.c_uint64 * capacity)()
    source = Buffer(ctypes.cast(source_storage, ctypes.c_void_p), len(data))
    tape = TokenTape(
        Buffer(ctypes.cast(kinds, ctypes.c_void_p), capacity),
        Buffer(ctypes.cast(starts, ctypes.c_void_p), capacity),
        Buffer(ctypes.cast(ends, ctypes.c_void_p), capacity),
        0,
        LEX_CLEAN,
        0,
        0,
    )
    library.lexer_run(source, ctypes.byref(tape))
    tokens = [(kinds[i], starts[i], ends[i]) for i in range(tape.count)]
    return tape.status, tape.error_start, tape.error_end, tokens


def run_lexer_with_capacities(library, data, capacities):
    kind_capacity, start_capacity, end_capacity = capacities
    source_storage = (ctypes.c_uint8 * max(1, len(data)))()
    for index, byte in enumerate(data):
        source_storage[index] = byte

    kinds = (ctypes.c_int32 * (kind_capacity + 1))()
    starts = (ctypes.c_uint64 * (start_capacity + 1))()
    ends = (ctypes.c_uint64 * (end_capacity + 1))()
    for index in range(kind_capacity):
        kinds[index] = KIND_POISON
    for index in range(start_capacity):
        starts[index] = OFFSET_POISON
    for index in range(end_capacity):
        ends[index] = OFFSET_POISON
    kinds[kind_capacity] = KIND_GUARD
    starts[start_capacity] = OFFSET_GUARD
    ends[end_capacity] = OFFSET_GUARD

    source = Buffer(ctypes.cast(source_storage, ctypes.c_void_p), len(data))
    tape = TokenTape(
        Buffer(ctypes.cast(kinds, ctypes.c_void_p), kind_capacity),
        Buffer(ctypes.cast(starts, ctypes.c_void_p), start_capacity),
        Buffer(ctypes.cast(ends, ctypes.c_void_p), end_capacity),
        0,
        LEX_CLEAN,
        0,
        0,
    )
    library.lexer_run(source, ctypes.byref(tape))

    guards = (kinds[kind_capacity], starts[start_capacity], ends[end_capacity])
    expected_guards = (KIND_GUARD, OFFSET_GUARD, OFFSET_GUARD)
    if guards != expected_guards:
        raise AssertionError(
            f"lexer wrote beyond advertised capacities {capacities}: "
            f"expected guards={expected_guards} observed={guards}"
        )
    maximum_count = min(capacities)
    if tape.count > maximum_count:
        raise AssertionError(
            f"lexer count exceeds capacities {capacities}: count={tape.count}"
        )

    tokens = [(kinds[i], starts[i], ends[i]) for i in range(tape.count)]
    columns = (
        list(kinds[:kind_capacity]),
        list(starts[:start_capacity]),
        list(ends[:end_capacity]),
    )
    return tape.status, tape.error_start, tape.error_end, tape.count, tokens, columns


def kind_of_stage0_token(token):
    if token.startswith('"'):
        return TOK_STRING
    if token.startswith("'"):
        return TOK_REGION_ID
    if token.startswith("@"):
        return TOK_LABEL
    if token == "->":
        return TOK_ARROW
    if token == "=>":
        return TOK_FAT_ARROW
    if token == "&uniq":
        return TOK_AMP_UNIQ
    if token == "&":
        return TOK_AMP
    if democ.LIT_RE.fullmatch(token) or re.fullmatch(r"[0-9]+", token):
        return TOK_NUMBER
    if re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*", token):
        return TOK_WORD
    if re.fullmatch(r"[A-Z][A-Za-z0-9]*", token):
        return TOK_TYPE_ID
    return TOK_SYMBOL


def expand_stage0_word(token, start):
    """Apply the closed OPNAME rule to stage 0's obsolete dotted-word token."""
    modes = {"wrap", "trap", "checked", "sat", "strict"}
    expected = []
    cursor = 0
    while cursor < len(token):
        match = re.match(r"[a-z][a-z0-9_]*", token[cursor:])
        if match is None:
            raise AssertionError(f"bad stage-0 dotted word {token!r}")
        word_end = cursor + len(match.group(0))
        suffix = None
        if word_end < len(token) and token[word_end] == ".":
            tail = re.match(r"[a-z][a-z0-9_]*", token[word_end + 1:])
            if tail is not None and tail.group(0) in modes:
                suffix = word_end + 1 + len(tail.group(0))
        if suffix is not None:
            expected.append((TOK_OP_NAME, start + cursor, start + suffix))
            cursor = suffix
        else:
            expected.append((TOK_WORD, start + cursor, start + word_end))
            cursor = word_end
        if cursor < len(token):
            expected.append((TOK_SYMBOL, start + cursor, start + cursor + 1))
            cursor += 1
    return expected


def stage0_tokens(path):
    data = path.read_bytes()
    if not data.isascii():
        return None
    text = data.decode("ascii")
    expected = []
    for match in democ.TOK.finditer(text):
        if match.group(1) is not None:
            return None
        token = match.group(0)
        if "." in token and re.fullmatch(
                r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+", token):
            expected.extend(expand_stage0_word(token, match.start()))
        else:
            expected.append((kind_of_stage0_token(token), match.start(), match.end()))
    expected.append((TOK_END, len(data), len(data)))
    return data, expected


def corpus_paths():
    roots = [
        ROOT / "conformance" / "cases",
        ROOT / "codegen-corpus" / "cases",
        ROOT / "m3" / "submissions" / "reference" / "xlang",
        ROOT / "experiments" / "port-study",
        ROOT / "prototype" / "democ" / "examples",
        ROOT / "compiler",
    ]
    paths = set()
    for root in roots:
        if root.exists():
            paths.update(root.rglob("*.xl"))
    return sorted(paths)


def main():
    with tempfile.TemporaryDirectory() as raw_directory:
        library = build_library(Path(raw_directory))

        compared = 0
        skipped_paths = []
        failures = []
        for path in corpus_paths():
            oracle = stage0_tokens(path)
            if oracle is None:
                skipped_paths.append(str(path.relative_to(ROOT)))
                continue
            data, expected = oracle
            status, error_start, error_end, observed = run_lexer(library, data)
            if status != LEX_CLEAN or observed != expected:
                failures.append(
                    f"{path.relative_to(ROOT)}: status={status} "
                    f"error=[{error_start},{error_end})\n"
                    f"  expected={expected[:12]}\n  observed={observed[:12]}"
                )
            compared += 1

        diagnostic_cases = {
            b"#": (LEX_UNKNOWN_BYTE, 0, 1),
            b"\x01": (LEX_UNKNOWN_BYTE, 0, 1),
            b'"unterminated': (LEX_UNTERMINATED_STRING, 0, 13),
            b'"\\t"': (LEX_INVALID_STRING, 1, 3),
            b'"\n"': (LEX_INVALID_STRING, 1, 2),
            b"'": (LEX_INVALID_REGION_ID, 0, 1),
            b"'1": (LEX_INVALID_REGION_ID, 0, 2),
            b"@": (LEX_INVALID_LABEL, 0, 1),
            b"@A": (LEX_INVALID_LABEL, 0, 2),
            b"// comment": (LEX_COMMENT, 0, 2),
            b"/* comment */": (LEX_COMMENT, 0, 2),
            b'"\x80"': (LEX_INVALID_STRING, 1, 2),
        }
        for data, expected in diagnostic_cases.items():
            status, error_start, error_end, _ = run_lexer(library, data)
            observed = (status, error_start, error_end)
            if observed != expected:
                failures.append(f"diagnostic {data!r}: expected={expected} observed={observed}")

        direct_cases = {
            b"": [(TOK_END, 0, 0)],
            b"foo.bar": [
                (TOK_WORD, 0, 3),
                (TOK_SYMBOL, 3, 4),
                (TOK_WORD, 4, 7),
                (TOK_END, 7, 7),
            ],
            b"foo.": [(TOK_WORD, 0, 3), (TOK_SYMBOL, 3, 4), (TOK_END, 4, 4)],
            b"value.trap": [(TOK_OP_NAME, 0, 10), (TOK_END, 10, 10)],
            b"iadd.trap": [(TOK_OP_NAME, 0, 9), (TOK_END, 9, 9)],
            b"&uniq 'r & @loop": [
                (TOK_AMP_UNIQ, 0, 5),
                (TOK_REGION_ID, 6, 8),
                (TOK_AMP, 9, 10),
                (TOK_LABEL, 11, 16),
                (TOK_END, 16, 16),
            ],
            b"-1_i64 0_T 1.5_f64": [
                (TOK_NUMBER, 0, 6),
                (TOK_NUMBER, 7, 10),
                (TOK_NUMBER, 11, 18),
                (TOK_END, 18, 18),
            ],
            b'"a\\\"b"': [(TOK_STRING, 0, 6), (TOK_END, 6, 6)],
        }
        for data, expected in direct_cases.items():
            status, error_start, error_end, observed = run_lexer(library, data)
            if status != LEX_CLEAN or observed != expected:
                failures.append(
                    f"direct case {data!r}: status={status} "
                    f"error=[{error_start},{error_end}); "
                    f"expected={expected} observed={observed}"
                )

        capacity_cases = [
            (b"fn", (0, 0, 0), (LEX_CAPACITY, 0, 2, 0, [])),
            (b"", (0, 0, 0), (LEX_CAPACITY, 0, 0, 0, [])),
            (b"fn main", (1, 1, 1),
             (LEX_CAPACITY, 3, 7, 1, [(TOK_WORD, 0, 2)])),
            (b"fn", (1, 1, 1),
             (LEX_CAPACITY, 2, 2, 1, [(TOK_WORD, 0, 2)])),
        ]
        for data, capacities, expected in capacity_cases:
            result = run_lexer_with_capacities(library, data, capacities)
            observed = result[:5]
            if observed != expected:
                failures.append(
                    f"capacity case {data!r} capacities={capacities}: "
                    f"expected={expected} observed={observed}"
                )

        asymmetric = run_lexer_with_capacities(library, b"fn main", (2, 1, 2))
        asymmetric_expected = (LEX_CAPACITY, 3, 7, 1, [(TOK_WORD, 0, 2)])
        if asymmetric[:5] != asymmetric_expected:
            failures.append(
                "asymmetric capacity case (2, 1, 2): "
                f"expected={asymmetric_expected} observed={asymmetric[:5]}"
            )
        asymmetric_columns = asymmetric[5]
        if (asymmetric_columns[0][1] != KIND_POISON
                or asymmetric_columns[2][1] != OFFSET_POISON):
            failures.append(
                "asymmetric capacity failure partially wrote a token: "
                f"columns={asymmetric_columns}"
            )

        if compared < 200:
            failures.append(f"corpus discovery regression: compared only {compared} sources")
        expected_skips = {
            "conformance/cases/form4-neg-comment.xl",
            "conformance/cases/x-form-form4-block-comment.xl",
        }
        if set(skipped_paths) != expected_skips:
            failures.append(
                f"unaccounted lexical-oracle skips: expected={sorted(expected_skips)} "
                f"observed={sorted(skipped_paths)}"
            )
        if failures:
            raise AssertionError("self-hosted lexer parity failed:\n" + "\n".join(failures[:20]))
        print(f"self-hosted lexer: {compared} corpus sources match normalized stage 0; "
              f"{len(skipped_paths)} comment-negative sources separately covered; diagnostics pass")


if __name__ == "__main__":
    main()
