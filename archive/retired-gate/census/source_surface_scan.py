"""Lexical declaration and reservation-surface scanning for the census."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Sequence

from census_support import CensusError


TYPEID = re.compile(r"[A-Z][A-Za-z0-9]*\Z")
LOWER_NAME = re.compile(r"[a-z][a-z0-9_]*\Z")


@dataclass(frozen=True)
class Token:
    text: str
    kind: str
    byte_start: int
    line: int


@dataclass(frozen=True)
class Declaration:
    namespace: str
    kind: str
    spelling: str
    line: int
    byte_start: int


@dataclass(frozen=True)
class GenericDeclaration:
    spelling: str
    line: int
    byte_start: int
    owner_kind: str
    owner_spelling: str
    owner_line: int
    owner_byte_start: int


def scan_tokens(raw: bytes, label: str) -> list[Token]:
    """Scan only the ASCII name/punctuation facts needed by this census."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CensusError(f"{label} is not UTF-8: {error}") from error
    tokens: list[Token] = []
    index = 0
    byte_offset = 0
    line = 1
    while index < len(text):
        char = text[index]
        width = len(char.encode("utf-8"))
        if char == "\n":
            line += 1
            index += 1
            byte_offset += width
            continue
        if char.isspace():
            index += 1
            byte_offset += width
            continue
        if char == '"':
            index += 1
            byte_offset += 1
            escaped = False
            while index < len(text):
                current = text[index]
                current_width = len(current.encode("utf-8"))
                index += 1
                byte_offset += current_width
                if current == "\n":
                    line += 1
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    break
            else:
                raise CensusError(f"{label} contains an unterminated string")
            continue
        if char in "'@" and index + 1 < len(text) and text[index + 1].islower():
            start_index = index
            start_byte = byte_offset
            start_line = line
            index += 2
            byte_offset += 2
            while index < len(text) and (
                text[index].islower() or text[index].isdigit() or text[index] == "_"
            ):
                index += 1
                byte_offset += 1
            kind = "region" if char == "'" else "label"
            tokens.append(Token(text[start_index:index], kind, start_byte, start_line))
            continue
        if char.isascii() and char.isalpha():
            start_index = index
            start_byte = byte_offset
            start_line = line
            index += 1
            byte_offset += 1
            while index < len(text) and (
                text[index].isascii()
                and (text[index].isalnum() or text[index] == "_")
            ):
                index += 1
                byte_offset += 1
            word = text[start_index:index]
            kind = "typeid" if TYPEID.fullmatch(word) else "word"
            tokens.append(Token(word, kind, start_byte, start_line))
            continue
        tokens.append(Token(char, "punctuation", byte_offset, line))
        index += 1
        byte_offset += width
    return tokens


def _matching_brace(tokens: Sequence[Token], opening: int) -> int | None:
    depth = 0
    for index in range(opening, len(tokens)):
        if tokens[index].text == "{":
            depth += 1
        elif tokens[index].text == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def declarations(
    tokens: Sequence[Token],
) -> tuple[list[Declaration], list[GenericDeclaration]]:
    found: list[Declaration] = []
    type_generics: list[GenericDeclaration] = []
    index = 0
    brace_depth = 0
    while index < len(tokens):
        token = tokens[index]
        if token.text == "{":
            brace_depth += 1
            index += 1
            continue
        if token.text == "}":
            brace_depth = max(0, brace_depth - 1)
            index += 1
            continue
        if brace_depth != 0 or token.text not in {"struct", "enum", "contract", "fn"}:
            index += 1
            continue
        if index + 1 >= len(tokens):
            index += 1
            continue
        name = tokens[index + 1]
        if token.text in {"struct", "enum", "contract"} and name.kind != "typeid":
            index += 1
            continue
        if token.text == "fn" and not LOWER_NAME.fullmatch(name.text):
            index += 1
            continue
        if token.text in {"struct", "enum"}:
            found.append(
                Declaration("nominal", token.text, name.text, name.line, name.byte_start)
            )
        if token.text == "struct":
            found.append(
                Declaration(
                    "constructor",
                    "struct-constructor",
                    name.text,
                    name.line,
                    name.byte_start,
                )
            )
        if token.text == "contract":
            found.append(
                Declaration("contract", "contract", name.text, name.line, name.byte_start)
            )

        cursor = index + 2
        if cursor < len(tokens) and tokens[cursor].text == "<":
            generic_depth = 1
            at_entry_start = True
            cursor += 1
            while cursor < len(tokens) and generic_depth:
                current = tokens[cursor]
                if current.text == "<":
                    generic_depth += 1
                elif current.text == ">":
                    generic_depth -= 1
                elif generic_depth == 1 and current.text == ",":
                    at_entry_start = True
                elif generic_depth == 1 and at_entry_start:
                    if current.text == "const":
                        at_entry_start = False
                    elif current.kind == "typeid":
                        type_generics.append(
                            GenericDeclaration(
                                spelling=current.text,
                                line=current.line,
                                byte_start=current.byte_start,
                                owner_kind=token.text,
                                owner_spelling=name.text,
                                owner_line=name.line,
                                owner_byte_start=name.byte_start,
                            )
                        )
                        at_entry_start = False
                    elif current.text not in {":", "[", "]"}:
                        at_entry_start = False
                cursor += 1

        if token.text == "enum":
            opening = next(
                (position for position in range(index + 2, len(tokens)) if tokens[position].text == "{"),
                None,
            )
            if opening is not None:
                closing = _matching_brace(tokens, opening)
                if closing is not None:
                    local_depth = 1
                    for position in range(opening + 1, closing):
                        current = tokens[position]
                        if current.text in {"{", "(", "[", "<"}:
                            local_depth += 1
                        elif current.text in {"}", ")", "]", ">"}:
                            local_depth -= 1
                        elif (
                            local_depth == 1
                            and current.kind == "typeid"
                            and position + 1 < closing
                            and tokens[position + 1].text == "("
                        ):
                            found.append(
                                Declaration(
                                    "constructor",
                                    "enum-variant",
                                    current.text,
                                    current.line,
                                    current.byte_start,
                                )
                            )
                    index = closing + 1
                    continue
        index += 1
    return found, type_generics


