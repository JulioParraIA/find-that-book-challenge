"""
conftest.py
-----------
Shared fixtures and mock clients for the test suite.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.models.schemas import ExtractedFields, BookCandidate


# ----------------------------------------------------------------
# Sample data fixtures
# ----------------------------------------------------------------

@pytest.fixture
def sample_extracted_fields():
    """Returns a typical ExtractedFields object."""
    return ExtractedFields(
        title="The Hobbit",
        author="J.R.R. Tolkien",
        keywords=["illustrated", "1937"],
    )


@pytest.fixture
def sample_extracted_fields_title_only():
    """Returns ExtractedFields with only a title."""
    return ExtractedFields(title="Frankenstein", author=None, keywords=[])


@pytest.fixture
def sample_extracted_fields_author_only():
    """Returns ExtractedFields with only an author."""
    return ExtractedFields(title=None, author="George Orwell", keywords=["animal", "political"])


@pytest.fixture
def sample_open_library_docs():
    """Returns a list of Open Library search result documents."""
    return [
        {
            "key": "/works/OL27479W",
            "title": "The Hobbit",
            "author_name": ["J.R.R. Tolkien"],
            "first_publish_year": 1937,
            "cover_i": 12345,
            "edition_count": 200,
        },
        {
            "key": "/works/OL27479W",
            "title": "The Hobbit",
            "author_name": ["J.R.R. Tolkien"],
            "first_publish_year": 1966,
            "cover_i": None,
            "edition_count": 10,
        },
        {
            "key": "/works/OL99999W",
            "title": "The Hobbit",
            "author_name": ["Charles Dixon", "J.R.R. Tolkien"],
            "first_publish_year": 1990,
            "cover_i": 67890,
            "edition_count": 5,
        },
        {
            "key": "/works/OL11111W",
            "title": "The Hobbit. 2/?",
            "author_name": ["J.R.R. Tolkien"],
            "first_publish_year": 1984,
            "cover_i": None,
            "edition_count": 3,
        },
    ]


@pytest.fixture
def sample_book_candidate():
    """Returns a single BookCandidate."""
    return BookCandidate(
        title="The Hobbit",
        author="J.R.R. Tolkien",
        first_publish_year=1937,
        open_library_id="/works/OL27479W",
        open_library_url="https://openlibrary.org/works/OL27479W",
        cover_url="https://covers.openlibrary.org/b/id/12345-M.jpg",
        explanation="Exact title match: 'The Hobbit'; J.R.R. Tolkien is primary author",
    )


# ----------------------------------------------------------------
# Mock settings fixture
# ----------------------------------------------------------------

@pytest.fixture
def mock_settings():
    """Returns a mock Settings object with test values."""
    settings = MagicMock()
    settings.anthropic_api_key = "test-api-key"
    settings.anthropic_model = "claude-sonnet-4-20250514"
    settings.open_library_base_url = "https://openlibrary.org"
    settings.open_library_covers_url = "https://covers.openlibrary.org"
    settings.max_candidates = 5
    settings.request_timeout = 30
    settings.allowed_origins = "http://localhost:5173"
    settings.log_level = "INFO"
    return settings


# ----------------------------------------------------------------
# FastAPI test client
# ----------------------------------------------------------------

@pytest.fixture
def test_client(mock_settings):
    """Creates a FastAPI TestClient with mocked settings."""
    with patch("app.config.get_settings", return_value=mock_settings):
        from app.main import app
        client = TestClient(app)
        yield client


# ----------------------------------------------------------------
# Mock Claude response fixture
# ----------------------------------------------------------------

@pytest.fixture
def mock_claude_response():
    """Returns a mock Anthropic API response."""
    response = MagicMock()
    response.content = [
        MagicMock(text='{"title": "The Hobbit", "author": "J.R.R. Tolkien", "keywords": ["illustrated", "1937"]}')
    ]
    return response