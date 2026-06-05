"""Journal defaults and SPS constants.

Values here are pre-filled into the review form. They are editable per
submission, so override them in the UI when a manuscript needs different data.
Zoologia (Curitiba) defaults are taken from the journal's SciELO record.
"""

SPS_VERSION = "sps-1.10"
DTD_VERSION = "1.1"
DTD_PUBLIC = "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.1 20151215//EN"
DTD_SYSTEM = "https://jats.nlm.nih.gov/publishing/1.1/JATS-journalpublishing1.dtd"

# --- Zoologia (Curitiba) journal metadata -----------------------------------
JOURNAL = {
    "title": "Zoologia (Curitiba)",
    "abbrev": "Zoologia (Curitiba)",
    "nlm_ta": "Zoologia (Curitiba)",
    "publisher_id": "zool",          # SciELO acronym, used in file naming
    "issn_epub": "1984-4689",        # electronic
    "issn_ppub": "1984-4670",        # print
    "publisher_name": "Sociedade Brasileira de Zoologia",
}

# --- Default license (Zoologia uses CC-BY) ----------------------------------
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
LICENSE_TYPE = "open-access"

# Standard IMRaD-style sections expected in a Zoologia research article.
# Parser uses these to detect section boundaries (case-insensitive, EN + PT).
SECTION_HEADINGS = [
    "introduction", "introdução",
    "material and methods", "materials and methods", "material e métodos",
    "results", "resultados",
    "discussion", "discussão",
    "conclusion", "conclusions", "conclusão", "conclusões",
    "taxonomy", "taxonomia", "systematics", "sistemática",
    "acknowledgments", "acknowledgements", "agradecimentos",
    "literature cited", "references", "referências",
]

# Headings that mark the start of the reference list.
REF_HEADINGS = {"literature cited", "references", "referências", "bibliography"}

# article-type options offered in the form (JATS @article-type values).
ARTICLE_TYPES = [
    "research-article", "review-article", "short-communication",
    "case-report", "editorial", "letter", "correction", "retraction",
]
