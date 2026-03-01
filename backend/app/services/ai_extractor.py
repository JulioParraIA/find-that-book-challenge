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
