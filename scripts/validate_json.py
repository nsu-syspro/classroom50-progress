#!/usr/bin/env python3
"""Validate all JSON data/config files against the schemas in schemas/.

Files checked (any classroom directory):
  - <classroom>/publish.json          -> schemas/publish.schema.json
  - <classroom>/data/progress.json    -> schemas/progress.schema.json
  - classrooms.json                   -> schemas/classrooms.schema.json

Requires the jsonschema package (pip install jsonschema); the validate
workflow installs it. Exit 0 = all valid, 1 = validation errors.
"""

import glob
import json
import os
import sys

try:
    import jsonschema
except ImportError:
    print("error: jsonschema is required (pip install jsonschema)", file=sys.stderr)
    sys.exit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMAS = os.path.join(ROOT, "schemas")

CHECKS = [
    ("*/publish.json", "publish.schema.json"),
    ("*/data/progress.json", "progress.schema.json"),
    ("classrooms.json", "classrooms.schema.json"),
]


def main() -> int:
    validator_cls = jsonschema.Draft202012Validator
    failed = 0
    checked = 0
    for pattern, schema_name in CHECKS:
        with open(os.path.join(SCHEMAS, schema_name), encoding="utf-8") as fh:
            schema = json.load(fh)
        validator = validator_cls(schema)
        paths = sorted(glob.glob(os.path.join(ROOT, pattern)))
        if not paths and pattern == "classrooms.json":
            continue  # may not exist before the first publish
        for path in paths:
            rel = os.path.relpath(path, ROOT)
            checked += 1
            try:
                with open(path, encoding="utf-8") as fh:
                    doc = json.load(fh)
                validator.validate(doc)
                print(f"ok       {rel}")
            except (OSError, json.JSONDecodeError) as exc:
                failed += 1
                print(f"INVALID  {rel}: {exc}")
            except jsonschema.ValidationError as exc:
                failed += 1
                where = list(exc.absolute_path)
                loc = " -> ".join(str(p) for p in where) or "(root)"
                print(f"INVALID  {rel} at {loc}: {exc.message}")
    print(f"{checked} file(s) checked, {failed} invalid")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
