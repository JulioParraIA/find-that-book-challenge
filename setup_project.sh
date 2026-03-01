#!/bin/bash
# =============================================================================
# setup_project.sh
# =============================================================================
# Creates the full project structure for Find That Book.
# Run this script from the root of the cloned repository.
#
# Usage:
#   git clone https://github.com/JulioParraIA/find-that-book-challenge.git
#   cd find-that-book-challenge
#   chmod +x setup_project.sh
#   bash setup_project.sh
#   git add .
#   git commit -m "feat: add complete backend and frontend structure"
#   git push origin main
# =============================================================================

set -e

echo "Creating project structure..."

# =============================================================================
# Directory Structure
# =============================================================================

mkdir -p backend/app/models
mkdir -p backend/app/services
mkdir -p backend/app/api
mkdir -p backend/tests
mkdir -p frontend/public
mkdir -p frontend/src/components
mkdir -p frontend/src/services
mkdir -p .github/workflows

echo "Directories created."

# =============================================================================
# Backend __init__.py files
# =============================================================================

for dir in backend/app backend/app/models backend/app/services backend/app/api backend/tests; do
  cat > "$dir/__init__.py" << 'INITEOF'
# This file marks the directory as a Python package.
INITEOF
done

echo "Python packages initialized."

# =============================================================================
# backend/app/config.py
# =============================================================================

cat > backend/app/config.py << 'PYEOF'
"""
config.py
---------
Centralized application configuration.

All settings are loaded from environment variables at startup.
Secrets (API keys, credentials) are expected to be injected via
Azure Container Apps environment variables, which can reference
Azure Key Vault secrets directly.

Environment Variables Required:
    - ANTHROPIC_API_KEY: API key for Claude (Anthropic). Stored in Azure Key Vault.
    - ALLOWED_ORIGINS: Comma-separated list of allowed CORS origins.

Environment Variables Optional:
    - LOG_LEVEL: Logging verbosity. Defaults to "INFO".
    - ANTHROPIC_MODEL: Claude model identifier. Defaults to "claude-sonnet-4-20250514".
    - OPEN_LIBRARY_BASE_URL: Base URL for Open Library API. Defaults to production.
    - MAX_CANDIDATES: Maximum number of book candidates to return. Defaults to 5.
    - REQUEST_TIMEOUT: HTTP request timeout in seconds. Defaults to 30.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Uses pydantic-settings for validation and type coercion.
    In production, these values are injected by Azure Container Apps
    and secrets are referenced from Azure Key Vault.
    """

    # ----------------------------------------------------------------
    # Secrets (stored in Azure Key Vault, referenced via App Settings)
    # ----------------------------------------------------------------
    anthropic_api_key: str

    # ----------------------------------------------------------------
    # CORS Configuration
    # ----------------------------------------------------------------
    allowed_origins: str = "http://localhost:5173"

    # ----------------------------------------------------------------
    # Claude AI Configuration
    # ----------------------------------------------------------------
    anthropic_model: str = "claude-sonnet-4-20250514"

    # ----------------------------------------------------------------
    # Open Library Configuration
    # ----------------------------------------------------------------
    open_library_base_url: str = "https://openlibrary.org"
    open_library_covers_url: str = "https://covers.openlibrary.org"

    # ----------------------------------------------------------------
    # Application Behavior
    # ----------------------------------------------------------------
    max_candidates: int = 5
    request_timeout: int = 30
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached singleton instance of application settings.

    The lru_cache decorator ensures that environment variables are read
    only once during the application lifecycle, avoiding redundant I/O
    on every request.
    """
    return Settings()
PYEOF

# =============================================================================
# backend/app/models/schemas.py
# =============================================================================

cat > backend/app/models/schemas.py << 'PYEOF'
"""
schemas.py
----------
Pydantic models defining the API request and response contracts.

