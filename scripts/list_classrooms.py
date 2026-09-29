#!/usr/bin/env python3
"""List publishable classrooms as a JSON array (for the workflow matrix).

A classroom is a subdirectory containing publish.json with enabled != false.
Prints e.g. ["mpt"] to stdout.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    out = []
    for name in sorted(os.listdir(ROOT)):
        path = os.path.join(ROOT, name)
        knobs = os.path.join(path, "publish.json")
        if not os.path.isdir(path) or not os.path.exists(knobs):
            continue
        try:
            with open(knobs, encoding="utf-8") as fh:
                enabled = json.load(fh).get("enabled", True)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"warning: {knobs}: {exc}", file=sys.stderr)
            continue
        if enabled:
            out.append(name)
        else:
            print(f"{name}: disabled, excluded from matrix", file=sys.stderr)
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
