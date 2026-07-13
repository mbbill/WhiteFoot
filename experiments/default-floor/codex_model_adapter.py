#!/usr/bin/env python3
"""Expose one tool-free Codex CLI agent message as model stdout."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


class ModelBoundaryError(RuntimeError):
    """Codex emitted something outside the source-only, no-tool boundary."""


def extract_source(jsonl: str) -> str:
    expected = ("thread.started", "turn.started", "item.completed", "turn.completed")
    message = None
    event_count = 0
    for line_number, line in enumerate(jsonl.splitlines(), 1):
        try:
            event: Any = json.loads(line)
        except json.JSONDecodeError as error:
            raise ModelBoundaryError(f"invalid Codex JSON event on line {line_number}") from error
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            raise ModelBoundaryError(f"malformed Codex event on line {line_number}")
        event_type = event["type"]
        if event_count >= len(expected) or event_type != expected[event_count]:
            wanted = expected[event_count] if event_count < len(expected) else "end of stream"
            raise ModelBoundaryError(
                f"unexpected Codex event on line {line_number}: got {event_type}, expected {wanted}"
            )
        if event_type == "item.completed":
            item = event.get("item")
            if not isinstance(item, dict) or item.get("type") != "agent_message":
                item_type = item.get("type") if isinstance(item, dict) else None
                raise ModelBoundaryError(
                    f"Codex emitted forbidden tool/non-message item: {event_type}/{item_type}"
                )
            if not isinstance(item.get("text"), str):
                raise ModelBoundaryError("completed agent message did not contain text")
            message = item["text"]
        event_count += 1
    if event_count != len(expected):
        raise ModelBoundaryError(
            f"incomplete Codex event stream: got {event_count} events, expected {len(expected)}"
        )
    if message is None:
        raise ModelBoundaryError("Codex event stream did not contain the final agent message")
    return message


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--codex", required=True, help="absolute path to the codex executable")
    result.add_argument("--model", required=True, help="frozen Codex model identifier")
    result.add_argument("--reasoning", default="medium", help="frozen model_reasoning_effort value")
    result.add_argument("--service-tier", default="default", help="frozen Codex service_tier value")
    result.add_argument("--timeout", type=float, default=300.0)
    return result


def main() -> int:
    args = parser().parse_args()
    if args.timeout <= 0:
        print("codex adapter timeout must be positive", file=sys.stderr)
        return 2
    prompt = sys.stdin.buffer.read()
    command = [
        args.codex,
        "exec",
        "-C",
        str(Path.cwd()),
        "--skip-git-repo-check",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--json",
        "--model",
        args.model,
        "-c",
        f'model_reasoning_effort="{args.reasoning}"',
        "-c",
        f'service_tier="{args.service_tier}"',
        "--sandbox",
        "read-only",
        "-",
    ]
    try:
        completed = subprocess.run(
            command,
            input=prompt,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=args.timeout,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as error:
        if error.stdout:
            sys.stderr.buffer.write(error.stdout if isinstance(error.stdout, bytes) else error.stdout.encode())
        if error.stderr:
            sys.stderr.buffer.write(error.stderr if isinstance(error.stderr, bytes) else error.stderr.encode())
        print("codex adapter timed out", file=sys.stderr)
        return 124
    except OSError as error:
        print(f"codex adapter could not execute CLI: {error}", file=sys.stderr)
        return 127
    sys.stderr.buffer.write(completed.stderr)
    sys.stderr.write("\n--- CODEX JSONL ---\n")
    sys.stderr.buffer.write(completed.stdout)
    if completed.returncode != 0:
        print(f"codex exited {completed.returncode}", file=sys.stderr)
        return 70
    try:
        source = extract_source(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, ModelBoundaryError) as error:
        print(f"model boundary rejected the turn: {error}", file=sys.stderr)
        return 71
    sys.stdout.buffer.write(source.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
