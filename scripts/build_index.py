#!/usr/bin/env python3
"""Build classrooms.json (the index-page data) from classroom directories.

For every subdirectory with publish.json where enabled != false and an
existing data/progress.json, emits an entry:
  {"slug", "title", "generated_at"}
The last publish run's outcome comes from env (LAST_RUN_CONCLUSION,
LAST_RUN_AT) so the page can show a status line linking to Actions.
Writes classrooms.json at the repo root. Exit 0 always; the workflow decides
whether anything changed.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    entries = []
    for name in sorted(os.listdir(ROOT)):
        path = os.path.join(ROOT, name)
        knobs_path = os.path.join(path, "publish.json")
        data_path = os.path.join(path, "data", "progress.json")
        if not os.path.isdir(path) or not os.path.exists(knobs_path):
            continue
        try:
            with open(knobs_path, encoding="utf-8") as fh:
                knobs = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if knobs.get("enabled") is False:
            continue
        try:
            with open(data_path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            print(f"warning: {name}: no data yet, excluded from index", file=sys.stderr)
            continue
        entries.append({
            "slug": name,
            "title": data.get("classroom_title") or name,
            "generated_at": data.get("generated_at"),
        })

    last_run = None
    if os.environ.get("LAST_RUN_CONCLUSION"):
        last_run = {
            "conclusion": os.environ["LAST_RUN_CONCLUSION"],
            "created_at": os.environ.get("LAST_RUN_AT"),
        }

    doc = {
        "schema": "nsu-syspro/progress-classrooms/v1",
        "last_run": last_run,
        "classrooms": entries,
    }
    out_path = os.path.join(ROOT, "classrooms.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"classrooms.json: {len(entries)} classrooms, last_run={last_run}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
