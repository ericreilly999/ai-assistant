#!/usr/bin/env python3
"""
Branch protection policy hook for Claude Code.

Blocks any Bash command that would push or merge directly to main/master.
Claude must always work on a feature branch and open a PR for review.
"""
import json
import subprocess
import sys
import re

try:
    data = json.load(sys.stdin)
    cmd = data.get("tool_input", {}).get("command", "")

    # Block: git push ... main  /  git push ... master  /  git push ... HEAD:main  etc.
    if re.search(r"git\s+push\b.*\b(main|master)\b", cmd):
        print(json.dumps({
            "continue": False,
            "stopReason": (
                "Branch policy violation: direct push to main/master is not allowed.\n"
                "Required workflow:\n"
                "  1. git checkout -b <feature-branch>\n"
                "  2. git push -u origin <feature-branch>\n"
                "  3. Open a PR and wait for the user's approval before merging."
            )
        }))
        sys.exit(0)

    # Block: git merge <anything> when already on main/master
    if re.search(r"git\s+merge\b", cmd):
        try:
            current = subprocess.check_output(
                ["git", "branch", "--show-current"], text=True
            ).strip()
            if current in ("main", "master"):
                print(json.dumps({
                    "continue": False,
                    "stopReason": (
                        f"Branch policy violation: cannot merge directly into '{current}'.\n"
                        "Open a PR and wait for the user's approval."
                    )
                }))
                sys.exit(0)
        except Exception:
            pass  # git not available or not in a repo — don't block

    # Block: git checkout main/master followed by merge (detect combined commands)
    if re.search(r"checkout\s+(main|master).*&&.*merge", cmd, re.DOTALL):
        print(json.dumps({
            "continue": False,
            "stopReason": (
                "Branch policy violation: chained checkout+merge into main/master is not allowed.\n"
                "Open a PR and wait for the user's approval."
            )
        }))
        sys.exit(0)

except Exception:
    pass  # Never block on hook errors — fail open
