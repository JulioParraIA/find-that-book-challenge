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
