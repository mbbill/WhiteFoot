import unittest

from schema import (
    EFFECTIVE_DOMAIN,
    FIELD_COUNT,
    FIELDS,
    FIXED_HEADER,
    HARD_DOMAIN,
    MAX_EXPECTED_TERMINALS,
    ProfileField,
    RESOLUTION_VIEW_NAMES,
    SchemaError,
    decode,
    encode_effective,
    encode_hard,
    identity,
    schema_descriptor,
    validate_hard_representation,
    validate_candidate_schema,
    validate_profile_pair,
    validate_schema,
    validate_tightening,
)


EXPECTED_FIELDS = (
    (1, "ingress", "max_sources", "sources"),
    (2, "ingress", "max_logical_path_bytes", "bytes per path"),
    (3, "ingress", "max_source_bytes", "bytes per source"),
    (4, "ingress", "max_total_source_bytes", "bytes per bundle"),
    (5, "ingress", "max_binding_bytes", "encoded bytes"),
    (6, "lexical", "max_token_bytes", "bytes per token"),
    (7, "lexical", "max_tokens", "tokens"),
    (8, "lexical", "max_lexemes", "tokens and trivia pieces"),
    (9, "lexical", "max_lexical_scan_work", "work units"),
    (10, "syntax", "max_classified_tokens", "classified tokens"),
    (11, "syntax", "max_production_nodes", "production nodes"),
    (12, "syntax", "max_mixed_elements", "non-root nodes and terminals"),
    (13, "syntax", "max_tree_depth", "production-parent edges"),
    (14, "syntax", "max_parser_stack_entries", "simultaneous entries"),
    (15, "syntax", "max_list_members", "successful repeat members"),
    (16, "syntax", "max_expected_terminals", "predicates and source end"),
    (17, "syntax", "max_syntax_work", "work units"),
    (18, "syntax", "max_tree_bytes", "charged persistent-tree bytes"),
    (19, "resolution", "max_declarations", "declaration records"),
    (20, "resolution", "max_scopes", "scopes"),
    (21, "resolution", "max_scope_depth", "parent edges"),
    (22, "resolution", "max_declaration_events", "source events"),
    (23, "resolution", "max_lexical_uses", "use records"),
    (24, "resolution", "max_deferred_uses", "deferred-use records"),
    (25, "resolution", "max_spelling_bytes", "charged spelling bytes"),
    (26, "resolution", "max_lookup_entries", "lookup records"),
    (27, "resolution", "max_ancestry_steps", "scope parent edges"),
    (28, "resolution", "max_node_path_depth", "path components"),
    (29, "resolution", "max_diagnostic_origins", "origin descriptors"),
    (30, "resolution", "max_diagnostic_paths", "node paths"),
    (31, "resolution", "max_diagnostic_path_components", "path components"),
    (32, "resolution", "max_coverage_records", "coverage records"),
    (33, "resolution", "max_resolution_work", "work units"),
)


