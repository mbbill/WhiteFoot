"""Shared report comparison only; contains no semantic model logic."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any


def canonical_bytes(report: dict[str, Any]) -> bytes:
    """Encode a model report for exact deterministic comparison."""

    return json.dumps(
        report, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")


def reports_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return canonical_bytes(left) == canonical_bytes(right)


def semantic_projection(report: dict[str, Any]) -> dict[str, Any]:
    """Remove resource accounting when comparing sufficient profiles."""

    projected = deepcopy(report)
    projected.pop("resources", None)
    return projected