These schemas serve as the single source of truth for data validation,
serialization, and API documentation (auto-generated by FastAPI).
"""

from typing import Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Incoming search request from the frontend."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Plain text search query. May contain title, author, keywords, or noise.",
        examples=["tolkien hobbit illustrated deluxe 1937", "dickens tale two cities"],
    )


class ExtractedFields(BaseModel):
    """Structured fields extracted from the messy blob by Claude AI."""
    title: Optional[str] = Field(default=None, description="Extracted or inferred book title.")
    author: Optional[str] = Field(default=None, description="Extracted or inferred author name.")
    keywords: list[str] = Field(default_factory=list, description="Additional keywords that may help identify the book.")


class BookCandidate(BaseModel):
    """A single book candidate returned to the frontend."""
    title: str = Field(..., description="Book title from Open Library.")
    author: str = Field(..., description="Primary author name. Contributors are excluded.")
    first_publish_year: Optional[int] = Field(default=None, description="Year the book was first published.")
    open_library_id: Optional[str] = Field(default=None, description="Open Library work identifier.")
    open_library_url: Optional[str] = Field(default=None, description="Direct URL to the book on Open Library.")
    cover_url: Optional[str] = Field(default=None, description="URL to the book cover image.")
    explanation: str = Field(..., description="One-sentence explanation of why this book was matched.")


class SearchResponse(BaseModel):
    """API response containing an ordered list of book candidates."""
    query: str = Field(..., description="Original query submitted by the user.")
    extracted_fields: ExtractedFields = Field(..., description="Fields extracted from the query by Claude AI.")
    candidates: list[BookCandidate] = Field(default_factory=list, description="Ordered list of book candidates.")
    total_results: int = Field(default=0, description="Total number of candidates found before truncation.")


class ErrorResponse(BaseModel):
    """Standardized error response for API consumers."""
    detail: str = Field(..., description="Human-readable error message.")
    error_code: Optional[str] = Field(default=None, description="Machine-readable error code.")
PYEOF

# =============================================================================
# backend/app/services/normalizer.py
# =============================================================================

cat > backend/app/services/normalizer.py << 'PYEOF'
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
PYEOF

# =============================================================================
# backend/app/services/ai_extractor.py
# =============================================================================

cat > backend/app/services/ai_extractor.py << 'PYEOF'
"""
ai_extractor.py
---------------
Integration layer with Claude API (Anthropic) for intelligent
field extraction from messy text blobs.

The ANTHROPIC_API_KEY is loaded from environment variables, which
in production are sourced from Azure Key Vault via Container Apps
secret references.
"""

import json
import logging
from typing import Optional

from anthropic import Anthropic, APIError, APITimeoutError

from app.config import get_settings
from app.models.schemas import ExtractedFields

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """You are a library search assistant. Your task is to extract structured fields from a messy, plain-text book search query.

The user will provide a text blob that may contain:
- A book title (full or partial)
- An author name (full or partial)
- Extra noise (edition info, year, format, etc.)
- Any combination of the above

RULES:
1. Return ONLY valid JSON. No markdown, no backticks, no explanation.
2. Use this exact schema:
   {
     "title": "extracted title or null",
     "author": "extracted author or null",
     "keywords": ["additional", "useful", "tokens"]
   }
3. If you cannot confidently identify a title or author, set the field to null.
4. The keywords array should contain any remaining tokens that might help identify the book.
5. Do NOT invent or guess information that is not present in the input.
6. Normalize author names to their most common form (e.g., "tolkien" -> "J.R.R. Tolkien").
7. If the input contains only an author name with no title, set title to null.
8. If the input contains only a title with no author, set author to null."""


async def extract_fields(query: str) -> ExtractedFields:
    """Sends the raw query to Claude and parses the structured response."""
    settings = get_settings()
    client = Anthropic(api_key=settings.anthropic_api_key)

    logger.info("Sending extraction request to Claude. Model: %s, Query length: %d", settings.anthropic_model, len(query))

    try:
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=300,
            system=EXTRACTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Extract fields from this search query: {query}"}],
        )

        raw_content = response.content[0].text
        logger.debug("Claude raw response: %s", raw_content)

        extracted = _parse_response(raw_content)
        logger.info("Extraction successful. Title: %s, Author: %s, Keywords: %s", extracted.title, extracted.author, extracted.keywords)
        return extracted

    except (APIError, APITimeoutError) as exc:
        logger.error("Claude API error: %s", str(exc))
        raise ExtractionError(f"Claude API request failed: {str(exc)}") from exc
    except Exception as exc:
        logger.error("Unexpected error during extraction: %s", str(exc))
        raise ExtractionError(f"Field extraction failed: {str(exc)}") from exc


def _parse_response(raw_content: str) -> ExtractedFields:
    """Parses Claude's raw text response into an ExtractedFields object."""
    cleaned = raw_content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        return ExtractedFields(
            title=data.get("title"),
            author=data.get("author"),
            keywords=data.get("keywords", []),
        )
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("Failed to parse Claude response as JSON. Raw: %s. Error: %s", raw_content, str(exc))
        fallback_keywords = [token.strip() for token in raw_content.split() if token.strip()]
        return ExtractedFields(title=None, author=None, keywords=fallback_keywords)


