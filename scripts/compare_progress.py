#!/usr/bin/env python3
"""Compare two JSON files ignoring volatile timestamps.

Usage: compare_progress.py NEW_FILE OLD_FILE
Any "generated_at" or "collected_at" key anywhere in either document is
ignored, so pure clock drift does not count as a change.

Exit 0 = content identical (no commit needed), 1 = different (commit),
2 = new file unreadable (error).
"""

import json
import sys

VOLATILE = {"generated_at", "collected_at"}


def load(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def strip(node):
    if isinstance(node, dict):
        return {k: strip(v) for k, v in node.items() if k not in VOLATILE}
    if isinstance(node, list):
        return [strip(item) for item in node]
    return node


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    new = load(sys.argv[1])
    old = load(sys.argv[2])
    if new is None:
        print("error: cannot read new file", file=sys.stderr)
        return 2
    if old is None:
        print("old file missing or invalid -> content changed")
        return 1
    if strip(new) == strip(old):
        print("no content changes")
        return 0
    print("content changed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
