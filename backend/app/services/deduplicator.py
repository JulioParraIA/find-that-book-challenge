"""
deduplicator.py
---------------
Deduplication and primary author resolution for Open Library results.

Groups search results by canonical work, selects the best representative
edition, and resolves primary authors from contributor lists.
"""

import logging
from typing import Any

from app.services.normalizer import normalize_text

logger = logging.getLogger(__name__)

CONTRIBUTOR_INDICATORS = [
    "illustrat", "editor", "translator", "adaptor", "adapted",
    "foreword", "introduction", "afterword", "compiled", "compiler",
    "narrator", "abridged",
]


def deduplicate_results(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Removes duplicate editions and consolidates results by canonical work."""
    if not docs:
        return []

    work_groups: dict[str, list[dict[str, Any]]] = {}
    for doc in docs:
        work_key = doc.get("key", "")
        if not work_key:
            work_groups[f"_unknown_{id(doc)}"] = [doc]
            continue
        if work_key not in work_groups:
            work_groups[work_key] = []
        work_groups[work_key].append(doc)

    deduplicated = []
    for work_key, editions in work_groups.items():
        best = _select_best_edition(editions)
        deduplicated.append(best)

    logger.info("Deduplication: %d documents reduced to %d unique works.", len(docs), len(deduplicated))
    return deduplicated


def _select_best_edition(editions: list[dict[str, Any]]) -> dict[str, Any]:
    """Selects the best representative edition from a group of duplicates."""
    if len(editions) == 1:
        return editions[0]

    def score_edition(doc: dict[str, Any]) -> int:
        score = 0
        if doc.get("cover_i"):
            score += 10
        if doc.get("first_publish_year"):
            score += 5
        if doc.get("author_name"):
            score += 3
        score += min(doc.get("edition_count", 0), 50)
        return score

    return max(editions, key=score_edition)


def resolve_primary_author(author_names: list[str]) -> str:
    """Identifies the primary author from a list of contributor names."""
    if not author_names:
        return "Unknown Author"
    if len(author_names) == 1:
        return author_names[0]

    primary_candidates = []
    for name in author_names:
        normalized_name = normalize_text(name)
        is_contributor = any(indicator in normalized_name for indicator in CONTRIBUTOR_INDICATORS)
        if not is_contributor:
            primary_candidates.append(name)

    if primary_candidates:
        return primary_candidates[0]
    return author_names[0]
