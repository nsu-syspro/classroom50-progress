# classroom50-progress

Student-facing progress page for the mpt classroom (classroom50):
https://nsu-syspro.github.io/classroom50-progress/

- `index.html` - the page (vanilla JS, fetches data/progress.json)
- `data/progress.json` - refreshed by `.github/workflows/publish-progress.yaml`
  (nightly at 03:00 Novosibirsk + manual dispatch)
- `publish.json` - publish knobs (mode: past-due|explicit, exclusions)
- `scripts/generate_progress.py` - the generator

Secrets: `PROGRESS_PAT` (fine-grained PAT: Contents RW, Actions RW,
Pull requests R, Members R on the org). The generator is the TA repo's
concern too - see ~/work/nsu-syspro/classroom50-review/ROADMAP.md (W7).
