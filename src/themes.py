"""Strict thematic classification of ballots, from the title of the text being voted on.

Each distinct legislative text was read and assigned a theme by hand (see themes_map.json): the
subject of the text decides, and every ballot on that text inherits the decision. A text gets a
theme only when it clearly belongs to one; texts whose subject is double (a budget mission on
justice, "l'industrie verte": economy or environment?) or outside the nine themes are left out
rather than forced into one. THEMES keeps the labels and the reading order.
"""
import json
import os
import re
import unicodedata

# Reading order of the themes; the labels are the ones used in the article.
THEMES = {
    "economy": {
        "label": "Economy & public finances",
    },
    "social": {
        "label": "Work, pensions & welfare",
    },
    "health": {
        "label": "Health & bioethics",
    },
    "environment": {
        "label": "Environment, energy & agriculture",
    },
    "security": {
        "label": "Security, justice & immigration",
    },
    "defence": {
        "label": "Defence & foreign affairs",
    },
    "institutions": {
        "label": "Institutions & democracy",
    },
    "housing": {
        "label": "Housing & urban planning",
    },
    "education": {
        "label": "Education, culture & research",
    },
}

_BILL = re.compile(r"(projet de loi|proposition de loi|proposition de resolution).*")
# Votes on the government as a whole rather than on a policy.
_CONFIDENCE = re.compile(r"motion de censure|declaration de politique generale|article 49, alinea")
# Resolutions cite the article of the Constitution they are tabled under, which is not their subject.
_PROCEDURE = re.compile(r"\(art\. 34-1 de la constitution\)")
_MAP_PATH = os.path.join(os.path.dirname(__file__), "themes_map.json")
with open(_MAP_PATH, encoding="utf-8") as _f:
    _MAP = json.load(_f)


def normalize(text):
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return text.replace("’", "'").replace("œ", "oe")


def subject(title):
    """The part of the title naming the text: amendment numbers and authors' names are dropped."""
    text = normalize(title)
    match = _BILL.search(text)
    return _PROCEDURE.sub("", match.group(0) if match else text)


def classify(title):
    """Theme key of the text this ballot is about, or None when it was left unclassified."""
    text = subject(title)
    if _CONFIDENCE.search(text):
        return None
    return _MAP.get(text)
