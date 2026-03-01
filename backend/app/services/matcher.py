"""
matcher.py
----------
Matching hierarchy and ranking engine for book candidates.

Implements the matching strategy:
    a. Exact/normalized title + primary author match (strongest).
    b. Exact/normalized title + contributor-only author (lower rank).
    c. Near-match title + author match (candidate).
    d. Author-only fallback.
    e. If no clear winner, return up to 5 ordered candidates with explanations.
"""

import logging
from typing import Any, Optional

from app.models.schemas import BookCandidate, ExtractedFields
from app.services.normalizer import normalize_text, strip_subtitle, is_variant_match, compute_similarity
from app.services.deduplicator import resolve_primary_author
from app.config import get_settings

logger = logging.getLogger(__name__)

SCORE_EXACT_TITLE: int = 100
SCORE_NEAR_TITLE: int = 60
SCORE_VARIANT_TITLE: int = 80
SCORE_PRIMARY_AUTHOR: int = 50
SCORE_CONTRIBUTOR_AUTHOR: int = 20
SCORE_YEAR_MATCH: int = 15
SCORE_KEYWORD_MATCH: int = 10
SIMILARITY_THRESHOLD: float = 0.4


def rank_candidates(
    docs: list[dict[str, Any]],
    extracted: ExtractedFields,
    covers_url: str,
    base_url: str,
) -> list[BookCandidate]:
    """Scores, ranks, and formats book candidates based on the extracted fields."""
    settings = get_settings()
    scored_candidates: list[tuple[int, BookCandidate, list[str]]] = []

    for doc in docs:
        score, explanations = _score_document(doc, extracted)
        if score <= 0:
            continue

        author_names = doc.get("author_name", [])
        primary_author = resolve_primary_author(author_names)
        explanation = "; ".join(explanations) if explanations else "General keyword match."

        cover_id = doc.get("cover_i")
        cover_url = f"{covers_url}/b/id/{cover_id}-M.jpg" if cover_id else None
        work_key = doc.get("key", "")
        open_library_url = f"{base_url}{work_key}" if work_key else None

        candidate = BookCandidate(
            title=doc.get("title", "Unknown Title"),
            author=primary_author,
            first_publish_year=doc.get("first_publish_year"),
            open_library_id=work_key,
            open_library_url=open_library_url,
            cover_url=cover_url,
            explanation=explanation,
        )
        scored_candidates.append((score, candidate, explanations))

    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    top_candidates = [candidate for _, candidate, _ in scored_candidates[:settings.max_candidates]]

    logger.info("Ranking complete. %d candidates scored, returning top %d.", len(scored_candidates), len(top_candidates))
    return top_candidates


def _score_document(doc: dict[str, Any], extracted: ExtractedFields) -> tuple[int, list[str]]:
    """Computes a composite match score for a single Open Library document."""
    score = 0
    explanations: list[str] = []

    doc_title = doc.get("title", "")
    doc_authors = doc.get("author_name", [])
    doc_year = doc.get("first_publish_year")

    if extracted.title:
        title_score, title_explanation = _match_title(extracted.title, doc_title)
        score += title_score
        if title_explanation:
            explanations.append(title_explanation)

    if extracted.author:
        author_score, author_explanation = _match_author(extracted.author, doc_authors)
        score += author_score
        if author_explanation:
            explanations.append(author_explanation)

    if extracted.keywords:
        keyword_score, keyword_explanation = _match_keywords(extracted.keywords, doc_title, doc_authors, doc_year)
        score += keyword_score
        if keyword_explanation:
            explanations.append(keyword_explanation)

    return score, explanations


def _match_title(extracted_title: str, doc_title: str) -> tuple[int, Optional[str]]:
    """Evaluates title match between extracted field and document."""
    norm_extracted = normalize_text(extracted_title)
    norm_doc = normalize_text(doc_title)
    norm_doc_stripped = normalize_text(strip_subtitle(doc_title))

    if norm_extracted == norm_doc or norm_extracted == norm_doc_stripped:
        return SCORE_EXACT_TITLE, f"Exact title match: '{doc_title}'"

    if is_variant_match(extracted_title, doc_title):
        return SCORE_VARIANT_TITLE, f"Known title variant: '{doc_title}'"

    similarity = max(
        compute_similarity(extracted_title, doc_title),
        compute_similarity(extracted_title, strip_subtitle(doc_title)),
    )
    if similarity >= SIMILARITY_THRESHOLD:
        return int(SCORE_NEAR_TITLE * similarity), f"Near title match ({similarity:.0%} similarity): '{doc_title}'"

    return 0, None


def _match_author(extracted_author: str, doc_authors: list[str]) -> tuple[int, Optional[str]]:
    """Evaluates author match between extracted field and document authors."""
    if not doc_authors:
        return 0, None

    norm_extracted = normalize_text(extracted_author)

    primary_author = doc_authors[0]
    if norm_extracted in normalize_text(primary_author):
        return SCORE_PRIMARY_AUTHOR, f"{primary_author} is primary author"

    for author in doc_authors[1:]:
        if norm_extracted in normalize_text(author):
            return SCORE_CONTRIBUTOR_AUTHOR, f"{author} listed as contributor (not primary author)"

    for author in doc_authors:
        norm_author = normalize_text(author)
        if norm_extracted in norm_author or norm_author in norm_extracted:
            return SCORE_PRIMARY_AUTHOR, f"Author match: {author}"

    return 0, None


def _match_keywords(keywords: list[str], doc_title: str, doc_authors: list[str], doc_year: Optional[int]) -> tuple[int, Optional[str]]:
    """Evaluates keyword matches against various document fields."""
    score = 0
    matched: list[str] = []
    combined_text = normalize_text(f"{doc_title} {' '.join(doc_authors)}")

    for keyword in keywords:
        norm_keyword = normalize_text(keyword)
        if not norm_keyword:
            continue
        if norm_keyword.isdigit() and doc_year:
            if int(norm_keyword) == doc_year:
                score += SCORE_YEAR_MATCH
                matched.append(f"year {norm_keyword}")
                continue
        if norm_keyword in combined_text:
            score += SCORE_KEYWORD_MATCH
            matched.append(norm_keyword)

    if matched:
        return score, f"Keyword matches: {', '.join(matched)}"
    return 0, None
