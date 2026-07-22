"""Exact non-authoritative ResourceProfile v1 field and wire schema.

This module contains no production hard maximum. Its golden vectors use
synthetic values only to freeze the proposed canonical encoding.
"""

from dataclasses import dataclass
from hashlib import sha256
import struct
from typing import Iterable


SCHEMA_VERSION = 1
HARD_DOMAIN = b"WHITEFOOT-RP-H1\0"
EFFECTIVE_DOMAIN = b"WHITEFOOT-RP-E1\0"
DESCRIPTOR_DOMAIN = b"WHITEFOOT-RP-S1\0"
DIGEST_BYTES = 32
FIXED_HEADER = struct.Struct(">16sH32s32s32s32s32sH")
FIELD_COUNT = struct.Struct(">H")
FIELD = struct.Struct(">HQ")
MAX_EXPECTED_TERMINALS = 73
MAX_HOST_CLASS_BYTES = 255


@dataclass(frozen=True)
class ProfileField:
    tag: int
    stage: str
    name: str
    unit: str


FIELDS = (
    ProfileField(1, "ingress", "max_sources", "sources"),
    ProfileField(2, "ingress", "max_logical_path_bytes", "bytes per path"),
    ProfileField(3, "ingress", "max_source_bytes", "bytes per source"),
    ProfileField(4, "ingress", "max_total_source_bytes", "bytes per bundle"),
    ProfileField(5, "ingress", "max_binding_bytes", "encoded bytes"),
    ProfileField(6, "lexical", "max_token_bytes", "bytes per token"),
    ProfileField(7, "lexical", "max_tokens", "tokens"),
    ProfileField(8, "lexical", "max_lexemes", "tokens and trivia pieces"),
    ProfileField(9, "lexical", "max_lexical_scan_work", "work units"),
    ProfileField(10, "syntax", "max_classified_tokens", "classified tokens"),
    ProfileField(11, "syntax", "max_production_nodes", "production nodes"),
    ProfileField(12, "syntax", "max_mixed_elements", "non-root nodes and terminals"),
    ProfileField(13, "syntax", "max_tree_depth", "production-parent edges"),
    ProfileField(14, "syntax", "max_parser_stack_entries", "simultaneous entries"),
    ProfileField(15, "syntax", "max_list_members", "successful repeat members"),
    ProfileField(16, "syntax", "max_expected_terminals", "predicates and source end"),
    ProfileField(17, "syntax", "max_syntax_work", "work units"),
    ProfileField(18, "syntax", "max_tree_bytes", "charged persistent-tree bytes"),
    ProfileField(19, "resolution", "max_declarations", "declaration records"),
    ProfileField(20, "resolution", "max_scopes", "scopes"),
    ProfileField(21, "resolution", "max_scope_depth", "parent edges"),
    ProfileField(22, "resolution", "max_declaration_events", "source events"),
    ProfileField(23, "resolution", "max_lexical_uses", "use records"),
    ProfileField(24, "resolution", "max_deferred_uses", "deferred-use records"),
    ProfileField(25, "resolution", "max_spelling_bytes", "charged spelling bytes"),
    ProfileField(26, "resolution", "max_lookup_entries", "lookup records"),
    ProfileField(27, "resolution", "max_ancestry_steps", "scope parent edges"),
    ProfileField(28, "resolution", "max_node_path_depth", "path components"),
    ProfileField(29, "resolution", "max_diagnostic_origins", "origin descriptors"),
    ProfileField(30, "resolution", "max_diagnostic_paths", "node paths"),
    ProfileField(31, "resolution", "max_diagnostic_path_components", "path components"),
    ProfileField(32, "resolution", "max_coverage_records", "coverage records"),
    ProfileField(33, "resolution", "max_resolution_work", "work units"),
)


RESOLUTION_VIEW_NAMES = tuple(
    "max_work" if field.name == "max_resolution_work" else field.name
    for field in FIELDS
    if field.stage == "resolution"
)


class SchemaError(ValueError):
    """The profile schema or one encoded profile is malformed."""


def _digest(value: bytes, label: str) -> bytes:
    if len(value) != DIGEST_BYTES:
        raise SchemaError(f"{label} must contain exactly 32 bytes")
    return value