class ResourceProfileSchemaTests(unittest.TestCase):
    def test_complete_schema_tuple_is_pinned(self) -> None:
        validate_schema()
        self.assertEqual(
            tuple((field.tag, field.stage, field.name, field.unit) for field in FIELDS),
            EXPECTED_FIELDS,
        )

    def test_resolution_view_retains_exact_r04_order(self) -> None:
        self.assertEqual(
            RESOLUTION_VIEW_NAMES,
            (
                "max_declarations",
                "max_scopes",
                "max_scope_depth",
                "max_declaration_events",
                "max_lexical_uses",
                "max_deferred_uses",
                "max_spelling_bytes",
                "max_lookup_entries",
                "max_ancestry_steps",
                "max_node_path_depth",
                "max_diagnostic_origins",
                "max_diagnostic_paths",
                "max_diagnostic_path_components",
                "max_coverage_records",
                "max_work",
            ),
        )

    def test_v1_contains_no_future_stage_placeholder(self) -> None:
        self.assertEqual(
            {field.stage for field in FIELDS},
            {"ingress", "lexical", "syntax", "resolution"},
        )

    def test_every_schema_tuple_mutation_is_rejected(self) -> None:
        mutations = []
        mutations.append(FIELDS[:-1])
        mutations.append(FIELDS + (ProfileField(34, "typing", "max_types", "types"),))
        swapped = list(FIELDS)
        swapped[0], swapped[1] = swapped[1], swapped[0]
        mutations.append(tuple(swapped))
        for attribute, replacement in (
            ("tag", 99),
            ("stage", "typing"),
            ("name", "max_files"),
            ("unit", "records"),
        ):
            changed = list(FIELDS)
            original = changed[0]
            changed[0] = ProfileField(
                replacement if attribute == "tag" else original.tag,
                replacement if attribute == "stage" else original.stage,
                replacement if attribute == "name" else original.name,
                replacement if attribute == "unit" else original.unit,
            )
            mutations.append(tuple(changed))
        duplicate = list(FIELDS)
        duplicate[1] = ProfileField(2, "ingress", "max_sources", "bytes per path")
        mutations.append(tuple(duplicate))
        for mutation in mutations:
            with self.assertRaises(SchemaError):
                validate_candidate_schema(mutation)

    def test_hard_and_effective_round_trip(self) -> None:
        specification = bytes(range(32))
        semantics = bytes(reversed(range(32)))
        work = bytes([0x55] * 32)
        storage = bytes([0xAA] * 32)
        host = "aarch64-apple-darwin-test"
        values_list = [index * index for index in range(33)]
        values_list[15] = MAX_EXPECTED_TERMINALS
        values = tuple(values_list)
        hard = encode_hard(specification, semantics, work, storage, host, values)
        self.assertEqual(
            decode(hard, HARD_DOMAIN),
            (bytes(32), specification, semantics, work, storage, host, values),
        )
        hard_identity = identity(hard)
        effective_values = tuple(value // 2 for value in values)
        effective = encode_effective(
            hard_identity,
            specification,
            semantics,
            work,
            storage,
            host,
            effective_values,
        )
        self.assertEqual(
            decode(effective, EFFECTIVE_DOMAIN),
            (
                hard_identity,
                specification,
                semantics,
                work,
                storage,
                host,
                effective_values,
            ),
        )
        self.assertEqual(
            validate_profile_pair(hard, effective),
            effective_values,
        )

    def test_encoding_rejects_omit_add_reorder_and_trailing_bytes(self) -> None:
        digest = bytes(32)
        values = tuple(range(33))
        with self.assertRaisesRegex(SchemaError, "count"):
            encode_hard(digest, digest, digest, digest, "test-host", values[:-1])
        with self.assertRaisesRegex(SchemaError, "count"):
            encode_hard(digest, digest, digest, digest, "test-host", values + (33,))
        encoded = encode_hard(digest, digest, digest, digest, "test-host", values)
        reordered = bytearray(encoded)
        first = FIXED_HEADER.size + len("test-host") + FIELD_COUNT.size
        reordered[first : first + 2] = (2).to_bytes(2, "big")
        with self.assertRaisesRegex(SchemaError, "tag or order"):
            decode(bytes(reordered), HARD_DOMAIN)
        with self.assertRaisesRegex(SchemaError, "length"):
            decode(encoded + b"x", HARD_DOMAIN)

    def test_identity_changes_after_one_bit_mutation(self) -> None:
        encoded = encode_hard(
            bytes(32),
            bytes(32),
            bytes(32),
            bytes(32),
            "test-host",
            tuple(range(33)),
        )
        mutated = bytearray(encoded)
        mutated[-1] ^= 1
        self.assertNotEqual(identity(encoded), identity(bytes(mutated)))

    def test_schema_descriptor_and_synthetic_golden_vectors_are_pinned(self) -> None:
        digest = bytes(32)
        values = tuple(range(33))
        hard = encode_hard(digest, digest, digest, digest, "test-host", values)
        effective = encode_effective(
            identity(hard),
            digest,
            digest,
            digest,
            digest,
            "test-host",
            values,
        )
        self.assertEqual(
            identity(schema_descriptor()).hex(),
            "db03e3b9af295fef9d0c08e70f8b11803995a43449c242ae3c66a64eaed57968",
        )
        self.assertEqual(
            identity(hard).hex(),
            "6c79cfe3e5806a188274b9a06337e43a67a205aa221998ac001dcf852375eb99",
        )
        self.assertEqual(
            identity(effective).hex(),
            "e14d1b005d1f11a223080bef21215129ccba83a082e948438353f780621aae2f",
        )

    def test_codec_rejects_noncanonical_host_and_parent_identity(self) -> None:
        digest = bytes(32)
        values = tuple(range(33))
        with self.assertRaisesRegex(SchemaError, "graphic ASCII"):
            encode_hard(digest, digest, digest, digest, "bad host", values)
        hard = bytearray(
            encode_hard(digest, digest, digest, digest, "test-host", values)
        )
        hard[18] = 1
        with self.assertRaisesRegex(SchemaError, "nonzero parent"):
            decode(bytes(hard), HARD_DOMAIN)
        effective_zero = bytearray(
            encode_hard(digest, digest, digest, digest, "test-host", values)
        )
        effective_zero[:16] = EFFECTIVE_DOMAIN
        with self.assertRaisesRegex(SchemaError, "zero hard-profile"):
            decode(bytes(effective_zero), EFFECTIVE_DOMAIN)
        with self.assertRaisesRegex(SchemaError, "not recognized"):
            decode(bytes(hard), b"UNKNOWN-DOMAIN!!")

    def test_pair_rejects_every_parent_or_meaning_mismatch(self) -> None:
        values = tuple(range(33))
        specification = bytes([1] * 32)
        semantics = bytes([2] * 32)
        work = bytes([3] * 32)
        storage = bytes([4] * 32)
        host = "test-host"
        hard = encode_hard(
            specification,
            semantics,
            work,
            storage,
            host,
            values,
        )

        def child(
            parent: bytes = identity(hard),
            child_specification: bytes = specification,
            child_semantics: bytes = semantics,
            child_work: bytes = work,
            child_storage: bytes = storage,
            child_host: str = host,
        ) -> bytes:
            return encode_effective(
                parent,
                child_specification,
                child_semantics,
                child_work,
                child_storage,
                child_host,
                values,
            )

        mutations = (
            (child(parent=bytes([9] * 32)), "wrong hard-profile"),
            (child(child_specification=bytes([9] * 32)), "specification"),
            (child(child_semantics=bytes([9] * 32)), "semantics"),
            (child(child_work=bytes([9] * 32)), "work"),
            (child(child_storage=bytes([9] * 32)), "storage"),
            (child(child_host="other-host"), "host class"),
        )
        for encoded, message in mutations:
            with self.assertRaisesRegex(SchemaError, message):
                validate_profile_pair(hard, encoded)

    def test_only_downward_closed_representation_constraints_are_validated(self) -> None:
        values = [0] * 33
        values[15] = MAX_EXPECTED_TERMINALS
        validate_hard_representation(values)
        values[15] += 1
        with self.assertRaisesRegex(SchemaError, "expected-terminal"):
            validate_hard_representation(values)
        values[15] = 0
        values[0] = 1 << 32
        with self.assertRaisesRegex(SchemaError, "max_sources"):
            validate_hard_representation(values)

    def test_pointwise_tightening_can_be_relationally_inconsistent(self) -> None:
        hard = [100] * 33
        hard[15] = MAX_EXPECTED_TERMINALS
        effective = [0] * 33
        effective[6] = 50
        effective[7] = 1
        self.assertEqual(validate_tightening(hard, effective), tuple(effective))
        effective[7] = 101
        with self.assertRaisesRegex(SchemaError, "max_lexemes"):
            validate_tightening(hard, effective)


if __name__ == "__main__":
    unittest.main()
