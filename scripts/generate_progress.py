#!/usr/bin/env python3
"""Generate data/progress.json for the classroom50-progress page.

Reads (via GitHub Contents API, PROGRESS_PAT):
  - <org>/<config-repo>/mpt/scores.json      (collected scores snapshot)
  - <org>/<config-repo>/mpt/assignments.json (due dates, names, max scores)
  - <org>/<config-repo>/mpt/roster.csv       (full names)
Fetches live per-student PR review states (Feedback PR #1, last APPROVED /
CHANGES_REQUESTED wins) for every (assignment, student) cell that has a
collected entry. Writes data/progress.json (schema nsu-syspro/progress/v1).

Publish knobs come from publish.json in this repo:
  {
    "mode": "past-due",            # past-due (default) | explicit
    "assignments": [],             # explicit mode: only these slugs
    "exclude_students": [],        # usernames never shown
    "show_attempts": true
  }

Exit codes: 0 ok; 1 config/data error; 2 network error.
"""

from __future__ import annotations

import csv
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

ORG = os.environ.get("PROGRESS_ORG", "nsu-syspro")
CLASSROOM = os.environ.get("PROGRESS_CLASSROOM", "mpt")
CONFIG_REPO = os.environ.get("PROGRESS_CONFIG_REPO", "classroom50")
API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = "nsu-syspro/progress/v1"


def die(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def token() -> str:
    tok = os.environ.get("PROGRESS_PAT", "").strip()
    if not tok:
        die("PROGRESS_PAT is not set")
    return tok


_TOK = token()
_HITS = 0


def api(path: str) -> tuple[int, bytes]:
    """GET; returns (http_status, body). Retries transient 5xx a few times."""
    global _HITS
    url = f"{API}/{path}" if not path.startswith("http") else path
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {_TOK}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "classroom50-progress",
        },
    )
    for attempt in range(4):
        _HITS += 1
        if _HITS % 20 == 0:
            time.sleep(1.0)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 500, 502, 503, 504) and attempt < 3:
                # 403 may be secondary rate limiting; back off and retry.
                time.sleep(2.0 * (attempt + 1))
                continue
            return exc.code, exc.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt < 3:
                time.sleep(2.0 * (attempt + 1))
                continue
            die(f"network error fetching {url}: {exc}", 2)
    return 599, b""


def raw_file(repo: str, path: str) -> bytes | None:
    """File content from <org>/<repo> at the default branch; None on 404.

    Uses the media-type raw format so the body is the file itself, and falls
    back to base64-decoding the Contents JSON envelope if a proxy/ghes ignores
    the Accept header.
    """
    enc = urllib.parse.quote(path, safe="/")
    url = f"{API}/repos/{ORG}/{repo}/contents/{enc}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {_TOK}",
            "Accept": "application/vnd.github.raw+json",
            "User-Agent": "classroom50-progress",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
            # Envelope sniff: a real assignments/scores/roster file never starts
            # with '{"name"' (scores/assignments start with '{"schema"').
            if body.startswith(b'{"name":"') or body.startswith(b'{"name": "'):
                envelope = json.loads(body)
                import base64
                return base64.b64decode(envelope.get("content", ""))
            return body
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if exc.code in (403, 500, 502, 503, 504) and attempt < 2:
                time.sleep(2.0 * (attempt + 1))
                continue
            die(f"GET {repo}/{path}: HTTP {exc.code}", 1)
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt < 2:
                time.sleep(2.0 * (attempt + 1))
                continue
            die(f"network error fetching {url}: {exc}", 2)
    return None