def generic_shadow_collisions(
    path: str,
    declarations_in_file: Sequence[Declaration],
    generics: Sequence[GenericDeclaration],
    prelude_nominals: frozenset[str],
) -> list[dict[str, Any]]:
    """Find TYPE-6 generic redeclarations and shadows visible at each generic."""
    collisions: list[dict[str, Any]] = []
    by_owner: dict[tuple[str, str, int], set[str]] = {}
    source_nominals = [
        declaration
        for declaration in declarations_in_file
        if declaration.namespace == "nominal"
    ]
    for generic in generics:
        owner = (
            generic.owner_kind,
            generic.owner_spelling,
            generic.owner_byte_start,
        )
        prior = by_owner.setdefault(owner, set())
        reasons: list[str] = []
        if generic.spelling in prior:
            reasons.append("same-generic-list-redeclaration")
        if generic.spelling in prelude_nominals:
            reasons.append("prelude-nominal-shadow")
        if any(
            declaration.spelling == generic.spelling
            and declaration.byte_start < generic.byte_start
            for declaration in source_nominals
        ):
            reasons.append("live-source-nominal-shadow")
        if reasons:
            collisions.append(
                {
                    "line": generic.line,
                    "owner_kind": generic.owner_kind,
                    "owner_line": generic.owner_line,
                    "owner_spelling": generic.owner_spelling,
                    "path": path,
                    "reasons": reasons,
                    "spelling": generic.spelling,
                }
            )
        prior.add(generic.spelling)
    return collisions


def find_collisions(path: str, items: Sequence[Declaration]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[Declaration]] = {}
    for item in items:
        grouped.setdefault((item.namespace, item.spelling), []).append(item)
    collisions: list[dict[str, Any]] = []
    for (namespace, spelling), entries in sorted(grouped.items()):
        if len(entries) < 2:
            continue
        collisions.append(
            {
                "declarations": [
                    {"kind": entry.kind, "line": entry.line} for entry in entries
                ],
                "namespace": namespace,
                "path": path,
                "spelling": spelling,
            }
        )
    return collisions


def table_only_bindings(
    path: str,
    tokens: Sequence[Token],
    table_only: frozenset[str],
) -> list[dict[str, Any]]:
    """Conservatively flag every table-only name in a declaration-shaped role."""
    hits: list[dict[str, Any]] = []
    declaration_heads = {"fn", "const", "let", "region"}
    for index, token in enumerate(tokens):
        spelling = token.text[1:] if token.kind == "region" else token.text
        if spelling not in table_only:
            continue
        previous = tokens[index - 1].text if index else None
        following = tokens[index + 1].text if index + 1 < len(tokens) else None
        reasons: list[str] = []
        if token.kind == "region":
            reasons.append("region-body")
        if previous in declaration_heads:
            reasons.append(f"after-{previous}")
        if following == ":":
            reasons.append("before-colon")
        if previous == ":":
            reasons.append("after-colon")
        if reasons:
            hits.append(
                {
                    "line": token.line,
                    "path": path,
                    "reasons": reasons,
                    "spelling": spelling,
                }
            )
    return hits
