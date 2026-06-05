"""Parse a .docx manuscript into the structured dict the form/XML builder use.

Heuristic, not magic: it reads paragraph styles + text patterns to guess the
title, authors, affiliations, abstract, keywords, IMRaD sections and reference
list. The result is always shown in an editable form before XML is generated,
so wrong guesses are corrected by a human rather than shipped silently.
"""
import re
from docx import Document

import config


def _is_heading(para):
    """True when a paragraph looks like a section heading."""
    style = (para.style.name or "").lower()
    if style.startswith("heading"):
        return True
    text = para.text.strip()
    if not text or len(text) > 80:
        return False
    # all-caps short line, or matches a known heading
    if text.lower() in config.SECTION_HEADINGS:
        return True
    return text.isupper() and len(text.split()) <= 6


def _split_authors(line):
    """Split an author byline into (name, superscript-affiliation-marks)."""
    authors = []
    # split on commas / 'and' / '&'
    parts = re.split(r",|\band\b|&", line)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # trailing affiliation markers: digits, *, superscript symbols
        m = re.match(r"^(.*?)[\s]*([\d\*¹²³⁰-₟,\-]+)?$", part)
        name = (m.group(1) or part).strip()
        marks = (m.group(2) or "").strip()
        aff_ids = []
        for d in re.findall(r"\d+", marks):
            aff_ids.append(f"aff{d}")
        given, surname = _split_name(name)
        authors.append({
            "given": given, "surname": surname, "orcid": "",
            "aff_ids": aff_ids, "corresp": "*" in marks, "email": "",
        })
    return authors


def _split_name(name):
    """Naive given/surname split: last token is surname."""
    toks = name.split()
    if len(toks) < 2:
        return name, ""
    return " ".join(toks[:-1]), toks[-1]


def parse(path):
    doc = Document(path)
    paras = [p for p in doc.paragraphs]
    data = {
        "lang": "en",
        "article_type": "research-article",
        "doi": "",
        "title": "",
        "trans_title": "",
        "authors": [],
        "affs": [],
        "abstract": "",
        "trans_abstract": "",
        "keywords": [],
        "trans_keywords": [],
        "received": "",
        "accepted": "",
        "license_url": config.LICENSE_URL,
        "copyright_year": "",
        "copyright_holder": config.JOURNAL["publisher_name"],
        "sections": [],
        "refs": [],
    }

    i = 0
    n = len(paras)

    # --- title = first non-empty paragraph ---------------------------------
    while i < n and not paras[i].text.strip():
        i += 1
    if i < n:
        data["title"] = paras[i].text.strip()
        i += 1

    # --- author byline = next non-empty line -------------------------------
    while i < n and not paras[i].text.strip():
        i += 1
    if i < n and not _is_heading(paras[i]):
        data["authors"] = _split_authors(paras[i].text.strip())
        i += 1

    # --- affiliations = lines starting with a number/marker ----------------
    while i < n:
        t = paras[i].text.strip()
        if not t:
            i += 1
            continue
        m = re.match(r"^[\(\[]?(\d+)[\)\].\s]+(.*)$", t)
        if m:
            data["affs"].append(_parse_aff(m.group(1), m.group(2)))
            i += 1
        else:
            break

    # --- walk remaining paragraphs, bucketing into sections ----------------
    current = {"title": "Body", "paras": []}
    in_refs = False
    in_abstract = False
    for p in paras[i:]:
        t = p.text.strip()
        if not t:
            continue
        low = t.lower()

        if low in ("abstract", "resumo"):
            in_abstract = True
            data["lang"] = "pt" if low == "resumo" else "en"
            continue
        if low.startswith("key") and "word" in low or low.startswith("palavras"):
            kws = re.sub(r"^[^:]*:", "", t).strip()
            data["keywords"] = [k.strip() for k in re.split(r"[;,]", kws) if k.strip()]
            in_abstract = False
            continue

        if _is_heading(p):
            if current["paras"]:
                data["sections"].append(current)
            if low in config.REF_HEADINGS:
                in_refs = True
                current = {"title": t, "paras": []}
                continue
            in_refs = False
            in_abstract = False
            current = {"title": t, "paras": []}
            continue

        if in_abstract:
            data["abstract"] = (data["abstract"] + " " + t).strip()
        elif in_refs:
            data["refs"].append({"label": str(len(data["refs"]) + 1), "mixed": t})
        else:
            current["paras"].append(t)

    if current["paras"]:
        data["sections"].append(current)

    return data


def _parse_aff(num, text):
    """Best-effort split of an affiliation string into institution/city/country."""
    bits = [b.strip() for b in text.split(",") if b.strip()]
    country = bits[-1] if bits else ""
    institution = bits[0] if bits else text
    city = bits[1] if len(bits) > 2 else ""
    return {
        "id": f"aff{num}", "label": num,
        "institution": institution, "city": city,
        "state": "", "country": country, "country_code": "",
        "original": text,
    }
