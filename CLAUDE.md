# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Flask web app that converts a Word manuscript (`.docx`) into **SciELO Publishing
Schema (SPS 1.10 / JATS 1.1) XML**, pre-configured for the journal *Zoologia
(Curitiba)*. Deploys to Railway. Authoritative format reference is the official
SPS guide: https://scielo.readthedocs.io/projects/scielo-publishing-schema/

## Commands

```bash
python3 -m venv .venv && . .venv/bin/activate   # one-time
pip install -r requirements.txt
PORT=8000 python3 app.py                         # local dev (set DEBUG=1 for reload)
gunicorn app:app --bind 0.0.0.0:$PORT            # production (Railway uses this)
```

No test suite yet. Smoke-test the pipeline directly:

```bash
python3 -c "import docx_parser, xml_builder, validator; \
  d=docx_parser.parse('sample.docx'); print(xml_builder.build(d)); \
  print(validator.validate(xml_builder.build(d)))"
```

## Architecture — the pipeline

Data flows as one **manuscript dict** through four stages. Understand the dict
shape (see `docx_parser.parse` return value) before editing any stage; every
module reads/writes the same keys.

1. `docx_parser.py` — `.docx` → dict. **Heuristic**: uses paragraph styles +
   text patterns to guess title / authors / affiliations / abstract / IMRaD
   sections / references. Will mis-guess; that is expected and corrected by humans
   in stage 2. Section detection keys off `config.SECTION_HEADINGS`.
2. `templates/review.html` — dict → editable HTML form → back to dict. The form
   is the **only state**; the server keeps nothing between requests (stateless,
   safe to scale). Complex lists are serialised as plain text (see the
   `*_to_text` / `text_to_*` helpers in `app.py`): authors/affs use `|`-delimited
   rows, body uses `## Heading` lines, refs one-per-line.
3. `xml_builder.py` — dict → SPS XML string via `lxml`. Emits all SciELO-mandatory
   indexable elements unconditionally; optional blocks only when data present.
4. `validator.py` — checks well-formedness + presence of mandatory elements
   (`REQUIRED` blocks download, `RECOMMENDED` only warns). The real SciELO Style
   Checker (`packtools`) is wired in `optional_packtools_check` but **not** a
   dependency — it degrades to a no-op when absent to keep the Railway image slim.

`app.py` ties the stages to routes: `/` → `/review` (POST docx) → `/generate`
(POST form) → `/download` (POST xml, optional `.zip` package).

## Conventions that matter

- **Journal/schema constants live in `config.py`** — Zoologia ISSNs, publisher,
  acronym (`zool`), license, SPS/DTD versions. Change journals here, not inline.
- Mandatory-element lists in `validator.REQUIRED` mirror SciELO's indexable-doc
  rules. Keep them in sync with the SPS guide version named in `config.SPS_VERSION`.
- Output filename follows SciELO style: `<acronym>-<first-author-surname><year>`
  (`safe_acron_name` in `app.py`).
- When extending XML coverage, add the element in `xml_builder.py` **and** a
  matching check in `validator.py` so the form surfaces what's missing.
