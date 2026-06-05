"""SciELO XML formatter — Flask web app.

Flow:  upload .docx  ->  editable review form  ->  generate SPS XML  ->  download
The review form carries the entire manuscript, so the server keeps no per-user
state (safe to run multiple Railway replicas behind one domain).
"""
import io
import os
import re
import tempfile
import zipfile

from flask import (Flask, render_template, request, send_file, abort)

import config
import docx_parser
import xml_builder
import validator

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB upload cap


# --------------------------------------------------------------------------- #
#  serialisation helpers: dict <-> the plain-text blocks shown in the form
# --------------------------------------------------------------------------- #
def authors_to_text(authors):
    rows = []
    for a in authors:
        rows.append(" | ".join([
            a.get("given", ""), a.get("surname", ""), a.get("orcid", ""),
            ",".join(s.replace("aff", "") for s in a.get("aff_ids", [])),
            a.get("email", ""),
        ]))
    return "\n".join(rows)


def text_to_authors(text):
    out = []
    for line in text.splitlines():
        if not line.strip():
            continue
        f = [c.strip() for c in line.split("|")]
        f += [""] * (5 - len(f))
        aff_ids = [f"aff{d.strip()}" for d in f[3].split(",") if d.strip()]
        out.append({
            "given": f[0], "surname": f[1], "orcid": f[2],
            "aff_ids": aff_ids, "email": f[4], "corresp": bool(f[4]),
        })
    return out


def affs_to_text(affs):
    rows = []
    for a in affs:
        rows.append(" | ".join([
            a.get("id", ""), a.get("label", ""), a.get("institution", ""),
            a.get("city", ""), a.get("state", ""), a.get("country", ""),
            a.get("country_code", ""),
        ]))
    return "\n".join(rows)


def text_to_affs(text):
    out = []
    for line in text.splitlines():
        if not line.strip():
            continue
        f = [c.strip() for c in line.split("|")]
        f += [""] * (7 - len(f))
        out.append({
            "id": f[0] or f"aff{len(out) + 1}", "label": f[1],
            "institution": f[2], "city": f[3], "state": f[4],
            "country": f[5], "country_code": f[6],
        })
    return out


def sections_to_text(sections):
    blocks = []
    for s in sections:
        blocks.append("## " + s.get("title", ""))
        blocks.extend(s.get("paras", []))
    return "\n".join(blocks)


def text_to_sections(text):
    sections, current = [], None
    for line in text.splitlines():
        if line.startswith("## "):
            if current:
                sections.append(current)
            current = {"title": line[3:].strip(), "paras": []}
        elif line.strip():
            if current is None:
                current = {"title": "", "paras": []}
            current["paras"].append(line.strip())
    if current:
        sections.append(current)
    return sections


def refs_to_text(refs):
    return "\n".join(r.get("mixed", "") for r in refs)


def text_to_refs(text):
    out = []
    for line in text.splitlines():
        if line.strip():
            out.append({"label": str(len(out) + 1), "mixed": line.strip()})
    return out


def form_to_data(form):
    """Rebuild the manuscript dict from posted form fields."""
    return {
        "lang": form.get("lang", "en"),
        "article_type": form.get("article_type", "research-article"),
        "doi": form.get("doi", "").strip(),
        "title": form.get("title", "").strip(),
        "trans_title": form.get("trans_title", "").strip(),
        "authors": text_to_authors(form.get("authors", "")),
        "affs": text_to_affs(form.get("affs", "")),
        "abstract": form.get("abstract", "").strip(),
        "keywords": [k.strip() for k in form.get("keywords", "").split(",") if k.strip()],
        "received": form.get("received", "").strip(),
        "accepted": form.get("accepted", "").strip(),
        "copyright_year": form.get("copyright_year", "").strip(),
        "copyright_holder": form.get("copyright_holder", "").strip(),
        "license_url": form.get("license_url", config.LICENSE_URL).strip(),
        "sections": text_to_sections(form.get("body", "")),
        "refs": text_to_refs(form.get("refs", "")),
    }


def safe_acron_name(data):
    """SciELO-style base filename: <acron>-<surname><year>."""
    surname = (data["authors"][0]["surname"] if data.get("authors") else "doc").lower()
    surname = re.sub(r"[^a-z0-9]", "", surname) or "doc"
    year = data.get("copyright_year", "") or "0000"
    return f"{config.JOURNAL['publisher_id']}-{surname}{year}"


# --------------------------------------------------------------------------- #
#  routes
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    return render_template("index.html", journal=config.JOURNAL)


@app.route("/review", methods=["POST"])
def review():
    file = request.files.get("docx")
    if not file or not file.filename.lower().endswith(".docx"):
        return render_template("index.html", journal=config.JOURNAL,
                               error="Please upload a .docx file."), 400
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        file.save(tmp.name)
        path = tmp.name
    try:
        data = docx_parser.parse(path)
    finally:
        os.unlink(path)

    return render_template(
        "review.html",
        article_types=config.ARTICLE_TYPES,
        data=data,
        authors=authors_to_text(data["authors"]),
        affs=affs_to_text(data["affs"]),
        body=sections_to_text(data["sections"]),
        refs=refs_to_text(data["refs"]),
        keywords=", ".join(data["keywords"]),
    )


@app.route("/generate", methods=["POST"])
def generate():
    data = form_to_data(request.form)
    xml = xml_builder.build(data)
    errors, warnings = validator.validate(xml)
    return render_template(
        "result.html", xml=xml, errors=errors, warnings=warnings,
        basename=safe_acron_name(data),
    )


@app.route("/download", methods=["POST"])
def download():
    xml = request.form.get("xml", "")
    basename = re.sub(r"[^A-Za-z0-9_-]", "", request.form.get("basename", "article"))
    if not xml.strip():
        abort(400)
    if request.form.get("as_zip"):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"{basename}/{basename}.xml", xml)
        buf.seek(0)
        return send_file(buf, mimetype="application/zip",
                         as_attachment=True, download_name=f"{basename}.zip")
    return send_file(io.BytesIO(xml.encode("utf-8")), mimetype="application/xml",
                     as_attachment=True, download_name=f"{basename}.xml")


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=bool(os.environ.get("DEBUG")))
