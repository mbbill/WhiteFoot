#!/usr/bin/env python3
"""Build the deterministic exact-byte manifest for G0-Core review."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "G0-CORE-ARTIFACT-MANIFEST.json"

ARTIFACTS = [
    "../../../CONSTITUTION.md",
    "../../../AGENTS.md",
    "../../../CLAUDE.md",
    "../../../PATTERNS.md",
    "../../../THE-PLAN.md",
    "../../../spec/kernel-spec-v0.6.md",
    "../../notes/user-directives.md",
    "../../../mcts_mem/xlang.md",
    "../../../mcts_mem/xlang/data-model.md",
    "../../../mcts_mem/xlang/ownership.md",
    "../../../mcts_mem/xlang/ownership/copy-classification.md",
    "../../../mcts_mem/xlang/ownership/copy-classification.alt/uniform-affine-enums.md",
    "../../../mcts_mem/xlang/pattern-doctrine.md",
    "../../../mcts_mem/xlang/pattern-doctrine.alt/unconstrained-architecture.md",
    "../../../mcts_mem/xlang/fact-channels.md",
    "../../../mcts_mem/xlang/surface-form.md",
    "G0-CORE-CHARTER.md",
    "RUST-1.97.0-CENSUS-MANIFEST.json",
    "RUST-1.97.0-API-INVENTORY.tsv",
    "RUST-1.97.0-MODULE-ACCOUNTING.tsv",
    "RUST-CENSUS-NOTES.md",
    "DOMAIN-CLASSIFICATION-RULES.tsv",
    "RUST-1.97.0-DOMAIN-CLASSIFICATION.tsv",
    "RUST-1.97.0-DOMAIN-SUMMARY.tsv",
    "RUST-1.97.0-MODULE-DOMAIN-MAP.tsv",
    "SYSTEMS-DOMAIN-LEDGER.md",
    "RUST-DATA-CONTRACT-CENSUS.md",
    "RUST-DATA-CONTRACT-CENSUS.tsv",
    "RUST-DATA-SURFACE-MAP.tsv",
    "RUST-D10-SURFACE-MAP.tsv",
    "CAPABILITY-OBLIGATION-REGISTRY.tsv",
    "SEMANTIC-OBLIGATION-REGISTRY.md",
    "DERIVATION-MATRIX.tsv",
    "WITNESS-REGISTRY.md",
    "E01-TRACEABILITY.md",
    "FAMILY-LOCK-A-TEMPLATE.md",
    "G0-CORE-REPORT.md",
    "tools/extract_rust_api.py",
    "tools/verify_rust_census.py",
    "tools/classify_rust_api.py",
    "tools/verify_rust_data_contract_census.py",
    "tools/build_d10_surface_map.py",
    "tools/verify_derivation_matrix.py",
    "tools/verify_g0_core.py",
    "tools/build_g0_manifest.py",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row_count(path: Path) -> int | None:
    if path.suffix != ".tsv":
        return None
    with path.open(encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.reader(handle, delimiter="\t")) - 1


def main() -> None:
    missing = [relative for relative in ARTIFACTS if not (ROOT / relative).is_file()]
    if missing:
        raise SystemExit("missing G0-Core artifacts: " + ", ".join(missing))

    artifacts = []
    for relative in ARTIFACTS:
        path = ROOT / relative
        entry: dict[str, object] = {
            "path": relative,
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }
        rows = row_count(path)
        if rows is not None:
            entry["data_rows"] = rows
        artifacts.append(entry)

    payload = {
        "schema": "xlang-g0-core-artifact-manifest-v1",
        "rust_release": "1.97.0",
        "rust_peeled_commit": "2d8144b7880597b6e6d3dfd63a9a9efae3f533d3",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }
    OUTPUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"G0-Core manifest: wrote {len(artifacts)} exact artifact records")


if __name__ == "__main__":
    main()
