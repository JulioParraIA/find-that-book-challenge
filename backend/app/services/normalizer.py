"""
normalizer.py
-------------
Text normalization and cleaning utilities for book search queries.

Handles preprocessing required before comparing user input against
Open Library records: lowercasing, diacritics removal, subtitle
variant handling, and punctuation stripping.
"""

import re
import unicodedata
from typing import Optional


KNOWN_VARIANTS: dict[str, list[str]] = {
    "the hobbit": ["there and back again"],
    "frankenstein": ["the modern prometheus"],
    "dracula": ["the un-dead"],
    "moby dick": ["the whale"],
    "fahrenheit 451": ["the fireman"],
}


def normalize_text(text: Optional[str]) -> str:
    """
    Applies a full normalization pipeline to the input text.

    Steps: lowercase -> remove diacritics -> strip punctuation ->
    collapse whitespace -> strip edges.
    """
    if not text:
        return ""

    result = text.lower()
    result = unicodedata.normalize("NFD", result)
    result = "".join(char for char in result if unicodedata.category(char) != "Mn")
    result = re.sub(r"[^a-z0-9\s]", "", result)
    result = re.sub(r"\s+", " ", result)
    return result.strip()


def strip_subtitle(title: str) -> str:
    """Removes subtitle from a book title (after colon, dash, or semicolon)."""
    separators = r"[:\-;–—]"
    parts = re.split(separators, title, maxsplit=1)
    return parts[0].strip()


def is_variant_match(title_a: str, title_b: str) -> bool:
    """Checks whether two titles are known variants of the same book."""
    norm_a = normalize_text(title_a)
    norm_b = normalize_text(title_b)

    if norm_a == norm_b:
        return True

    for canonical, variants in KNOWN_VARIANTS.items():
        normalized_variants = [normalize_text(v) for v in variants]
        canonical_normalized = normalize_text(canonical)
        all_forms = [canonical_normalized] + normalized_variants
        if norm_a in all_forms and norm_b in all_forms:
            return True

    return False


def compute_similarity(text_a: str, text_b: str) -> float:
    """Computes Jaccard token-based similarity between two strings."""
    tokens_a = set(normalize_text(text_a).split())
    tokens_b = set(normalize_text(text_b).split())

    if not tokens_a or not tokens_b:
        return 0.0

    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)