class ExtractionError(Exception):
    """Raised when field extraction from Claude fails."""
    pass
PYEOF

# =============================================================================
# backend/app/services/open_library_client.py
# =============================================================================

cat > backend/app/services/open_library_client.py << 'PYEOF'
"""
open_library_client.py
----------------------
HTTP client for the Open Library API.

Encapsulates all interactions with Open Library search and detail endpoints.
Uses httpx for async HTTP to avoid blocking the event loop.
"""

import logging
from typing import Any, Optional

import httpx

from app.config import get_settings
from app.services.normalizer import normalize_text

logger = logging.getLogger(__name__)


class OpenLibraryClient:
    """Async HTTP client for Open Library API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.open_library_base_url
        self._covers_url = settings.open_library_covers_url
        self._timeout = settings.request_timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "OpenLibraryClient":
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers={"Accept": "application/json"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._client:
            await self._client.aclose()

    async def search_books(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Searches Open Library for books matching the given criteria."""
        params: dict[str, Any] = {
            "limit": limit,
            "fields": "key,title,author_name,author_key,first_publish_year,cover_i,edition_count,number_of_pages_median,subject,isbn",
        }

        if title and author:
            params["title"] = title
            params["author"] = author
        elif title:
            params["title"] = title
        elif author:
            params["author"] = author
        elif query:
            params["q"] = query
        else:
            return []

        try:
            response = await self._client.get("/search.json", params=params)
            response.raise_for_status()
            data = response.json()
            docs = data.get("docs", [])
            logger.info("Open Library returned %d results.", len(docs))
            return docs
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.error("Open Library request failed: %s", str(exc))
            return []

    async def get_work_details(self, work_key: str) -> Optional[dict[str, Any]]:
        """Fetches detailed information for a specific work."""
        try:
            response = await self._client.get(f"{work_key}.json")
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.error("Failed to fetch work details for %s: %s", work_key, str(exc))
            return None

    async def get_author_details(self, author_key: str) -> Optional[dict[str, Any]]:
        """Fetches author information from Open Library."""
        try:
            response = await self._client.get(f"/authors/{author_key}.json")
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.error("Failed to fetch author details for %s: %s", author_key, str(exc))
            return None

    async def get_author_works(self, author_key: str, limit: int = 10) -> list[dict[str, Any]]:
        """Fetches the top works by a given author."""
        try:
            response = await self._client.get(f"/authors/{author_key}/works.json", params={"limit": limit})
            response.raise_for_status()
            data = response.json()
            return data.get("entries", [])
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.error("Failed to fetch works for author %s: %s", author_key, str(exc))
            return []

    def build_cover_url(self, cover_id: Optional[int], size: str = "M") -> Optional[str]:
        """Constructs a cover image URL from an Open Library cover ID."""
        if not cover_id:
            return None
        return f"{self._covers_url}/b/id/{cover_id}-{size}.jpg"

    def build_work_url(self, work_key: str) -> str:
        """Constructs a public-facing URL for a work on Open Library."""
        return f"{self._base_url}{work_key}"
PYEOF

# =============================================================================
# backend/app/services/deduplicator.py
# =============================================================================

cat > backend/app/services/deduplicator.py << 'PYEOF'
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
PYEOF

# =============================================================================
# backend/app/services/matcher.py
# =============================================================================

cat > backend/app/services/matcher.py << 'PYEOF'
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
PYEOF

