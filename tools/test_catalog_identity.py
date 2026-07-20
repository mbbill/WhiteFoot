#!/usr/bin/env python3
"""Hostile tests for the exact static-catalog identity locks."""

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import catalog_identity
import semantic_catalog


EXPECTED = "2fa586a8a1d9a49f344d64ad2b5f450a2ae2e8362bc187c70267097b9b427e1d"
DECOMPOSITION = "3ccd1c7b5113e176e7edac37eb4a98603d158cce41908a6297064bf5ded2d156"


class CatalogIdentityTests(unittest.TestCase):
    def test_live_catalog_and_both_locks_have_the_exact_identity(self) -> None:
        root_before = catalog_identity.read_lock(
            catalog_identity.ROOT,
            catalog_identity.ROOT_LOCK_COMPONENTS,
            "root static-catalog lock",
        )
        compiler_before = catalog_identity.read_lock(
            catalog_identity.ROOT,
            catalog_identity.COMPILER_LOCK_COMPONENTS,
            "compiler static-catalog lock",
        )
        self.assertEqual(catalog_identity.check(), EXPECTED)
        self.assertEqual(
            catalog_identity.EXPECTED_STATIC_SEMANTIC_CATALOG_SHA256,
            EXPECTED,
        )
        self.assertEqual(
            catalog_identity.read_lock(
                catalog_identity.ROOT,
                catalog_identity.ROOT_LOCK_COMPONENTS,
                "root static-catalog lock",
            ),
            root_before,
        )
        self.assertEqual(
            catalog_identity.read_lock(
                catalog_identity.ROOT,
                catalog_identity.COMPILER_LOCK_COMPONENTS,
                "compiler static-catalog lock",
            ),
            compiler_before,
        )

    def test_lock_spelling_is_exact_and_fail_closed(self) -> None:
        valid = (EXPECTED + "\n").encode("ascii")
        malformed = (
            EXPECTED.encode("ascii"),
            (EXPECTED + "\r\n").encode("ascii"),
            (EXPECTED.upper() + "\n").encode("ascii"),
            (EXPECTED + "\n\n").encode("ascii"),
            ("g" + EXPECTED[1:] + "\n").encode("ascii"),
        )
        self.assertEqual(catalog_identity.parse_lock(valid, "probe"), EXPECTED)
        for raw in malformed:
            with self.subTest(raw=raw):
                with self.assertRaises(catalog_identity.CatalogIdentityError):
                    catalog_identity.parse_lock(raw, "probe")

    def test_stale_and_cross_lock_substitutions_are_distinct(self) -> None:
        valid = (EXPECTED + "\n").encode("ascii")
        stale = (("0" * 64) + "\n").encode("ascii")
        with self.assertRaisesRegex(catalog_identity.CatalogIdentityError, "root.*stale"):
            catalog_identity.validate_identities(EXPECTED, stale, valid)
        with self.assertRaisesRegex(catalog_identity.CatalogIdentityError, "compiler.*differs"):
            catalog_identity.validate_identities(EXPECTED, valid, stale)
        with self.assertRaisesRegex(catalog_identity.CatalogIdentityError, "reviewed"):
            catalog_identity.validate_identities("0" * 64, valid, valid)

    def test_catalog_identity_is_not_the_decomposition_identity(self) -> None:
        catalog = semantic_catalog.build_from_files()
        self.assertEqual(catalog["decomposition_sha256"], DECOMPOSITION)
        self.assertEqual(catalog_identity.catalog_sha256(catalog), EXPECTED)
        self.assertNotEqual(EXPECTED, DECOMPOSITION)

        changed = copy.deepcopy(catalog)
        changed["kind"] += "-changed"
        self.assertNotEqual(catalog_identity.catalog_sha256(changed), EXPECTED)

    def test_outer_catalog_identity_does_not_use_the_generator_hash_helper(self) -> None:
        catalog = semantic_catalog.build_from_files()
        with mock.patch.object(
            semantic_catalog,
            "sha256",
            return_value="0" * 64,
        ):
            self.assertEqual(catalog_identity.catalog_sha256(catalog), EXPECTED)

    def test_lock_reader_rejects_symlink_substitution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock = root / "facets" / "v0.8" / "static-catalog.sha256"
            lock.parent.mkdir(parents=True)
            outside = root / "outside"
            outside.write_text(EXPECTED + "\n", encoding="ascii")
            lock.symlink_to(outside)
            with self.assertRaises(catalog_identity.CatalogIdentityError):
                catalog_identity.read_lock(
                    root,
                    catalog_identity.ROOT_LOCK_COMPONENTS,
                    "probe lock",
                )

    def test_lock_reader_rejects_oversized_regular_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock = root / "facets" / "v0.8" / "static-catalog.sha256"
            lock.parent.mkdir(parents=True)
            lock.write_bytes((EXPECTED + "\n\n").encode("ascii"))
            with self.assertRaises(catalog_identity.CatalogIdentityError):
                catalog_identity.read_lock(
                    root,
                    catalog_identity.ROOT_LOCK_COMPONENTS,
                    "probe lock",
                )


if __name__ == "__main__":
    unittest.main()
