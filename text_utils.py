"""Small text hygiene helpers for extracted web content."""

import re

_WHITESPACE = re.compile(r"\s+")
_POSSESSIVE_ARTIFACT = re.compile(r"(?<=[A-Za-z])\ufffd+s\b")


def clean_text(value: str | None) -> str:
    """Normalize whitespace and repair common encoding artifacts.

    Search snippets occasionally contain U+FFFD replacement
    characters where an apostrophe was lost (for example
    "Bachelors"). Only the possessive pattern is repaired; other
    unknown characters are left untouched rather than guessed.
    """
    if not isinstance(value, str):
        return ""

    text = value.replace("\u00a0", " ").replace("\u200b", "")
    text = _POSSESSIVE_ARTIFACT.sub("'s", text)
    text = re.sub(r"\ufffd\?{1,2}", "\u2014", text)
    text = re.sub(r"\ufffd{2,3}", "\u2014", text)
    text = text.replace("\ufffd", "")
    return _WHITESPACE.sub(" ", text).strip()


def clean_list(values: list[str] | None) -> list[str]:
    """Clean, deduplicate, and drop empty list entries."""
    if not isinstance(values, list):
        return []

    cleaned = [
        clean_text(item)
        for item in values
        if isinstance(item, str)
    ]

    return list(dict.fromkeys(item for item in cleaned if item))