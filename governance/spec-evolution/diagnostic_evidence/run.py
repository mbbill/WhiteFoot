#!/usr/bin/env python3
"""Run every bounded evidence case through both independent models."""

from __future__ import annotations

import hashlib
import json
import sys

import model_ledger
import model_relational
from cases import all_cases
from report import canonical_bytes, reports_equal


FROZEN_REPORT_SHA256 = "94b2b33e0bad33b66eb85c88e2d5c5bc3129e334530a0477d40574b5604db397"


def agreed_report_digest() -> tuple[int, str]:
    """Return the case count and digest, rejecting any model disagreement."""

    reports = []
    for case in all_cases():
        ledger = model_ledger.run(case)
        relational = model_relational.run(case)
        if not reports_equal(ledger, relational):
            raise RuntimeError(
                f"model disagreement: {case['name']}\n"
                + json.dumps({"ledger": ledger, "relational": relational}, indent=2)
            )
        reports.append({"name": case["name"], "report": ledger})
    encoded = canonical_bytes({"cases": reports})
    return len(reports), hashlib.sha256(encoded).hexdigest()


def main() -> int:
    try:
        case_count, report_sha256 = agreed_report_digest()
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    if report_sha256 != FROZEN_REPORT_SHA256:
        print(
            "frozen diagnostic-evidence report mismatch: "
            f"expected {FROZEN_REPORT_SHA256}, got {report_sha256}",
            file=sys.stderr,
        )
        return 1
    print(
        json.dumps(
            {
                "abstract_role_streams": True,
                "case_count": case_count,
                "models": ["ordered-ledger", "pairwise-visibility-relation"],
                "report_sha256": report_sha256,
                "status": "agree",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
