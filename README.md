# classroom50-progress

Student-facing progress pages for classroom50 classrooms:

- mpt: https://nsu-syspro.github.io/classroom50-progress/mpt/

Layout (per classroom `<slug>`):

- `<slug>/index.html` - the page (vanilla JS, fetches `<slug>/data/progress.json`)
- `<slug>/data/progress.json` - refreshed by the publish workflow (nightly
  03:00 Novosibirsk + manual dispatch); committed only when the content
  (scores / review states) actually changes
- `<slug>/publish.json` - publish knobs (mode: past-due|explicit, exclusions)

Shared: `scripts/generate_progress.py` (classroom selected via PROGRESS_CLASSROOM,
default mpt), `.github/workflows/publish-progress.yaml`.

Secrets: `PROGRESS_PAT` (fine-grained PAT: Contents RW, Actions RW,
Pull requests R, Members R on the org).