def _values(values: Iterable[int]) -> tuple[int, ...]:
    closed = tuple(values)
    if len(closed) != len(FIELDS):
        raise SchemaError("profile value count does not match the field schema")
    if any(value < 0 or value > (1 << 64) - 1 for value in closed):
        raise SchemaError("profile value does not fit unsigned 64-bit encoding")
    return closed


def _host_class(value: str) -> bytes:
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError as error:
        raise SchemaError("host class must be ASCII") from error
    if not encoded or len(encoded) > MAX_HOST_CLASS_BYTES:
        raise SchemaError("host class length is outside the closed bound")
    if any(byte < 0x21 or byte > 0x7E for byte in encoded):
        raise SchemaError("host class contains non-graphic ASCII")
    return encoded


def _encode(
    domain: bytes,
    parent_digest: bytes,
    specification_digest: bytes,
    semantics_digest: bytes,
    work_digest: bytes,
    storage_digest: bytes,
    host_class: str,
    values: Iterable[int],
) -> bytes:
    closed = _values(values)
    host = _host_class(host_class)
    output = bytearray(
        FIXED_HEADER.pack(
            domain,
            SCHEMA_VERSION,
            _digest(parent_digest, "parent digest"),
            _digest(specification_digest, "specification digest"),
            _digest(semantics_digest, "semantics digest"),
            _digest(work_digest, "work digest"),
            _digest(storage_digest, "storage digest"),
            len(host),
        )
    )
    output.extend(host)
    output.extend(FIELD_COUNT.pack(len(FIELDS)))
    for field, value in zip(FIELDS, closed):
        output.extend(FIELD.pack(field.tag, value))
    return bytes(output)


def encode_hard(
    specification_digest: bytes,
    semantics_digest: bytes,
    work_digest: bytes,
    storage_digest: bytes,
    host_class: str,
    values: Iterable[int],
) -> bytes:
    """Encode one proposed hard profile in its exact canonical byte form."""
    return _encode(
        HARD_DOMAIN,
        bytes(DIGEST_BYTES),
        specification_digest,
        semantics_digest,
        work_digest,
        storage_digest,
        host_class,
        values,
    )


def encode_effective(
    hard_profile_digest: bytes,
    specification_digest: bytes,
    semantics_digest: bytes,
    work_digest: bytes,
    storage_digest: bytes,
    host_class: str,
    values: Iterable[int],
) -> bytes:
    """Encode one caller-tightened effective profile."""
    return _encode(
        EFFECTIVE_DOMAIN,
        hard_profile_digest,
        specification_digest,
        semantics_digest,
        work_digest,
        storage_digest,
        host_class,
        values,
    )


def decode(
    encoded: bytes,
    expected_domain: bytes,
) -> tuple[bytes, bytes, bytes, bytes, bytes, str, tuple[int, ...]]:
    """Strictly decode one hard or effective canonical profile."""
    if expected_domain not in (HARD_DOMAIN, EFFECTIVE_DOMAIN):
        raise SchemaError("expected profile domain is not recognized")
    if len(encoded) < FIXED_HEADER.size + FIELD_COUNT.size:
        raise SchemaError("profile byte length is not canonical")
    (
        domain,
        version,
        parent_digest,
        specification_digest,
        semantics_digest,
        work_digest,
        storage_digest,
        host_length,
    ) = FIXED_HEADER.unpack_from(encoded)
    if domain != expected_domain:
        raise SchemaError("profile domain is wrong")
    if version != SCHEMA_VERSION:
        raise SchemaError("profile schema version is wrong")
    cursor = FIXED_HEADER.size
    host_end = cursor + host_length
    expected_length = host_end + FIELD_COUNT.size + FIELD.size * len(FIELDS)
    if host_end > len(encoded) or expected_length != len(encoded):
        raise SchemaError("profile byte length is not canonical")
    try:
        host_class = encoded[cursor:host_end].decode("ascii")
    except UnicodeDecodeError as error:
        raise SchemaError("host class is not ASCII") from error
    if _host_class(host_class) != encoded[cursor:host_end]:
        raise SchemaError("host class encoding is not canonical")
    count = FIELD_COUNT.unpack_from(encoded, host_end)[0]
    if count != len(FIELDS):
        raise SchemaError("profile field count is wrong")
    cursor = host_end + FIELD_COUNT.size
    values = []
    for expected in FIELDS:
        tag, value = FIELD.unpack_from(encoded, cursor)
        cursor += FIELD.size
        if tag != expected.tag:
            raise SchemaError("profile field tag or order is wrong")
        values.append(value)
    if expected_domain == HARD_DOMAIN and parent_digest != bytes(DIGEST_BYTES):
        raise SchemaError("hard profile has a nonzero parent identity")
    if expected_domain == EFFECTIVE_DOMAIN and parent_digest == bytes(DIGEST_BYTES):
        raise SchemaError("effective profile has a zero hard-profile identity")
    return (
        parent_digest,
        specification_digest,
        semantics_digest,
        work_digest,
        storage_digest,
        host_class,
        tuple(values),
    )


