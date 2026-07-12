#!/usr/bin/env python3
"""Classify conservative LLVM call-site effect-attribute visibility gaps.

This is an optimized-IR calibration tool, not a profiler.  For each direct call
through a declaration, it joins declaration and call-site facts, then compares
that effective view with the same-named definition in another captured module.
Unsupported syntax is reported separately and can never become a positive gap.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


SCHEMA = 3
SCOPE = "optimized-ir-callsite-effect-attribute-gap-calibration-v3"
MEMORY_LOCATIONS = ("argmem", "inaccessiblemem", "errnomem", "other")
ACCESS_BITS = {"none": 0, "read": 1, "write": 2, "readwrite": 3}
BITS_ACCESS = {value: key for key, value in ACCESS_BITS.items()}
LOCAL_LINKAGES = {"private", "internal"}
NON_EMITTING_DEFINITION_LINKAGES = {"available_externally"}
LINKAGES = {
    "private",
    "internal",
    "available_externally",
    "linkonce",
    "weak",
    "common",
    "appending",
    "extern_weak",
    "linkonce_odr",
    "weak_odr",
    "external",
}
DISPOSITIONS = (
    "strong-total-pure-gap",
    "read-only-total-gap",
    "already-visible",
    "caller-facts-unsupported",
    "definition-ineligible",
    "definition-facts-unsupported",
    "unresolved-definition",
    "ambiguous-definition",
    "linkage-incompatible",
    "abi-unsupported",
    "abi-mismatch",
)


class ParseError(ValueError):
    """The input looked like LLVM IR but could not be classified safely."""


@dataclass(frozen=True)
class MemoryEffects:
    state: str
    locations: tuple[tuple[str, str], ...] = ()
    reason: str | None = None

    @classmethod
    def absent(cls) -> "MemoryEffects":
        return cls("absent")

    @classmethod
    def unsupported(cls, reason: str) -> "MemoryEffects":
        return cls("unsupported", reason=reason)

    @classmethod
    def known(cls, accesses: dict[str, int]) -> "MemoryEffects":
        normalized = tuple(
            (location, BITS_ACCESS[accesses[location]])
            for location in MEMORY_LOCATIONS
        )
        return cls("known", normalized)

    def access_bits(self) -> dict[str, int]:
        if self.state != "known":
            raise ValueError("memory effects are not known")
        return {location: ACCESS_BITS[access] for location, access in self.locations}

    def summary(self) -> str:
        if self.state != "known":
            return self.state
        combined = 0
        for value in self.access_bits().values():
            combined |= value
        if combined == 0:
            return "none"
        if combined & ACCESS_BITS["write"]:
            return "may-write"
        return "read-only"

    def as_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "summary": self.summary(),
            "locations": dict(self.locations) if self.state == "known" else None,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class EffectFacts:
    memory: MemoryEffects
    nounwind: bool
    willreturn: bool
    speculatable: bool

    def tier(self) -> str | None:
        # `speculatable` is deliberately not treated as `willreturn`.  The
        # channel being calibrated emits a separate willreturn proof.
        if not self.nounwind or not self.willreturn or self.memory.state != "known":
            return None
        summary = self.memory.summary()
        if summary == "none":
            return "strong-total-pure"
        if summary == "read-only":
            return "read-only-total"
        return None

    def as_dict(self) -> dict[str, object]:
        return {
            "memory": self.memory.as_dict(),
            "nounwind": self.nounwind,
            "willreturn": self.willreturn,
            "speculatable": self.speculatable,
            "tier": self.tier(),
        }


@dataclass(frozen=True)
class ABISignature:
    state: str
    return_type: str | None = None
    parameters: tuple[str, ...] = ()
    vararg: bool = False
    calling_convention: str | None = None
    address_space: int | None = None
    reason: str | None = None

    @classmethod
    def unsupported(cls, reason: str) -> "ABISignature":
        return cls("unsupported", reason=reason)

    def as_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "return_type": self.return_type,
            "parameters": list(self.parameters),
            "vararg": self.vararg,
            "calling_convention": self.calling_convention,
            "address_space": self.address_space,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class FunctionRecord:
    module: str
    symbol: str
    kind: str
    linkage: str
    facts: EffectFacts
    abi: ABISignature


@dataclass(frozen=True)
class CallSite:
    module: str
    caller: str
    line: int
    ordinal: int
    symbol: str | None
    facts: EffectFacts
    abi: ABISignature
    unsupported_reason: str | None = None


@dataclass(frozen=True)
class Module:
    path: str
    functions: tuple[FunctionRecord, ...]
    calls: tuple[CallSite, ...]


@dataclass(frozen=True)
class _FunctionEntry:
    kind: str
    header: str
    line: int
    body: tuple[tuple[int, str], ...]


_FUNCTION_START = re.compile(r"^\s*(define|declare)\b")
_FUNCTION_END = re.compile(r"^\s*}\s*(?:;.*)?$")
_MODULE_MARKER = re.compile(
    r"^\s*(?:source_filename\s*=|target\s+(?:datalayout|triple)\s*=)", re.M
)
_TOP_LEVEL_START = re.compile(
    r"^(?:define\b|declare\b|attributes\b|source_filename\b|target\b|"
    r"module\s+asm\b|uselistorder(?:_bb)?\b|[!@%$])"
)
_CALL_WORD = re.compile(r"(?<![-A-Za-z$._0-9])(callbr|invoke|call)(?![-A-Za-z$._0-9])")
_SYMBOL = re.compile(
    r'@(?P<symbol>"(?:\\.|[^"\\])*"|[-A-Za-z$._][-A-Za-z$._0-9]*)\s*\('
)
_GROUP_START = re.compile(r"\battributes\s+#(?P<id>[0-9]+)\s*=\s*\{")
_GROUP_REF = re.compile(r"(?<![-A-Za-z$._0-9])#([0-9]+)\b")
_MEMORY_WORD = re.compile(r"(?<![-A-Za-z$._0-9])memory(?![-A-Za-z$._0-9])")
_SIGILED_IDENTIFIER = re.compile(
    r"[!%@](?:[-A-Za-z$._][-A-Za-z$._0-9]*|[0-9]+)"
)
_INLINE_ASM = re.compile(
    r"(?<![-A-Za-z$._0-9@%$!])asm(?![-A-Za-z$._0-9])"
)
_CALLING_CONVENTIONS = (
    "ccc",
    "fastcc",
    "coldcc",
    "cfguard_checkcc",
    "anyregcc",
    "preserve_mostcc",
    "preserve_allcc",
    "preserve_nonecc",
    "cxx_fast_tlscc",
    "tailcc",
    "swiftcc",
    "swifttailcc",
    "ghccc",
    "webkit_jscc",
)
_PRIMITIVE_TYPES = {
    "void",
    "half",
    "bfloat",
    "float",
    "double",
    "fp128",
    "x86_fp80",
    "ppc_fp128",
    "label",
    "metadata",
    "x86_mmx",
    "token",
}
_CALLSITE_ATTRIBUTE_NAMES = {
    "alignstack",
    "allocsize",
    "alwaysinline",
    "argmemonly",
    "builtin",
    "cold",
    "convergent",
    "disable_sanitizer_instrumentation",
    "fn_ret_thunk_extern",
    "hot",
    "inaccessiblemem_or_argmemonly",
    "inaccessiblememonly",
    "inlinehint",
    "jumptable",
    "memory",
    "minsize",
    "mustprogress",
    "naked",
    "nobuiltin",
    "nocallback",
    "nocf_check",
    "noduplicate",
    "nofree",
    "noimplicitfloat",
    "noinline",
    "nomerge",
    "nonlazybind",
    "noprofile",
    "norecurse",
    "noredzone",
    "noreturn",
    "nosync",
    "nounwind",
    "null_pointer_is_valid",
    "optforfuzzing",
    "optnone",
    "optsize",
    "readnone",
    "readonly",
    "returns_twice",
    "safestack",
    "sanitize_address",
    "sanitize_hwaddress",
    "sanitize_memory",
    "sanitize_thread",
    "shadowcallstack",
    "speculatable",
    "ssp",
    "sspreq",
    "sspstrong",
    "strictfp",
    "uwtable",
    "vscale_range",
    "willreturn",
    "writeonly",
}


def _mask_quoted(text: str) -> str:
    """Replace arbitrary LLVM quoted strings while preserving byte positions."""
    out = list(text)
    quoted = False
    escaped = False
    start = -1
    for index, char in enumerate(text):
        if quoted:
            out[index] = "\n" if char == "\n" else " "
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '"':
            quoted = True
            start = index
            out[index] = " "
    if quoted:
        raise ParseError(f"unterminated quoted string at byte {start}")
    return "".join(out)


def _mask_comments(text: str) -> str:
    masked = list(text)
    quoted = False
    escaped = False
    index = 0
    while index < len(text):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            index += 1
            continue
        if char == '"':
            quoted = True
            index += 1
            continue
        if char == ";":
            while index < len(text) and text[index] != "\n":
                masked[index] = " "
                index += 1
            continue
        index += 1
    return "".join(masked)


def _mask_sigiled_identifiers(text: str) -> str:
    return _SIGILED_IDENTIFIER.sub(lambda match: " " * len(match.group(0)), text)


def _word(text: str, value: str) -> bool:
    pattern = rf"(?<![-A-Za-z$._0-9]){re.escape(value)}(?![-A-Za-z$._0-9])"
    return re.search(pattern, text) is not None


def _matching_delimiter(text: str, start: int, opening: str, closing: str) -> int | None:
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return index
            if depth < 0:
                return None
    return None


def _matching_paren(text: str, start: int) -> int | None:
    return _matching_delimiter(_mask_quoted(text), start, "(", ")")


def _attribute_groups(source: str, module: str) -> dict[str, str]:
    masked = _mask_quoted(_mask_comments(source))
    groups: dict[str, str] = {}
    position = 0
    while True:
        match = _GROUP_START.search(masked, position)
        if match is None:
            break
        group_id = match.group("id")
        if group_id in groups:
            raise ParseError(f"{module}: duplicate attribute group #{group_id}")
        opening = match.end() - 1
        closing = _matching_delimiter(masked, opening, "{", "}")
        if closing is None:
            raise ParseError(f"{module}: unterminated attribute group #{group_id}")
        groups[group_id] = source[opening + 1 : closing]
        position = closing + 1
    return groups


def _function_entries(source: str, module: str) -> list[_FunctionEntry]:
    lines = source.splitlines()
    entries: list[_FunctionEntry] = []
    index = 0
    while index < len(lines):
        start_match = _FUNCTION_START.match(lines[index])
        if start_match is None:
            index += 1
            continue
        kind = start_match.group(1)
        first_line = index + 1
        parts = [lines[index]]
        index += 1
        while True:
            header = "\n".join(parts)
            symbol = _SYMBOL.search(header)
            close = _matching_paren(header, symbol.end() - 1) if symbol else None
            if close is not None:
                break
            if index >= len(lines) or _FUNCTION_START.match(lines[index]):
                raise ParseError(
                    f"{module}: malformed {kind} header: {parts[0].strip()}"
                )
            parts.append(lines[index])
            index += 1

        body: list[tuple[int, str]] = []
        if kind == "define":
            while "{" not in _mask_quoted(header[close + 1 :]):
                if index >= len(lines):
                    raise ParseError(f"{module}: missing body opener at line {first_line}")
                parts.append(lines[index])
                index += 1
                header = "\n".join(parts)
            while index < len(lines) and not _FUNCTION_END.match(lines[index]):
                body.append((index + 1, lines[index]))
                index += 1
            if index >= len(lines):
                raise ParseError(f"{module}: unterminated function at line {first_line}")
            index += 1
        else:
            # LLVM treats newlines as whitespace.  rustc/LLVM normally prints
            # declarations on one line, but indented function attributes on
            # following lines are valid and must remain part of the header.
            while index < len(lines):
                continuation = lines[index]
                if not continuation.strip():
                    break
                continuation_code = _mask_comments(continuation).strip()
                if not continuation_code or _TOP_LEVEL_START.match(continuation_code):
                    break
                parts.append(continuation)
                index += 1
            header = "\n".join(parts)
        entries.append(_FunctionEntry(kind, header, first_line, tuple(body)))
    return entries


def _parse_modern_memory(spec: str) -> MemoryEffects:
    items = [item.strip() for item in spec.split(",")]
    if not items or any(not item for item in items):
        return MemoryEffects.unsupported("empty memory effect item")
    default: int | None = None
    overrides: dict[str, int] = {}
    for index, item in enumerate(items):
        if ":" not in item:
            if index != 0 or default is not None or item not in ACCESS_BITS:
                return MemoryEffects.unsupported(f"unsupported memory default: {item}")
            default = ACCESS_BITS[item]
            continue
        location, access = (part.strip() for part in item.split(":", 1))
        if location not in MEMORY_LOCATIONS:
            return MemoryEffects.unsupported(f"unsupported memory location: {location}")
        if access not in ACCESS_BITS:
            return MemoryEffects.unsupported(f"unsupported memory access: {access}")
        if location in overrides:
            return MemoryEffects.unsupported(f"duplicate memory location: {location}")
        overrides[location] = ACCESS_BITS[access]

    # In LLVM's location form, unmentioned locations are none.  An explicit
    # leading default (e.g. `read, argmem: none`) changes that base.
    base = ACCESS_BITS["none"] if default is None else default
    accesses = {location: overrides.get(location, base) for location in MEMORY_LOCATIONS}
    return MemoryEffects.known(accesses)


def _parse_legacy_memory(attrs: str) -> MemoryEffects:
    access_attrs = [name for name in ("readnone", "readonly", "writeonly") if _word(attrs, name)]
    restrictors = [
        name
        for name in ("argmemonly", "inaccessiblememonly", "inaccessiblemem_or_argmemonly")
        if _word(attrs, name)
    ]
    if len(access_attrs) > 1 or len(restrictors) > 1:
        return MemoryEffects.unsupported("conflicting legacy memory attributes")
    if not access_attrs and not restrictors:
        return MemoryEffects.absent()
    access_name = access_attrs[0] if access_attrs else "readwrite"
    access = {
        "readnone": ACCESS_BITS["none"],
        "readonly": ACCESS_BITS["read"],
        "writeonly": ACCESS_BITS["write"],
        "readwrite": ACCESS_BITS["readwrite"],
    }[access_name]
    if not restrictors:
        locations = set(MEMORY_LOCATIONS)
    elif restrictors[0] == "argmemonly":
        locations = {"argmem"}
    elif restrictors[0] == "inaccessiblememonly":
        locations = {"inaccessiblemem"}
    else:
        locations = {"argmem", "inaccessiblemem"}
    return MemoryEffects.known(
        {
            location: access if location in locations else ACCESS_BITS["none"]
            for location in MEMORY_LOCATIONS
        }
    )


def _memory_effects(attrs: str) -> MemoryEffects:
    clean = _mask_sigiled_identifiers(_mask_quoted(attrs))
    matches = list(_MEMORY_WORD.finditer(clean))
    legacy_present = any(
        _word(clean, name)
        for name in (
            "readnone",
            "readonly",
            "writeonly",
            "argmemonly",
            "inaccessiblememonly",
            "inaccessiblemem_or_argmemonly",
        )
    )
    if not matches:
        return _parse_legacy_memory(clean)
    if len(matches) != 1 or legacy_present:
        return MemoryEffects.unsupported("multiple or mixed memory attribute forms")
    start = matches[0].end()
    while start < len(clean) and clean[start].isspace():
        start += 1
    if start >= len(clean) or clean[start] != "(":
        return MemoryEffects.unsupported("memory attribute has no argument list")
    close = _matching_delimiter(clean, start, "(", ")")
    if close is None:
        return MemoryEffects.unsupported("unterminated memory attribute")
    return _parse_modern_memory(clean[start + 1 : close])


def _effect_facts(attrs: str) -> EffectFacts:
    clean = _mask_sigiled_identifiers(_mask_quoted(attrs))
    return EffectFacts(
        memory=_memory_effects(clean),
        nounwind=_word(clean, "nounwind"),
        willreturn=_word(clean, "willreturn"),
        speculatable=_word(clean, "speculatable"),
    )


def _attrs_from_suffix(suffix: str, groups: dict[str, str], context: str) -> EffectFacts:
    clean = _mask_quoted(suffix)
    attrs = [suffix]
    for group_id in _GROUP_REF.findall(clean):
        if group_id not in groups:
            raise ParseError(f"{context} references missing attribute group #{group_id}")
        attrs.append(groups[group_id])
    return _effect_facts(" ".join(attrs))


def _canonical_type(text: str) -> str:
    value = re.sub(r"\s+", " ", text.strip())
    value = re.sub(r"\s*([{},<>\[\]])\s*", r"\1", value)
    value = re.sub(r"addrspace\s*\(\s*([0-9]+)\s*\)", r"addrspace(\1)", value)
    return value


def _balanced_type_end(text: str, start: int) -> int | None:
    pairs = {"{": "}", "[": "]", "<": ">", "(": ")"}
    stack: list[str] = []
    quoted = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '"':
            quoted = True
        elif char in pairs:
            stack.append(pairs[char])
        elif char in pairs.values():
            if not stack or char != stack.pop():
                return None
            if not stack:
                return index
    return None


def _type_prefix(text: str) -> tuple[str, int] | None:
    leading = len(text) - len(text.lstrip())
    value = text[leading:]
    if not value:
        return None
    if value[0] in "{[<":
        end = _balanced_type_end(value, 0)
        if end is None:
            return None
        return _canonical_type(value[: end + 1]), leading + end + 1
    patterns = (
        r"ptr(?:\s+addrspace\s*\(\s*[0-9]+\s*\))?",
        r"i[0-9]+",
        r'%(?:"(?:\\.|[^"\\])*"|[-A-Za-z$._][-A-Za-z$._0-9]*)',
        r"(?:" + "|".join(sorted(_PRIMITIVE_TYPES, key=len, reverse=True)) + r")",
    )
    for pattern in patterns:
        match = re.match(pattern + r"(?![-A-Za-z$._0-9])", value)
        if match:
            return _canonical_type(match.group(0)), leading + match.end()
    return None


def _type_suffix(text: str) -> tuple[str, int] | None:
    value = text.rstrip()
    simple_patterns = (
        r"ptr(?:\s+addrspace\s*\(\s*[0-9]+\s*\))?",
        r"i[0-9]+",
        r'%(?:"(?:\\.|[^"\\])*"|[-A-Za-z$._][-A-Za-z$._0-9]*)',
        r"(?:" + "|".join(sorted(_PRIMITIVE_TYPES, key=len, reverse=True)) + r")",
    )
    for pattern in simple_patterns:
        match = re.search(r"(?<![-A-Za-z$._0-9])(" + pattern + r")$", value)
        if match:
            return _canonical_type(match.group(1)), match.start(1)
    for start, char in enumerate(value):
        if char not in "{[<":
            continue
        end = _balanced_type_end(value, start)
        if end == len(value) - 1:
            return _canonical_type(value[start : end + 1]), start
    return None


def _split_top_level(text: str) -> list[str] | None:
    pieces: list[str] = []
    start = 0
    stack: list[str] = []
    pairs = {"{": "}", "[": "]", "<": ">", "(": ")"}
    quoted = False
    escaped = False
    for index, char in enumerate(text):
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '"':
            quoted = True
        elif char in pairs:
            stack.append(pairs[char])
        elif char in pairs.values():
            if not stack or char != stack.pop():
                return None
        elif char == "," and not stack:
            pieces.append(text[start:index])
            start = index + 1
    if quoted or stack:
        return None
    pieces.append(text[start:])
    return pieces


def _parameter_signature(text: str, *, declaration: bool) -> tuple[tuple[str, ...], bool] | None:
    if not text.strip():
        return (), False
    pieces = _split_top_level(text)
    if pieces is None:
        return None
    parameters: list[str] = []
    vararg = False
    for index, piece in enumerate(pieces):
        if piece.strip() == "...":
            if not declaration or index != len(pieces) - 1:
                return None
            vararg = True
            continue
        parsed = _type_prefix(piece)
        if parsed is None:
            return None
        parameters.append(parsed[0])
    return tuple(parameters), vararg


def _calling_convention(prefix: str) -> tuple[str | None, str | None]:
    clean = _mask_sigiled_identifiers(_mask_quoted(prefix))
    found = [name for name in _CALLING_CONVENTIONS if _word(clean, name)]
    numeric = re.findall(r"(?<![-A-Za-z$._0-9])cc\s+([0-9]+)\b", clean)
    found.extend(f"cc {number}" for number in numeric)
    if len(found) > 1:
        return None, f"multiple calling conventions: {sorted(found)}"
    return (found[0] if found else "ccc"), None


def _address_space(text: str, *, default: int | None) -> tuple[int | None, str | None]:
    clean = _mask_sigiled_identifiers(_mask_quoted(text))
    found = re.findall(r"(?<![-A-Za-z$._0-9])addrspace\s*\(\s*([0-9]+)\s*\)", clean)
    if len(found) > 1:
        return None, f"multiple function address spaces: {found}"
    return (int(found[0]) if found else default), None


def _function_abi(
    header: str, symbol_match: re.Match[str], close: int, suffix: str
) -> ABISignature:
    prefix = header[: symbol_match.start()]
    return_type = _type_suffix(prefix)
    if return_type is None:
        return ABISignature.unsupported("unsupported return type")
    params_start = symbol_match.end()
    parameters = _parameter_signature(
        header[params_start:close], declaration=True
    )
    if parameters is None:
        return ABISignature.unsupported("unsupported parameter signature")
    calling_convention, convention_error = _calling_convention(prefix)
    if convention_error:
        return ABISignature.unsupported(convention_error)
    address_space, address_error = _address_space(suffix, default=0)
    if address_error:
        return ABISignature.unsupported(address_error)
    return ABISignature(
        "known",
        return_type[0],
        parameters[0],
        parameters[1],
        calling_convention,
        address_space,
    )


def _call_abi(segment: str, symbol_match: re.Match[str], close: int) -> ABISignature:
    prefix = segment[: symbol_match.start()]
    return_type = _type_suffix(prefix)
    if return_type is None:
        return ABISignature.unsupported("unsupported call return type")
    parameters = _parameter_signature(
        segment[symbol_match.end() : close], declaration=False
    )
    if parameters is None:
        return ABISignature.unsupported("unsupported call argument signature")
    calling_convention, convention_error = _calling_convention(prefix)
    if convention_error:
        return ABISignature.unsupported(convention_error)
    address_space, address_error = _address_space(
        prefix[: return_type[1]], default=None
    )
    if address_error:
        return ABISignature.unsupported(address_error)
    return ABISignature(
        "known",
        return_type[0],
        parameters[0],
        False,
        calling_convention,
        address_space,
    )


def _call_attribute_prefix(suffix: str) -> tuple[str, bool]:
    """Remove invoke destinations, operand bundles, and metadata attachments."""
    clean = _mask_quoted(suffix)
    depth = 0
    index = 0
    while index < len(clean):
        char = clean[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise ParseError("unbalanced call-site attribute parentheses")
        elif depth == 0 and char == "[":
            return suffix[:index], True
        elif depth == 0 and char == ",":
            return suffix[:index], False
        elif depth == 0 and clean.startswith("to label", index):
            before = clean[index - 1] if index else " "
            after_index = index + len("to label")
            after = clean[after_index] if after_index < len(clean) else " "
            if before.isspace() and after.isspace():
                return suffix[:index], False
        index += 1
    if depth != 0:
        raise ParseError("unbalanced call-site attribute parentheses")
    return suffix, False


def _linkage(header: str, symbol_start: int, module: str, symbol: str) -> str:
    prefix = _mask_sigiled_identifiers(_mask_quoted(header[:symbol_start]))
    found = [linkage for linkage in LINKAGES if _word(prefix, linkage)]
    if len(found) > 1:
        raise ParseError(f"{module}: multiple linkages on @{symbol}: {sorted(found)}")
    return found[0] if found else "external"


def _function_record(
    entry: _FunctionEntry, module: str, groups: dict[str, str]
) -> FunctionRecord:
    symbol_match = _SYMBOL.search(entry.header)
    if symbol_match is None:
        first = entry.header.splitlines()[0]
        raise ParseError(f"{module}: cannot parse function symbol: {first}")
    symbol = symbol_match.group("symbol")
    close = _matching_paren(entry.header, symbol_match.end() - 1)
    if close is None:
        raise ParseError(f"{module}: unterminated parameter list for @{symbol}")
    suffix = entry.header[close + 1 :]
    masked_suffix = _mask_quoted(suffix)
    body_open = masked_suffix.find("{")
    if body_open >= 0:
        suffix = suffix[:body_open]
    facts = _attrs_from_suffix(suffix, groups, f"{module}: @{symbol}")
    abi = _function_abi(entry.header, symbol_match, close, suffix)
    return FunctionRecord(
        module=module,
        symbol=symbol,
        kind=entry.kind,
        linkage=_linkage(entry.header, symbol_match.start(), module, symbol),
        facts=facts,
        abi=abi,
    )


def _call_arguments_complete(instruction: str, call_start: int) -> bool:
    segment = instruction[call_start:]
    masked = _mask_quoted(_mask_comments(segment))
    if _INLINE_ASM.search(masked):
        # Inline asm is unsupported regardless; its destination lines are
        # still accumulated by the continuation grammar below.
        return True
    symbol = _SYMBOL.search(segment)
    if symbol is not None:
        return _matching_paren(segment, symbol.end() - 1) is not None
    indirect = re.search(
        r'%(?:"(?:\\.|[^"\\])*"|[-A-Za-z$._][-A-Za-z$._0-9]*)\s*\(',
        segment,
    )
    if indirect is not None:
        return _matching_paren(segment, indirect.end() - 1) is not None
    return False


def _is_call_continuation(line: str) -> bool:
    value = _mask_comments(line).strip()
    if not value:
        return False
    if value.startswith(('"', "[", "]", ",")):
        return True
    if re.match(r"#[0-9]+\b", value):
        return True
    if re.match(r"(?:to|unwind)\s+label\b", value):
        return True
    if re.match(r"label\b", value):
        return True
    first = re.match(r"([-A-Za-z$._][-A-Za-z$._0-9]*)", value)
    return first is not None and first.group(1) in _CALLSITE_ATTRIBUTE_NAMES


def _call_sites(
    entry: _FunctionEntry,
    caller: str,
    module: str,
    groups: dict[str, str],
) -> list[CallSite]:
    calls: list[CallSite] = []
    ordinal = 0
    body_index = 0
    while body_index < len(entry.body):
        line_number, line = entry.body[body_index]
        code = _mask_quoted(_mask_comments(line))
        call_match = _CALL_WORD.search(code)
        if call_match is None:
            body_index += 1
            continue
        ordinal += 1
        parts = [line]
        next_index = body_index + 1
        while not _call_arguments_complete(
            "\n".join(parts), call_match.start()
        ):
            if next_index >= len(entry.body):
                break
            parts.append(entry.body[next_index][1])
            next_index += 1
        while next_index < len(entry.body):
            next_line = entry.body[next_index][1]
            if not _is_call_continuation(next_line):
                break
            parts.append(next_line)
            next_index += 1
        body_index = next_index
        instruction = "\n".join(parts)
        segment = instruction[call_match.start() :]
        masked_segment = _mask_quoted(_mask_comments(segment))
        if _INLINE_ASM.search(masked_segment):
            calls.append(
                CallSite(
                    module,
                    caller,
                    line_number,
                    ordinal,
                    None,
                    _effect_facts(""),
                    ABISignature.unsupported("inline-asm callee"),
                    "inline-asm callee",
                )
            )
            continue
        symbol_match = _SYMBOL.search(segment)
        if symbol_match is None:
            calls.append(
                CallSite(
                    module,
                    caller,
                    line_number,
                    ordinal,
                    None,
                    _effect_facts(""),
                    ABISignature.unsupported("unsupported callee expression"),
                    "indirect, inline-asm, or unsupported callee expression",
                )
            )
            continue
        symbol = symbol_match.group("symbol")
        close = _matching_paren(segment, symbol_match.end() - 1)
        if close is None:
            raise ParseError(
                f"{module}: unterminated call to @{symbol} at line {line_number}"
            )
        suffix = segment[close + 1 :]
        attribute_prefix, has_operand_bundle = _call_attribute_prefix(suffix)
        facts = _attrs_from_suffix(
            attribute_prefix,
            groups,
            f"{module}: call @{symbol} at line {line_number}",
        )
        calls.append(
            CallSite(
                module,
                caller,
                line_number,
                ordinal,
                symbol,
                facts,
                _call_abi(segment, symbol_match, close),
                "operand bundle" if has_operand_bundle else None,
            )
        )
    return calls


def parse_module(path: Path, *, label: str | None = None) -> Module:
    source = path.read_text()
    module = label or str(path)
    groups = _attribute_groups(source, module)
    functions: list[FunctionRecord] = []
    calls: list[CallSite] = []
    seen: set[tuple[str, str]] = set()
    for entry in _function_entries(source, module):
        record = _function_record(entry, module, groups)
        key = (record.kind, record.symbol)
        if key in seen:
            raise ParseError(f"{module}: duplicate {record.kind} for @{record.symbol}")
        seen.add(key)
        functions.append(record)
        if record.kind == "define":
            calls.extend(_call_sites(entry, record.symbol, module, groups))
    if not functions and _MODULE_MARKER.search(_mask_comments(source)) is None:
        raise ParseError(f"{module}: no recognizable LLVM module or function")
    functions.sort(key=lambda record: (record.symbol, record.kind))
    calls.sort(key=lambda call: (call.line, call.ordinal))
    return Module(module, tuple(functions), tuple(calls))


def _join_memory(left: MemoryEffects, right: MemoryEffects) -> MemoryEffects:
    # Unsupported syntax dominates: treating it as absence could manufacture a
    # gap.  A later schema may admit it explicitly.
    if left.state == "unsupported":
        return left
    if right.state == "unsupported":
        return right
    if left.state == "absent":
        return right
    if right.state == "absent":
        return left
    left_bits = left.access_bits()
    right_bits = right.access_bits()
    return MemoryEffects.known(
        {
            location: left_bits[location] & right_bits[location]
            for location in MEMORY_LOCATIONS
        }
    )


def _join_facts(declaration: EffectFacts, callsite: EffectFacts) -> EffectFacts:
    return EffectFacts(
        memory=_join_memory(declaration.memory, callsite.memory),
        nounwind=declaration.nounwind or callsite.nounwind,
        willreturn=declaration.willreturn or callsite.willreturn,
        speculatable=declaration.speculatable or callsite.speculatable,
    )


def _linkage_compatible(declaration: str, definition: str) -> bool:
    if declaration in LOCAL_LINKAGES or declaration in NON_EMITTING_DEFINITION_LINKAGES:
        return False
    if definition in LOCAL_LINKAGES or definition in NON_EMITTING_DEFINITION_LINKAGES:
        return False
    return True


def _function_abi_mismatches(
    declaration: ABISignature, definition: ABISignature
) -> list[str]:
    mismatches: list[str] = []
    if declaration.return_type != definition.return_type:
        mismatches.append("return-type")
    if declaration.parameters != definition.parameters:
        mismatches.append("parameter-types")
    if declaration.vararg != definition.vararg:
        mismatches.append("vararg")
    if declaration.calling_convention != definition.calling_convention:
        mismatches.append("calling-convention")
    if declaration.address_space != definition.address_space:
        mismatches.append("address-space")
    return mismatches


def _call_abi_mismatches(call: ABISignature, declaration: ABISignature) -> list[str]:
    mismatches: list[str] = []
    if call.return_type != declaration.return_type:
        mismatches.append("call-return-type")
    fixed = declaration.parameters
    if declaration.vararg:
        if len(call.parameters) < len(fixed) or call.parameters[: len(fixed)] != fixed:
            mismatches.append("call-parameter-types")
    elif call.parameters != fixed:
        mismatches.append("call-parameter-types")
    if call.calling_convention != declaration.calling_convention:
        mismatches.append("call-calling-convention")
    if call.address_space is not None and call.address_space != declaration.address_space:
        mismatches.append("call-address-space")
    return mismatches


def _missing_required_facts(tier: str, caller: EffectFacts) -> list[str]:
    missing: list[str] = []
    memory = caller.memory.summary()
    if tier == "strong-total-pure":
        if memory != "none":
            missing.append("memory(none)")
    elif tier == "read-only-total":
        if memory not in ("none", "read-only"):
            missing.append("memory(read-only-or-stronger)")
    else:
        raise AssertionError(tier)
    if not caller.nounwind:
        missing.append("nounwind")
    if not caller.willreturn:
        missing.append("willreturn")
    return missing


def _definition_missing_for_eligibility(facts: EffectFacts) -> list[str]:
    missing: list[str] = []
    if facts.memory.state == "absent":
        missing.append("memory-attribute")
    elif facts.memory.state == "known" and facts.memory.summary() == "may-write":
        missing.append("non-writing-memory-effect")
    if not facts.nounwind:
        missing.append("nounwind")
    if not facts.willreturn:
        missing.append("willreturn")
    return missing


def classify_modules(modules: Sequence[Module]) -> dict[str, object]:
    definitions: dict[str, list[FunctionRecord]] = {}
    declarations: dict[tuple[str, str], FunctionRecord] = {}
    all_calls: list[CallSite] = []
    for module in modules:
        all_calls.extend(module.calls)
        for function in module.functions:
            if function.kind == "define":
                definitions.setdefault(function.symbol, []).append(function)
            else:
                declarations[(function.module, function.symbol)] = function

    unsupported_calls = sum(call.unsupported_reason is not None for call in all_calls)
    calls_without_declaration = 0
    records: list[dict[str, object]] = []
    for call in sorted(all_calls, key=lambda c: (c.module, c.line, c.ordinal)):
        if call.symbol is None:
            continue
        declaration = declarations.get((call.module, call.symbol))
        if declaration is None:
            calls_without_declaration += 1
            continue
        effective = _join_facts(declaration.facts, call.facts)
        candidates = [
            definition
            for definition in definitions.get(call.symbol, [])
            if definition.module != call.module
        ]
        compatible = [
            definition
            for definition in candidates
            if _linkage_compatible(declaration.linkage, definition.linkage)
        ]
        base: dict[str, object] = {
            "caller_module": call.module,
            "caller_function": call.caller,
            "callsite_line": call.line,
            "callsite_ordinal": call.ordinal,
            "symbol": call.symbol,
            "declaration_linkage": declaration.linkage,
            "declaration_abi": declaration.abi.as_dict(),
            "declaration_facts": declaration.facts.as_dict(),
            "callsite_abi": call.abi.as_dict(),
            "callsite_facts": call.facts.as_dict(),
            "callsite_unsupported_reason": call.unsupported_reason,
            "effective_caller_facts": effective.as_dict(),
            "definition_module": None,
            "definition_linkage": None,
            "definition_abi": None,
            "definition_facts": None,
            "missing_required_facts": [],
            "missing_speculatable": False,
        }
        if not candidates:
            base["disposition"] = "unresolved-definition"
        elif not compatible:
            base["disposition"] = "linkage-incompatible"
            base["incompatible_definitions"] = [
                {"module": definition.module, "linkage": definition.linkage}
                for definition in sorted(candidates, key=lambda item: item.module)
            ]
        elif len(compatible) != 1:
            base["disposition"] = "ambiguous-definition"
            base["definition_candidates"] = [
                {"module": definition.module, "linkage": definition.linkage}
                for definition in sorted(compatible, key=lambda item: item.module)
            ]
        else:
            definition = compatible[0]
            facts = definition.facts
            base["definition_module"] = definition.module
            base["definition_linkage"] = definition.linkage
            base["definition_abi"] = definition.abi.as_dict()
            base["definition_facts"] = facts.as_dict()
            base["missing_speculatable"] = facts.speculatable and not effective.speculatable
            abi_states = (call.abi.state, declaration.abi.state, definition.abi.state)
            if "unsupported" in abi_states:
                base["disposition"] = "abi-unsupported"
                base["abi_unsupported_reasons"] = {
                    "callsite": call.abi.reason,
                    "declaration": declaration.abi.reason,
                    "definition": definition.abi.reason,
                }
            else:
                abi_mismatches = _call_abi_mismatches(call.abi, declaration.abi)
                abi_mismatches.extend(
                    _function_abi_mismatches(declaration.abi, definition.abi)
                )
                abi_mismatches = sorted(set(abi_mismatches))
                if abi_mismatches:
                    base["disposition"] = "abi-mismatch"
                    base["abi_mismatches"] = abi_mismatches
                elif facts.memory.state == "unsupported":
                    base["disposition"] = "definition-facts-unsupported"
                else:
                    tier = facts.tier()
                    if tier is None:
                        base["disposition"] = "definition-ineligible"
                        base["definition_eligibility_missing"] = (
                            _definition_missing_for_eligibility(facts)
                        )
                    elif (
                        call.unsupported_reason is not None
                        or effective.memory.state == "unsupported"
                    ):
                        base["disposition"] = "caller-facts-unsupported"
                    else:
                        missing = _missing_required_facts(tier, effective)
                        base["missing_required_facts"] = missing
                        base["disposition"] = (
                            "already-visible" if not missing else f"{tier}-gap"
                        )
        records.append(base)

    counts = Counter(str(record["disposition"]) for record in records)
    return {
        "schema": SCHEMA,
        "scope": SCOPE,
        "modules": sorted(module.path for module in modules),
        "summary": {
            "ir_call_instructions": len(all_calls),
            "unsupported_ir_call_instructions": unsupported_calls,
            "direct_calls_without_declaration": calls_without_declaration,
            "opaque_declaration_calls": len(records),
            "disposition_counts": {
                disposition: counts.get(disposition, 0) for disposition in DISPOSITIONS
            },
        },
        "records": records,
    }


def _labels(paths: Iterable[Path], root: Path | None) -> list[tuple[Path, str]]:
    pairs = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            raise ParseError(f"duplicate resolved LLVM IR path: {resolved}")
        seen.add(resolved)
        if root is None:
            label = str(resolved)
        else:
            try:
                label = str(resolved.relative_to(root.resolve()))
            except ValueError as exc:
                raise ParseError(f"{resolved} is outside --root {root.resolve()}") from exc
        pairs.append((resolved, label))
    return sorted(pairs, key=lambda pair: pair[1])


def run(paths: Sequence[Path], *, root: Path | None = None) -> dict[str, object]:
    if not paths:
        raise ParseError("at least one LLVM IR path is required")
    modules = [parse_module(path, label=label) for path, label in _labels(paths, root)]
    return classify_modules(modules)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ir", type=Path, nargs="+", help="optimized LLVM .ll modules")
    parser.add_argument("--root", type=Path, help="render module paths relative to this root")
    parser.add_argument("--pretty", action="store_true", help="pretty-print deterministic JSON")
    args = parser.parse_args(argv)
    try:
        report = run(args.ir, root=args.root)
    except (OSError, UnicodeError, ParseError) as exc:
        print(f"effect-attrs classifier: {exc}", file=sys.stderr)
        return 2
    if args.pretty:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
