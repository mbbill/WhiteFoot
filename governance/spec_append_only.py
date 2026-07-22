#!/usr/bin/env python3
"""Enforce that numbered kernel specifications are append-only.

A released `spec/kernel-spec-v*.md` file must never be modified, renamed, or
deleted. Amending the language is allowed — with care — but a change batch goes
into a NEW version file, never into a released one. This is the single machine
protection over the spec; it exists because a silently edited specification is
the one drift the rest of the project cannot recover from.

    spec_append_only.py            check the working tree against HEAD
    spec_append_only.py --staged   check staged changes (pre-commit hook)

Everything DERIVED from the spec — conformance cases, the reference model, the
lexer/parser and generated syntax data, tests, and docs — must be kept
consistent with the newest version. That consistency is the agent's
responsibility and is deliberately NOT enforced here: this guard protects only
the append-only property, nothing else.
"""

from __future__ import annotations

import subprocess
import sys

SPEC_GLOB = "spec/kernel-spec-v*.md"


def released_spec_changes(staged: bool) -> list[tuple[str, str]]:
    """Return (status, path) rows where a released spec file changed."""
    base = ["--cached"] if staged else ["HEAD"]
    result = subprocess.run(
        ["git", "diff", "--name-status", *base, "--", SPEC_GLOB],
        capture_output=True,
        text=True,
        check=True,
    )
    rows: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) >= 2 and fields[0][:1] in {"M", "D", "R", "C", "T"}:
            rows.append((fields[0], fields[-1]))
    return rows


def main(argv: list[str] | None = None) -> int:
    staged = "--staged" in (argv if argv is not None else sys.argv[1:])
    violations = released_spec_changes(staged)
    if violations:
        print(
            "spec append-only violation: a released kernel specification was "
            "modified, renamed, or removed. Add a NEW version file instead:",
            file=sys.stderr,
        )
        for status, path in violations:
            print(f"  {status}\t{path}", file=sys.stderr)
        return 1
    print("spec append-only: no released kernel specification was modified or removed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
