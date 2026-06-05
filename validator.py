"""Lightweight validation before download.

Two layers:
  1. well-formed   - does the string parse as XML at all (lxml).
  2. required      - are SciELO's mandatory indexable elements present.

This is deliberately not the full SciELO Style Checker. To run the official
checks, install `packtools` and call `optional_packtools_check` (it degrades
gracefully when packtools is absent, so Railway deploys stay slim by default).
"""
from lxml import etree

# SciELO mandatory elements for indexable documents (SPS 1.10).
REQUIRED = {
    "article-title": ".//article-meta/title-group/article-title",
    "contrib (author)": ".//article-meta/contrib-group/contrib",
    "aff": ".//article-meta/aff",
    "permissions/license": ".//article-meta/permissions/license",
    "ref-list": ".//back/ref-list",
}

RECOMMENDED = {
    "article-id (DOI)": ".//article-meta/article-id[@pub-id-type='doi']",
    "abstract": ".//article-meta/abstract",
    "kwd-group": ".//article-meta/kwd-group",
}


def validate(xml_string):
    """Return (errors, warnings). errors block download; warnings don't."""
    errors, warnings = [], []
    try:
        root = etree.fromstring(xml_string.encode("utf-8"))
    except etree.XMLSyntaxError as e:
        return [f"XML not well-formed: {e}"], []

    for label, xpath in REQUIRED.items():
        if not root.findall(xpath):
            errors.append(f"Missing mandatory element: {label}")

    for label, xpath in RECOMMENDED.items():
        if not root.findall(xpath):
            warnings.append(f"Recommended element absent: {label}")

    # empty-content sanity checks
    for el in root.iter("article-title"):
        if not (el.text or "").strip():
            errors.append("article-title is empty")
    for el in root.iter("surname"):
        if not (el.text or "").strip():
            warnings.append("an author surname is empty")

    return errors, warnings


def optional_packtools_check(xml_bytes):
    """Run SciELO packtools style checker if installed; else return None."""
    try:
        from packtools import XMLValidator  # type: ignore
    except Exception:
        return None
    try:
        xmlvalidator = XMLValidator.parse(xml_bytes)
        _, errors = xmlvalidator.validate_style()
        return [str(e) for e in errors]
    except Exception as e:  # pragma: no cover
        return [f"packtools error: {e}"]
