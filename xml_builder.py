"""Build a SciELO Publishing Schema (SPS 1.10 / JATS 1.1) XML from the dict.

Only the elements SciELO marks as mandatory for indexable documents are always
emitted (article-id DOI, title-group, contrib-group, aff, permissions,
ref-list, xref). Optional blocks are emitted when the corresponding data is
present. Output is pretty-printed UTF-8 with the JATS DOCTYPE.
"""
from lxml import etree

import config

XLINK = "http://www.w3.org/1999/xlink"
NSMAP = {"xlink": XLINK}


def _sub(parent, tag, text=None, **attrs):
    el = etree.SubElement(parent, tag, **attrs)
    if text is not None:
        el.text = text
    return el


def build(data):
    article = etree.Element(
        "article",
        nsmap=NSMAP,
        attrib={
            "{http://www.w3.org/XML/1998/namespace}lang": data.get("lang", "en"),
            "dtd-version": config.DTD_VERSION,
            "specific-use": config.SPS_VERSION,
            "article-type": data.get("article_type", "research-article"),
        },
    )

    _front(article, data)
    _body(article, data)
    _back(article, data)

    etree.indent(article, space="  ")
    doctype = (
        '<!DOCTYPE article PUBLIC "%s" "%s">' % (config.DTD_PUBLIC, config.DTD_SYSTEM)
    )
    body = etree.tostring(article, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n%s\n%s\n' % (doctype, body)


def _front(article, data):
    front = _sub(article, "front")

    # --- journal-meta ------------------------------------------------------
    jm = _sub(front, "journal-meta")
    j = config.JOURNAL
    _sub(jm, "journal-id", j["publisher_id"], **{"journal-id-type": "publisher-id"})
    jtg = _sub(jm, "journal-title-group")
    _sub(jtg, "journal-title", j["title"])
    _sub(jtg, "abbrev-journal-title", j["abbrev"], **{"abbrev-type": "publisher"})
    _sub(jm, "issn", j["issn_epub"], **{"pub-type": "epub"})
    _sub(jm, "issn", j["issn_ppub"], **{"pub-type": "ppub"})
    pub = _sub(jm, "publisher")
    _sub(pub, "publisher-name", j["publisher_name"])

    # --- article-meta ------------------------------------------------------
    am = _sub(front, "article-meta")
    if data.get("doi"):
        _sub(am, "article-id", data["doi"], **{"pub-id-type": "doi"})

    cats = _sub(am, "article-categories")
    subjg = _sub(cats, "subj-group", **{"subj-group-type": "heading"})
    _sub(subjg, "subject", _heading_for(data.get("article_type", "")))

    tg = _sub(am, "title-group")
    _sub(tg, "article-title", data.get("title", ""))
    if data.get("trans_title"):
        ttg = _sub(tg, "trans-title-group",
                   **{"{http://www.w3.org/XML/1998/namespace}lang":
                      "pt" if data.get("lang") == "en" else "en"})
        _sub(ttg, "trans-title", data["trans_title"])

    _contrib_group(am, data)

    for aff in data.get("affs", []):
        _aff(am, aff)

    _pubdates_and_permissions(am, data)

    if data.get("abstract"):
        ab = _sub(am, "abstract")
        _sub(ab, "p", data["abstract"])
    if data.get("keywords"):
        kg = _sub(am, "kwd-group",
                  **{"{http://www.w3.org/XML/1998/namespace}lang": data.get("lang", "en")})
        for k in data["keywords"]:
            _sub(kg, "kwd", k)


def _contrib_group(am, data):
    cg = _sub(am, "contrib-group")
    for a in data.get("authors", []):
        c = _sub(cg, "contrib", **{"contrib-type": "author"})
        if a.get("orcid"):
            _sub(c, "contrib-id", a["orcid"], **{"contrib-id-type": "orcid"})
        name = _sub(c, "name")
        _sub(name, "surname", a.get("surname", ""))
        _sub(name, "given-names", a.get("given", ""))
        for aid in a.get("aff_ids", []):
            _sub(c, "xref", a.get("label_for", aid.replace("aff", "")),
                 **{"ref-type": "aff", "rid": aid})
        if a.get("corresp") and a.get("email"):
            _sub(c, "email", a["email"])


def _aff(am, aff):
    el = _sub(am, "aff", id=aff["id"])
    if aff.get("label"):
        _sub(el, "label", aff["label"])
    if aff.get("institution"):
        _sub(el, "institution", aff["institution"],
             **{"content-type": "orgname"})
    if aff.get("city") or aff.get("state"):
        addr = _sub(el, "addr-line")
        if aff.get("city"):
            _sub(addr, "named-content", aff["city"], **{"content-type": "city"})
        if aff.get("state"):
            _sub(addr, "named-content", aff["state"], **{"content-type": "state"})
    if aff.get("country"):
        attrs = {}
        if aff.get("country_code"):
            attrs["country"] = aff["country_code"]
        _sub(el, "country", aff["country"], **attrs)


def _pubdates_and_permissions(am, data):
    if data.get("received") or data.get("accepted"):
        hist = _sub(am, "history")
        for kind, key in (("received", "received"), ("accepted", "accepted")):
            if data.get(key):
                _date(hist, "date", kind, data[key])

    perm = _sub(am, "permissions")
    year = data.get("copyright_year", "")
    if year:
        _sub(perm, "copyright-statement",
             "Copyright © %s %s" % (year, data.get("copyright_holder", "")))
        _sub(perm, "copyright-year", year)
        if data.get("copyright_holder"):
            _sub(perm, "copyright-holder", data["copyright_holder"])
    lic = _sub(perm, "license",
               **{"license-type": config.LICENSE_TYPE,
                  "{%s}href" % XLINK: data.get("license_url", config.LICENSE_URL)})
    lp = _sub(lic, "license-p")
    lp.text = "This is an open-access article distributed under the terms of the Creative Commons Attribution License."


def _date(parent, tag, date_type, iso):
    """iso = 'YYYY-MM-DD' (or partial)."""
    parts = (iso.split("-") + ["", "", ""])[:3]
    el = _sub(parent, tag, **{"date-type": date_type})
    y, m, d = parts
    if d:
        _sub(el, "day", d)
    if m:
        _sub(el, "month", m)
    if y:
        _sub(el, "year", y)


def _body(article, data):
    body = _sub(article, "body")
    for sec in data.get("sections", []):
        s = _sub(body, "sec")
        if sec.get("title"):
            _sub(s, "title", sec["title"])
        for para in sec.get("paras", []):
            _sub(s, "p", para)


def _back(article, data):
    refs = data.get("refs", [])
    if not refs:
        return
    back = _sub(article, "back")
    rl = _sub(back, "ref-list")
    _sub(rl, "title", "References")
    for r in refs:
        ref = _sub(rl, "ref", id="B%s" % r.get("label", ""))
        if r.get("label"):
            _sub(ref, "label", r["label"])
        _sub(ref, "mixed-citation", r.get("mixed", ""))


def _heading_for(article_type):
    mapping = {
        "research-article": "Research Article",
        "review-article": "Review Article",
        "short-communication": "Short Communication",
        "case-report": "Case Report",
        "editorial": "Editorial",
    }
    return mapping.get(article_type, "Article")
