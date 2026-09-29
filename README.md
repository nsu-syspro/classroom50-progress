# classroom50-progress

Student-facing progress pages for classroom50 classrooms:

- root: https://nsu-syspro.github.io/classroom50-progress/ (classroom list)
- mpt:  https://nsu-syspro.github.io/classroom50-progress/?classroom=mpt
  (also `/mpt/`, via a redirect stub)

One common page, one directory per classroom. The page's design and layout
are shared; classroom directories hold only JSON.

## Layout

```
index.html                       common page (list + per-classroom view)
classrooms.json                  index data (generated)
mpt/
  publish.json                   per-classroom knobs (edited by humans)
  data/progress.json             collection data (generated)
  index.html                     optional redirect stub
scripts/
  generate_progress.py           scores + roster + PR states -> progress.json
  build_index.py                 classroom dirs -> classrooms.json
  list_classrooms.py             enabled classrooms -> workflow matrix
  compare_progress.py            content comparison (timestamps ignored)
  validate_json.py               schema validation for all JSON files
schemas/
  publish.schema.json            format of <classroom>/publish.json
  progress.schema.json           format of <classroom>/data/progress.json
  classrooms.schema.json         format of classrooms.json
.github/workflows/
  publish-progress.yaml          nightly 03:00 NSK + dispatch: collect ->
                                 generate -> commit if content changed -> index
  validate-json.yaml             every push: JSON schema validation + actionlint
```

## publish.json format

Edited by humans. Full reference with per-field docs lives in
[`schemas/publish.schema.json`](schemas/publish.schema.json); keep the
`$schema` line at the top so your editor validates and autocompletes it
(VS Code and most editors do this out of the box).

```json
{
  "$schema": "../schemas/publish.schema.json",
  "enabled": true,
  "title": "ИСП",
  "mode": "past-due",
  "assignments": [],
  "exclude_students": ["aleksiwithlove"]
}
```

| Field             | Type           | Default     | Meaning |
|-------------------|----------------|-------------|---------|
| `enabled`         | bool           | (required)  | master switch: `false` = no collection, no page data refresh, hidden from the classroom list; data files stay in place |
| `title`           | string         | dir name    | display name on the page and in the list |
| `mode`            | string         | `past-due`  | `past-due`: assignments whose deadline has passed (locked ones always skipped); `explicit`: only slugs in `assignments` |
| `assignments`     | array of slugs | `[]`        | used in `explicit` mode only |
| `exclude_students`| array of names | `[]`        | usernames never shown; roster staff is excluded automatically |

## Adding a classroom

1. Create the directory with two files:

   `bash/publish.json`:
   ```json
   {
     "$schema": "../schemas/publish.schema.json",
     "enabled": true,
     "title": "Bash"
   }
   ```

   `bash/index.html` (optional redirect stub so `/bash/` works; copy as-is
   and replace the slug):
   ```html
   <!DOCTYPE html>
   <meta charset="utf-8">
   <title>bash</title>
   <script>location.replace("../?classroom=bash");</script>
   ```

2. That's it. The publish workflow's matrix is built from the directories
   (`scripts/list_classrooms.py`), so the next run collects scores, generates
   `bash/data/progress.json` and adds the classroom to the list. The
   validate workflow checks your JSON before that.

## Pausing a classroom

Set `"enabled": false` in its `publish.json`. It drops out of the matrix
(no collection, no refresh) and disappears from the classroom list; existing
`data/progress.json` stays in the repo and is simply not shown.

## Data freshness and commits

- The workflow runs nightly at 03:00 Novosibirsk (20:00 UTC) and on demand
  (Actions tab -> Publish progress -> Run workflow).
- Each run dispatches the classroom50 score collection first, so published
  scores are fresh; then regenerates progress.json.
- A commit happens **only when content changes** (scores, review states,
  students); `generated_at`/`collected_at` timestamps are ignored in the
  comparison. Whether a refresh attempt succeeded is visible in the Actions
  runs, not in the commit log.
- Review states (проверено / есть замечания / на проверке) are fetched live
  from the Feedback PRs at generation time.

## JSON format enforcement

All three JSON kinds are checked against JSON Schema (draft 2020-12) on
every push and PR (`.github/workflows/validate-json.yaml`), plus actionlint
for the workflows. `publish.json` files carry a `$schema` pointer, so
editors validate them as you type. Run the checks locally with:

```sh
python3 scripts/validate_json.py   # pip install jsonschema
```

## Secrets

`PROGRESS_PAT` - fine-grained PAT with Contents RW, Actions RW,
Pull requests R, Members R on the org. Rotated by the teacher; when it
expires the nightly run fails at the collect step (visible in Actions).