# =============================================================================
# backend/app/api/routes.py
# =============================================================================

cat > backend/app/api/routes.py << 'PYEOF'
"""
routes.py
---------
API route definitions for the Find That Book service.

POST /api/search - Main search endpoint.
GET /api/health  - Liveness probe for Azure Container Apps.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from app.config import get_settings
from app.models.schemas import SearchRequest, SearchResponse, ErrorResponse
from app.services.ai_extractor import extract_fields, ExtractionError
from app.services.open_library_client import OpenLibraryClient
from app.services.deduplicator import deduplicate_results
from app.services.matcher import rank_candidates

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["search"])


@router.post(
    "/search",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search for a book from a messy text query",
    responses={
        400: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def search_books(request: SearchRequest) -> SearchResponse:
    """Main search endpoint. Orchestrates the full book discovery pipeline."""
    settings = get_settings()
    query = request.query.strip()

    logger.info("Received search request. Query: '%s'", query)

    # Step 1: Extract structured fields via Claude.
    try:
        extracted = await extract_fields(query)
    except ExtractionError as exc:
        logger.error("Field extraction failed: %s", str(exc))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI extraction service unavailable: {str(exc)}")

    # Step 2: Search Open Library using extracted fields.
    try:
        async with OpenLibraryClient() as client:
            docs = await client.search_books(title=extracted.title, author=extracted.author)

            if not docs and extracted.keywords:
                fallback_query = " ".join(filter(None, [extracted.title, extracted.author] + extracted.keywords))
                logger.info("Primary search returned no results. Fallback query: '%s'", fallback_query)
                docs = await client.search_books(query=fallback_query)

            if not docs and extracted.author:
                logger.info("Fallback to author-only search for: '%s'", extracted.author)
                docs = await client.search_books(author=extracted.author)
    except Exception as exc:
        logger.error("Open Library search failed: %s", str(exc))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Book search service temporarily unavailable.")

    # Step 3: Deduplicate results.
    deduplicated = deduplicate_results(docs)

    # Step 4: Rank candidates and build response.
    candidates = rank_candidates(
        docs=deduplicated,
        extracted=extracted,
        covers_url=settings.open_library_covers_url,
        base_url=settings.open_library_base_url,
    )

    logger.info("Search complete. Query: '%s', Candidates: %d/%d", query, len(candidates), len(deduplicated))

    return SearchResponse(
        query=query,
        extracted_fields=extracted,
        candidates=candidates,
        total_results=len(deduplicated),
    )


@router.get("/health", status_code=status.HTTP_200_OK, summary="Health check endpoint")
async def health_check() -> dict:
    """Simple health check for container orchestration."""
    return {"status": "healthy", "service": "find-that-book-api"}
PYEOF

# =============================================================================
# backend/app/main.py
# =============================================================================

cat > backend/app/main.py << 'PYEOF'
"""
main.py
-------
FastAPI application entry point for the Find That Book API.

Running locally:  uvicorn app.main:app --reload --port 8000
Running in Docker: uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import router as search_router


