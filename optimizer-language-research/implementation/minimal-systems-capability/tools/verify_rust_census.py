#!/usr/bin/env python3
"""Verify the pinned Rust 1.97.0 census artifacts and independent seed counts."""

from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parent.parent
INVENTORY = ROOT / "RUST-1.97.0-API-INVENTORY.tsv"
MODULES = ROOT / "RUST-1.97.0-MODULE-ACCOUNTING.tsv"
MANIFEST = ROOT / "RUST-1.97.0-CENSUS-MANIFEST.json"

EXPECTED_COUNTS = {
    "inventory_rows": 16432,
    "stable_safe_rows": 9874,
    "stable_unsafe_rows": 554,
    "unstable_rows": 6004,
    "canonical_stable_safe_declarations": 5096,
    "canonical_stable_unsafe_declarations": 273,
    "module_rows": 290,
    "collapsed_module_rows": 28,
    "missing_pages": 0,
    "external_module_links": 0,
}

# Independent narrow extractor counts recorded by the data-structure census.
EXPECTED_SEEDS = {
    "std::array": (5, 0),
    "std::slice": (121, 13),
    "std::str": (74, 7),
    "alloc::boxed::Box": (13, 3),
    "alloc::vec::Vec": (44, 2),
    "alloc::collections::vec_deque::VecDeque": (54, 0),
    "alloc::collections::linked_list::LinkedList": (20, 0),
    "alloc::collections::binary_heap::BinaryHeap": (23, 0),
    "alloc::collections::btree_map::BTreeMap": (31, 0),
    "alloc::collections::btree_set::BTreeSet": (27, 0),
    "std::collections::hash_map::HashMap": (32, 1),
    "std::collections::hash_set::HashSet": (30, 0),
    "alloc::string::String": (35, 3),
    "alloc::rc::Rc": (19, 5),
    "alloc::rc::Weak": (7, 1),
    "core::cell::RefCell": (12, 1),
}


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"census verification failed: {message}")


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(manifest["schema"] == "rustdoc-public-api-v1", "unexpected schema")
    require(manifest["rust"]["version"] == "1.97.0", "unexpected Rust version")
    require(
        manifest["rust"]["commit"] == "2d8144b7880597b6e6d3dfd63a9a9efae3f533d3",
        "unexpected Rust commit",
    )
    require(manifest["counts"] == EXPECTED_COUNTS, "manifest counts changed")
    require(manifest["outputs"][INVENTORY.name] == digest(INVENTORY), "inventory digest mismatch")
    require(manifest["outputs"][MODULES.name] == digest(MODULES), "module digest mismatch")

    with INVENTORY.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    with MODULES.open(encoding="utf-8", newline="") as handle:
        modules = list(csv.DictReader(handle, delimiter="\t"))

    require(len(rows) == EXPECTED_COUNTS["inventory_rows"], "inventory row count changed")
    require(len(modules) == EXPECTED_COUNTS["module_rows"], "module row count changed")
    require(all(row["canonical_key"] for row in rows), "empty canonical key")
    require(all(row["docs_path"] for row in rows), "empty documentation path")
    require(
        sum(row["mode"] == "collapsed" for row in modules) == 28,
        "collapsed-module set changed",
    )
    require(
        sum(int(row["direct_stable_items"]) for row in modules if row["mode"] == "collapsed")
        == 16888,
        "collapsed stable item accounting changed",
    )
    require(
        sum(int(row["direct_unstable_items"]) for row in modules if row["mode"] == "collapsed")
        == 12633,
        "collapsed unstable item accounting changed",
    )

    actual_seeds: dict[str, list[int]] = {path: [0, 0] for path in EXPECTED_SEEDS}
    canonical_safe: set[str] = set()
    canonical_unsafe: set[str] = set()
    for row in rows:
        if row["item_path"] not in EXPECTED_SEEDS:
            continue
        if row["member_kind"] != "provided_or_inherent_method" or row["stability"] != "stable":
            continue
        index = 0 if row["caller_safety"] == "safe" else 1
        actual_seeds[row["item_path"]][index] += 1
        (canonical_safe if index == 0 else canonical_unsafe).add(row["canonical_key"])

    for path, expected in EXPECTED_SEEDS.items():
        require(tuple(actual_seeds[path]) == expected, f"seed count changed for {path}")
    require(len(canonical_safe) == 545, "canonical stable-safe seed count is not 545")
    require(len(canonical_unsafe) == 35, "canonical stable-unsafe seed count is not 35")

    print(
        "rust census: PASS — 290 modules, 16,432 detailed rows, "
        "5,096 canonical stable-safe and 273 canonical stable-unsafe declarations; "
        "545/35 selected data-structure seeds"
    )


if __name__ == "__main__":
    main()