def schema_descriptor() -> bytes:
    """Encode exact field names, stages, and units for review hashing."""
    output = bytearray(DESCRIPTOR_DOMAIN)
    output.extend(struct.pack(">HH", SCHEMA_VERSION, len(FIELDS)))
    for field in FIELDS:
        output.extend(struct.pack(">H", field.tag))
        for text in (field.stage, field.name, field.unit):
            encoded = text.encode("ascii")
            output.extend(struct.pack(">H", len(encoded)))
            output.extend(encoded)
    return bytes(output)


def validate_hard_representation(values: Iterable[int]) -> tuple[int, ...]:
    """Check only downward-closed representation restrictions."""
    closed = _values(values)
    by_name = {field.name: closed[index] for index, field in enumerate(FIELDS)}
    for name in (
        "max_sources",
        "max_production_nodes",
        "max_mixed_elements",
        "max_tree_depth",
    ):
        if by_name[name] > (1 << 32) - 1:
            raise SchemaError(f"{name} exceeds the v1 u32 representation")
    if by_name["max_expected_terminals"] > MAX_EXPECTED_TERMINALS:
        raise SchemaError("expected-terminal maximum exceeds the closed v1 universe")
    return closed


def validate_tightening(hard: Iterable[int], effective: Iterable[int]) -> tuple[int, ...]:
    """Accept arbitrary pointwise tightening and reject every loosening."""
    hard_values = validate_hard_representation(hard)
    effective_values = validate_hard_representation(effective)
    for field, hard_value, effective_value in zip(FIELDS, hard_values, effective_values):
        if effective_value > hard_value:
            raise SchemaError(f"{field.name} loosens the hard profile")
    return effective_values


def validate_profile_pair(hard_encoded: bytes, effective_encoded: bytes) -> tuple[int, ...]:
    """Validate one exact hard profile and its caller-tightened child."""
    hard = decode(hard_encoded, HARD_DOMAIN)
    effective = decode(effective_encoded, EFFECTIVE_DOMAIN)
    if effective[0] != identity(hard_encoded):
        raise SchemaError("effective profile names the wrong hard-profile identity")
    labels = ("specification", "semantics", "work", "storage", "host class")
    for index, label in zip(range(1, 6), labels):
        if effective[index] != hard[index]:
            raise SchemaError(f"effective profile changes the {label} identity")
    return validate_tightening(hard[6], effective[6])


def identity(encoded: bytes) -> bytes:
    """Return the exact 32-byte identity of canonical profile bytes."""
    return sha256(encoded).digest()


def validate_candidate_schema(candidate: Iterable[ProfileField]) -> None:
    """Reject any candidate that differs from the complete closed tuple."""
    closed = tuple(candidate)
    expected_tags = tuple(range(1, len(closed) + 1))
    actual_tags = tuple(field.tag for field in closed)
    if actual_tags != expected_tags:
        raise SchemaError("profile field tags are not contiguous")
    names = tuple(field.name for field in closed)
    if len(names) != len(set(names)):
        raise SchemaError("profile field names are not unique")
    if any(not field.stage or not field.unit for field in closed):
        raise SchemaError("profile field stage or unit is empty")
    if closed != FIELDS:
        raise SchemaError("profile field tuple differs from ResourceProfile v1")


def validate_schema() -> None:
    """Reject drift in the module's closed schema."""
    validate_candidate_schema(FIELDS)


if __name__ == "__main__":
    validate_schema()