def create_app() -> FastAPI:
    """Application factory. Creates and configures the FastAPI instance."""
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger(__name__)

    application = FastAPI(
        title="Find That Book API",
        description="Library discovery service powered by Claude AI and Open Library.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    allowed_origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    logger.info("CORS configured. Allowed origins: %s", allowed_origins)
    application.include_router(search_router)
    logger.info("Find That Book API initialized.")

    return application


app = create_app()
PYEOF

# =============================================================================
# backend/requirements.txt
# =============================================================================

cat > backend/requirements.txt << 'EOF'
# Find That Book - Backend Dependencies
fastapi==0.115.*
uvicorn[standard]==0.34.*
pydantic-settings==2.7.*
httpx==0.28.*
anthropic==0.52.*
pytest==8.3.*
pytest-asyncio==0.25.*
python-dotenv==1.1.*
EOF

# =============================================================================
# backend/Dockerfile
# =============================================================================

cat > backend/Dockerfile << 'DOCKEOF'
FROM python:3.12-slim AS dependencies
WORKDIR /tmp
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS production
RUN groupadd --system appgroup && \
    useradd --system --gid appgroup appuser
WORKDIR /app
COPY --from=dependencies /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin
COPY ./app ./app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
DOCKEOF

# =============================================================================
# backend/.env.example
# =============================================================================

cat > backend/.env.example << 'EOF'
# Secrets (Azure Key Vault in production)
ANTHROPIC_API_KEY=sk-ant-your-api-key-here

# CORS
ALLOWED_ORIGINS=http://localhost:5173

# Claude AI Configuration
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Application Behavior
MAX_CANDIDATES=5
REQUEST_TIMEOUT=30
LOG_LEVEL=INFO
EOF

# =============================================================================
# docker-compose.yml
# =============================================================================

cat > docker-compose.yml << 'EOF'
version: "3.9"

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ftb-backend
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    environment:
      - LOG_LEVEL=DEBUG
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    container_name: ftb-frontend
    ports:
      - "5173:5173"
    environment:
      - VITE_API_BASE_URL=http://localhost:8000
    depends_on:
      backend:
        condition: service_healthy
    volumes:
      - ./frontend/src:/app/src
      - ./frontend/public:/app/public
EOF

# =============================================================================
# FRONTEND FILES
# =============================================================================

cat > frontend/package.json << 'EOF'
{
  "name": "find-that-book-frontend",
  "version": "1.0.0",
  "description": "Frontend for the Find That Book library discovery application.",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.16",
    "vite": "^6.0.1"
  }
}
EOF

cat > frontend/vite.config.js << 'EOF'
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
EOF

cat > frontend/tailwind.config.js << 'EOF'
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
    },
  },
  plugins: [],
};
EOF

cat > frontend/postcss.config.js << 'EOF'
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
EOF

cat > frontend/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="Find That Book - Library discovery tool." />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
    <title>Find That Book</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
EOF

cat > frontend/src/main.jsx << 'EOF'
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./App.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);
EOF

cat > frontend/src/App.css << 'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  font-family: "Inter", system-ui, -apple-system, sans-serif;
  background-color: #0f172a;
  color: #e2e8f0;
  margin: 0;
  padding: 0;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}

*:focus-visible {
  outline: 2px solid #3b82f6;
  outline-offset: 2px;
  border-radius: 4px;
}
EOF

