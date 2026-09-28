"""Wikipedia helpers shared by scripts/dex-enrich.py and scripts/game-enrich.py.

One rule for how a Wikipedia summary is abridged — two or three sentences,
two if three run past 480 characters — so a species page and a game page
quote their source the same way, and a fix to the sentence splitter reaches
both. Standard library only; the HTTP getter is passed in, so each script keeps
its own User-Agent, delay and retry policy.
"""

import re
import urllib.parse

# A chunk ending like this is an abbreviation, not a sentence end — without
# this, "…including L. a. agilis" gets cut to "…including L. a."
_ABBREV_END = re.compile(
    r"(?:^|\s)(?:[A-Za-z]|sp|ssp|subsp|var|cf|etc|ca|vs|approx|Dr|St|bzw|ggf|u|z|d)\.$"
)


def split_sentences(text):
    chunks = re.split(r"(?<=[.!?])\s+", text)
    out = []
    for chunk in chunks:
        if out and _ABBREV_END.search(out[-1]):
            out[-1] = f"{out[-1]} {chunk}"
        else:
            out.append(chunk)
    return out


def trim_extract(extract):
    """Abridge a Wikipedia summary extract: the first three sentences, or two if
    three run past 480 characters. "" for anything under 50 characters, which is
    a stub or a disambiguation line rather than a description."""
    extract = (extract or "").strip()
    if len(extract) < 50:
        return ""
    sentences = split_sentences(extract)
    text = " ".join(sentences[:3])
    if len(text) > 480:
        text = " ".join(sentences[:2])
    return text


def article_url(title, lang):
    return f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'), safe='')}"


def wikipedia_summary(title, lang, get):
    """The abridged summary of `title` on <lang>.wikipedia.org, or "".
    `get(url)` returns parsed JSON or None."""
    if not title:
        return ""
    quoted = urllib.parse.quote(title.replace(" ", "_"), safe="")
    data = get(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quoted}")
    if not data:
        return ""
    return trim_extract(data.get("extract"))
