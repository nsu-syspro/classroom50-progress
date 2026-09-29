#!/usr/bin/env python3
"""Compare two progress.json files ignoring volatile timestamps.

Usage: compare_progress.py NEW_FILE OLD_FILE
Exit 0 = content identical (no commit needed), 1 = different (commit),
2 = old file unreadable/invalid (treat as different).
"""

import json
import sys


def load(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def strip(doc: dict) -> None:
    doc.pop("generated_at", None)
    for assignment in doc.get("assignments", []):
        assignment.pop("collected_at", None)


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
    strip(new)
    strip(old)
    if new == old:
        print("no content changes")
        return 0
    print("content changed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
