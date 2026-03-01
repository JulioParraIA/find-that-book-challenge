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
