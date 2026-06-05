# SciELO XML Formatter · Zoologia (Curitiba)

Upload a Word manuscript (`.docx`), review the parsed structure in a web form,
and download **SciELO Publishing Schema (SPS 1.10 / JATS 1.1) XML** ready for the
journal *Zoologia (Curitiba)*.

The parser is heuristic by design — it makes a best guess, then **you correct it
in an editable form** before XML is generated. Output is validated for SciELO's
mandatory indexable elements before download.

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PORT=8000 python3 app.py
# open http://localhost:8000
```

## Deploy to Railway

1. Push this folder to a Git repo.
2. In Railway: **New Project → Deploy from GitHub repo**, pick the repo.
3. Railway auto-detects Python (Nixpacks). Start command and health check come
   from `railway.json` (`/health`). No env vars required.
4. **Generate Domain** on the service to get a public URL.

(Or use the Railway CLI / MCP: create service → deploy → generate domain.)

## How it works

`.docx → parse → editable form → SPS XML → validate → download`

| Stage | File |
|-------|------|
| Parse docx | `docx_parser.py` |
| Review form | `templates/review.html` |
| Build XML | `xml_builder.py` |
| Validate | `validator.py` |
| Routes / glue | `app.py` |
| Journal + schema constants | `config.py` |

Journal metadata (ISSN, publisher, license, acronym) and the SPS version live in
`config.py` — edit there to retarget another SciELO journal.

## Optional: official SciELO Style Checker

Install [`packtools`](https://github.com/scieloorg/packtools) to enable the full
SciELO validation in `validator.optional_packtools_check`. It's not a default
dependency so the deploy image stays small.

## Reference

SciELO Publishing Schema guide:
https://scielo.readthedocs.io/projects/scielo-publishing-schema/