def parse_rfc3339(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None


def load_knobs(classroom: str) -> dict:
    path = os.path.join(ROOT, classroom, "publish.json")
    if not os.path.exists(path):
        # Sensible defaults when a classroom has no knobs file yet.
        return {"mode": "past-due", "assignments": [], "exclude_students": [],
                "show_attempts": True}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def select_assignments(entries: list[dict], knobs: dict, now: datetime) -> list[dict]:
    mode = knobs.get("mode", "past-due")
    out = []
    for entry in entries:
        slug = entry.get("slug")
        if entry.get("locked"):
            continue
        if mode == "explicit":
            if slug in (knobs.get("assignments") or []):
                out.append(entry)
            continue
        due = parse_rfc3339(entry.get("due") or "")
        if due is not None and due <= now:
            out.append(entry)
    out.sort(key=lambda e: e.get("due") or "")
    return out


def review_state(slug: str, owner: str) -> str:
    repo = f"{CLASSROOM}-{slug}-{owner}"
    status, body = api(f"repos/{ORG}/{repo}/pulls/1")
    if status == 404:
        return "no_pr"
    if status != 200:
        print(f"warning: {repo} PR fetch: HTTP {status}", file=sys.stderr)
        return "unknown"
    status, body = api(f"repos/{ORG}/{repo}/pulls/1/reviews?per_page=100")
    if status != 200:
        print(f"warning: {repo} reviews fetch: HTTP {status}", file=sys.stderr)
        return "unknown"
    decision = "unreviewed"
    try:
        for review in json.loads(body):
            state = review.get("state")
            if state in ("APPROVED", "CHANGES_REQUESTED"):
                decision = state.lower()
    except json.JSONDecodeError:
        return "unknown"
    return decision


def main() -> int:
    now = datetime.now(timezone.utc)
    knobs = load_knobs(CLASSROOM)

    assignments_raw = raw_file(CONFIG_REPO, f"{CLASSROOM}/assignments.json")
    scores_raw = raw_file(CONFIG_REPO, f"{CLASSROOM}/scores.json")
    roster_raw = raw_file(CONFIG_REPO, f"{CLASSROOM}/roster.csv")
    if assignments_raw is None or scores_raw is None:
        die(f"missing {CLASSROOM}/assignments.json or scores.json in {ORG}/{CONFIG_REPO}")

    all_assignments = json.loads(assignments_raw)["assignments"]
    published = select_assignments(all_assignments, knobs, now)
    published_slugs = {a["slug"] for a in published}

    scores = json.loads(scores_raw)["assignments"]

    names: dict[str, str] = {}
    roster_students: list[str] = []
    if roster_raw:
        for row in csv.DictReader(io.StringIO(roster_raw.decode("utf-8"))):
            username = (row.get("username") or "").strip()
            if not username:
                continue
            full = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
            names[username] = full
            if (row.get("role") or "student") == "student":
                roster_students.append(username)

    excluded = set(knobs.get("exclude_students") or [])
    # Teachers/HTA/TA on the roster are never shown.
    staff = set()
    if roster_raw:
        for row in csv.DictReader(io.StringIO(roster_raw.decode("utf-8"))):
            if (row.get("role") or "student") != "student" and row.get("username"):
                staff.add(row["username"])
    excluded |= staff

    # --- cells ---
    cells: list[dict] = []
    owners_seen: set[str] = set()
    jobs: list[tuple[str, str]] = []
    for slug in sorted(published_slugs):
        bucket = scores.get(slug) or {}
        for entry in bucket.get("entries", []):
            owner = entry.get("owner") or ""
            if owner in excluded:
                continue
            owners_seen.add(owner)
            jobs.append((slug, owner))

    with ThreadPoolExecutor(max_workers=4) as pool:
        states = dict(
            zip(
                [(s, o) for s, o in jobs],
                pool.map(lambda job: review_state(*job), jobs),
            )
        )

    for slug in sorted(published_slugs):
        bucket = scores.get(slug) or {}
        max_score = next(
            (a for a in all_assignments if a["slug"] == slug), {}
        )
        assignment_max = sum(t.get("points", 0) for t in max_score.get("tests", [])) or 10
        for entry in bucket.get("entries", []):
            owner = entry.get("owner") or ""
            if owner in excluded:
                continue
            subs = entry.get("submissions") or []
            latest = subs[0] if subs else {}
            cell = {
                "student": owner,
                "assignment": slug,
                "score": latest.get("score"),
                "max_score": latest.get("max-score") or assignment_max,
                "attempts": len(subs) if knobs.get("show_attempts", True) else None,
                "review": states.get((slug, owner), "unknown"),
                "pr_url": f"https://github.com/{ORG}/{CLASSROOM}-{slug}-{owner}/pull/1",
                "release_url": latest.get("release"),
            }
            cells.append(cell)

    students = [u for u in roster_students if u not in excluded]
    students += sorted(owners_seen - set(students) - excluded)

    doc = {
        "schema": SCHEMA,
        "classroom": CLASSROOM,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "assignments": [
            {
                "slug": a["slug"],
                "name": a.get("name") or a["slug"],
                "due": a.get("due"),
                "max_score": sum(t.get("points", 0) for t in a.get("tests", [])) or 10,
                "collected_at": (scores.get(a["slug"]) or {}).get("collected_at"),
                "submitted": len(
                    (scores.get(a["slug"]) or {}).get("entries", [])
                ),
            }
            for a in published
        ],
        "students": [
            {"username": u, "display": names.get(u) or u} for u in students
        ],
        "cells": cells,
    }

    out_path = os.path.join(ROOT, CLASSROOM, "data", "progress.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(
        f"progress.json: {len(doc['assignments'])} assignments, "
        f"{len(doc['students'])} students, {len(cells)} cells, "
        f"{_HITS} API calls"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