cat > frontend/src/services/api.js << 'EOF'
/**
 * api.js - HTTP client for the Find That Book backend API.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
const REQUEST_TIMEOUT_MS = 30000;

export async function searchBooks(query) {
  const url = `${API_BASE_URL}/api/search`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ query }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({ detail: `Status ${response.status}` }));
      throw new ApiError(errorBody.detail || `Request failed`, response.status);
    }
    return await response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof ApiError) throw error;
    if (error.name === "AbortError") throw new ApiError("Request timed out.", 408, "TIMEOUT");
    throw new ApiError("Unable to connect to the search service.", 0, "NETWORK_ERROR");
  }
}

export async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    return response.ok;
  } catch { return false; }
}

export class ApiError extends Error {
  constructor(message, statusCode, errorCode = null) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
    this.errorCode = errorCode;
  }
}
EOF

cat > frontend/src/App.jsx << 'JSXEOF'
import { useState, useCallback } from "react";
import { searchBooks, ApiError } from "./services/api.js";
import SearchBar from "./components/SearchBar.jsx";
import ResultsList from "./components/ResultsList.jsx";
import LoadingState from "./components/LoadingState.jsx";

function App() {
  const [candidates, setCandidates] = useState([]);
  const [extractedFields, setExtractedFields] = useState(null);
  const [totalResults, setTotalResults] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = useCallback(async (query) => {
    setError(null);
    setCandidates([]);
    setExtractedFields(null);
    setTotalResults(0);
    setIsLoading(true);
    setHasSearched(true);

    try {
      const response = await searchBooks(query);
      setCandidates(response.candidates || []);
      setExtractedFields(response.extracted_fields || null);
      setTotalResults(response.total_results || 0);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "An unexpected error occurred.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <div className="min-h-screen bg-slate-900">
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Find That Book</h1>
          <p className="mt-1 text-sm text-slate-400">Enter a messy description, title, author, or keywords.</p>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        <SearchBar onSearch={handleSearch} isLoading={isLoading} />

        {extractedFields && !isLoading && (
          <div className="mt-6 p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">Interpreted Query</p>
            <div className="flex flex-wrap gap-3 text-sm">
              {extractedFields.title && <span className="px-3 py-1 bg-blue-900/40 text-blue-300 border border-blue-800 rounded-full">Title: {extractedFields.title}</span>}
              {extractedFields.author && <span className="px-3 py-1 bg-green-900/40 text-green-300 border border-green-800 rounded-full">Author: {extractedFields.author}</span>}
              {extractedFields.keywords?.map((kw, i) => <span key={i} className="px-3 py-1 bg-slate-700/50 text-slate-300 border border-slate-600 rounded-full">{kw}</span>)}
            </div>
          </div>
        )}

        {error && (
          <div className="mt-6 p-4 bg-red-900/20 border border-red-800 rounded-lg text-red-300 text-sm" role="alert">
            <p className="font-medium">Search failed</p>
            <p className="mt-1 text-red-400">{error}</p>
          </div>
        )}

        {isLoading && <div className="mt-8"><LoadingState /></div>}

        {!isLoading && candidates.length > 0 && (
          <div className="mt-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-slate-200">Results</h2>
              <span className="text-xs text-slate-500">Showing {candidates.length} of {totalResults} matches</span>
            </div>
            <ResultsList candidates={candidates} />
          </div>
        )}

        {!isLoading && hasSearched && candidates.length === 0 && !error && (
          <div className="mt-12 text-center">
            <p className="text-slate-500 text-sm">No books found. Try rephrasing your query.</p>
          </div>
        )}
      </main>

      <footer className="border-t border-slate-800 mt-16">
        <div className="max-w-4xl mx-auto px-4 py-6 text-center">
          <p className="text-xs text-slate-600">Powered by Claude AI and Open Library. Built for the CBTW Technical Challenge.</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
JSXEOF

cat > frontend/src/components/SearchBar.jsx << 'JSXEOF'
import { useState, useCallback } from "react";

const EXAMPLE_QUERIES = [
  "dickens tale two cities",
  "tolkien hobbit illustrated deluxe 1937",
  "mark huckleberry",
  "austen bennet pride",
  "orwell animal political allegory",
];

function SearchBar({ onSearch, isLoading }) {
  const [query, setQuery] = useState("");

  const handleSubmit = useCallback(() => {
    const trimmed = query.trim();
    if (trimmed.length === 0) return;
    onSearch(trimmed);
  }, [query, onSearch]);

  const handleKeyDown = useCallback((event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      handleSubmit();
    }
  }, [handleSubmit]);

  return (
    <div>
      <div className="relative">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          placeholder="Describe the book you are looking for..."
          rows={3}
          maxLength={500}
          className="w-full px-4 py-3 rounded-lg resize-none bg-slate-800 border border-slate-700 text-slate-100 placeholder-slate-500 text-sm leading-relaxed transition-colors duration-150 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Book search query"
        />
        <span className="absolute bottom-2 right-3 text-xs text-slate-600">{query.length}/500</span>
      </div>

      <div className="mt-3 flex items-center justify-between">
        <p className="text-xs text-slate-600">Press Ctrl+Enter to search</p>
        <button
          onClick={handleSubmit}
          disabled={isLoading || query.trim().length === 0}
          className="px-6 py-2 rounded-lg text-sm font-medium transition-all duration-150 bg-blue-600 text-white hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed"
        >
          {isLoading ? "Searching..." : "Search"}
        </button>
      </div>

      <div className="mt-4">
        <p className="text-xs text-slate-600 mb-2">Try an example:</p>
        <div className="flex flex-wrap gap-2">
          {EXAMPLE_QUERIES.map((example, i) => (
            <button key={i} onClick={() => setQuery(example)} disabled={isLoading}
              className="px-3 py-1 rounded-full text-xs bg-slate-800 border border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-300 transition-colors duration-150 disabled:opacity-50">
              {example}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default SearchBar;
JSXEOF

cat > frontend/src/components/BookCard.jsx << 'JSXEOF'
import { useState, useCallback } from "react";

function CoverPlaceholder() {
  return (
    <div className="w-full h-full bg-slate-700 flex items-center justify-center rounded">
      <svg className="w-10 h-10 text-slate-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
      </svg>
    </div>
  );
}

function BookCard({ candidate, rank }) {
  const [imageError, setImageError] = useState(false);
  const handleImageError = useCallback(() => setImageError(true), []);
  const hasCover = candidate.cover_url && !imageError;

  return (
    <article className="flex gap-4 p-4 rounded-lg bg-slate-800/60 border border-slate-700/50 hover:border-slate-600 transition-colors duration-150" role="listitem">
      <div className="flex-shrink-0 w-6 pt-1">
        <span className="text-xs font-mono text-slate-600 select-none">{String(rank).padStart(2, "0")}</span>
      </div>
      <div className="flex-shrink-0 w-20 h-28 overflow-hidden rounded">
        {hasCover
          ? <img src={candidate.cover_url} alt={`Cover of ${candidate.title}`} onError={handleImageError} className="w-full h-full object-cover" loading="lazy" />
          : <CoverPlaceholder />}
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="text-base font-semibold text-slate-100 leading-tight truncate">{candidate.title}</h3>
        <p className="mt-1 text-sm text-slate-400">
          {candidate.author}
          {candidate.first_publish_year && <span className="text-slate-600"> &middot; {candidate.first_publish_year}</span>}
        </p>
        <p className="mt-2 text-xs text-slate-500 leading-relaxed">{candidate.explanation}</p>
        {candidate.open_library_url && (
          <a href={candidate.open_library_url} target="_blank" rel="noopener noreferrer"
            className="inline-block mt-2 text-xs text-blue-400 hover:text-blue-300 transition-colors duration-150">
            View on Open Library &rarr;
          </a>
        )}
      </div>
    </article>
  );
}

export default BookCard;
JSXEOF

cat > frontend/src/components/ResultsList.jsx << 'JSXEOF'
import BookCard from "./BookCard.jsx";

function ResultsList({ candidates }) {
  if (!candidates || candidates.length === 0) return null;

  return (
    <div className="space-y-3" role="list" aria-label="Book search results">
      {candidates.map((candidate, index) => (
        <BookCard key={candidate.open_library_id || index} candidate={candidate} rank={index + 1} />
      ))}
    </div>
  );
}

export default ResultsList;
JSXEOF

cat > frontend/src/components/LoadingState.jsx << 'JSXEOF'
const SKELETON_COUNT = 5;

function SkeletonCard() {
  return (
    <div className="flex gap-4 p-4 rounded-lg bg-slate-800/60 border border-slate-700/50 animate-pulse" aria-hidden="true">
      <div className="flex-shrink-0 w-6 pt-1"><div className="h-3 w-5 bg-slate-700 rounded" /></div>
      <div className="flex-shrink-0 w-20 h-28 bg-slate-700 rounded" />
      <div className="flex-1 space-y-3">
        <div className="h-4 w-3/4 bg-slate-700 rounded" />
        <div className="h-3 w-1/2 bg-slate-700/60 rounded" />
        <div className="space-y-1.5 pt-1">
          <div className="h-2.5 w-full bg-slate-700/40 rounded" />
          <div className="h-2.5 w-2/3 bg-slate-700/40 rounded" />
        </div>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="space-y-3" role="status" aria-label="Loading search results">
      <span className="sr-only">Searching for books...</span>
      {Array.from({ length: SKELETON_COUNT }, (_, i) => <SkeletonCard key={i} />)}
    </div>
  );
}

export default LoadingState;
JSXEOF

cat > frontend/Dockerfile.dev << 'EOF'
FROM node:20-slim
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
EOF

cat > frontend/public/favicon.svg << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"/>
</svg>
EOF

# =============================================================================
# Done
# =============================================================================

echo ""
echo "======================================"
echo "  Project structure created!"
echo "======================================"
echo ""
echo "Next steps:"
echo "  git add ."
echo "  git commit -m 'feat: add complete backend and frontend structure'"
echo "  git push origin main"
echo ""