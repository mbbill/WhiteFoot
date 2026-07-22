#!/usr/bin/env python3
"""Mock the codex exec --json event boundary."""

import sys


def main() -> int:
    args = sys.argv[1:]
    required = (
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--skip-git-repo-check",
        "--json",
        'model_reasoning_effort="medium"',
        'service_tier="default"',
    )
    if any(item not in args for item in required) or args[-1] != "-":
        return 70
    prompt = sys.stdin.read()
    if "Implement the frozen target contract." not in prompt:
        return 71
    print('{"type":"thread.started","thread_id":"mock"}')
    print('{"type":"turn.started"}')
    print('{"type":"item.completed","item":{"type":"agent_message","text":"GOOD codex final message\\n"}}')
    print('{"type":"turn.completed","usage":{}}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
