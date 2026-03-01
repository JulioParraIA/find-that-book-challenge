"""
test_api.py
-----------
Integration tests for the /api/search and /api/health endpoints.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.models.schemas import ExtractedFields


# ----------------------------------------------------------------
# Health endpoint
# ----------------------------------------------------------------

class TestHealthEndpoint:
    """Tests for GET /api/health."""

    @patch("app.config.get_settings")
    def test_health_returns_200(self, mock_get_settings):
        mock_settings = MagicMock()
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.allowed_origins = "http://localhost:5173"
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings

        from app.main import app
        client = TestClient(app)
        response = client.get("/api/health")
        assert response.status_code == 200

    @patch("app.config.get_settings")
    def test_health_response_body(self, mock_get_settings):
        mock_settings = MagicMock()
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.allowed_origins = "http://localhost:5173"
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings

        from app.main import app
        client = TestClient(app)
        response = client.get("/api/health")
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "find-that-book-api"


# ----------------------------------------------------------------
# Search endpoint - validation
# ----------------------------------------------------------------

class TestSearchValidation:
    """Tests for input validation on POST /api/search."""

    @patch("app.config.get_settings")
    def test_empty_query_returns_422(self, mock_get_settings):
        mock_settings = MagicMock()
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.allowed_origins = "http://localhost:5173"
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings

        from app.main import app
        client = TestClient(app)
        response = client.post("/api/search", json={"query": ""})
        assert response.status_code == 422

    @patch("app.config.get_settings")
    def test_missing_query_returns_422(self, mock_get_settings):
        mock_settings = MagicMock()
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.allowed_origins = "http://localhost:5173"
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings

        from app.main import app
        client = TestClient(app)
        response = client.post("/api/search", json={})
        assert response.status_code == 422

    @patch("app.config.get_settings")
    def test_query_too_long_returns_422(self, mock_get_settings):
        mock_settings = MagicMock()
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.allowed_origins = "http://localhost:5173"
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings

        from app.main import app
        client = TestClient(app)
        response = client.post("/api/search", json={"query": "x" * 501})
        assert response.status_code == 422

    @patch("app.config.get_settings")
    def test_get_method_not_allowed(self, mock_get_settings):
        mock_settings = MagicMock()
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.allowed_origins = "http://localhost:5173"
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings

        from app.main import app
        client = TestClient(app)
        response = client.get("/api/search")
        assert response.status_code == 405


# ----------------------------------------------------------------
# Search endpoint - successful flow
# ----------------------------------------------------------------

class TestSearchEndpoint:
    """Tests for the full search flow with mocked dependencies."""

    @patch("app.services.matcher.get_settings")
    @patch("app.config.get_settings")
    @patch("app.api.routes.extract_fields")
    @patch("app.api.routes.OpenLibraryClient")
    def test_successful_search(self, mock_ol_class, mock_extract, mock_get_settings, mock_matcher_settings):
        mock_settings = MagicMock()
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.allowed_origins = "http://localhost:5173"
        mock_settings.log_level = "INFO"
        mock_settings.open_library_base_url = "https://openlibrary.org"
        mock_settings.open_library_covers_url = "https://covers.openlibrary.org"
        mock_settings.max_candidates = 5
        mock_get_settings.return_value = mock_settings
        mock_matcher_settings.return_value = mock_settings

        mock_extract.return_value = ExtractedFields(
            title="The Hobbit", author="J.R.R. Tolkien", keywords=[]
        )

        mock_client = AsyncMock()
        mock_client.search_books.return_value = [
            {
                "key": "/works/OL27479W",
                "title": "The Hobbit",
                "author_name": ["J.R.R. Tolkien"],
                "first_publish_year": 1937,
                "cover_i": 12345,
                "edition_count": 200,
            }
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_ol_class.return_value = mock_client

        from app.main import app
        client = TestClient(app)
        response = client.post("/api/search", json={"query": "tolkien hobbit"})

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "tolkien hobbit"
        assert data["extracted_fields"]["title"] == "The Hobbit"
        assert len(data["candidates"]) > 0
        assert data["total_results"] >= 1

    @patch("app.config.get_settings")
    @patch("app.api.routes.extract_fields")
    def test_extraction_failure_returns_502(self, mock_extract, mock_get_settings):
        mock_settings = MagicMock()
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.allowed_origins = "http://localhost:5173"
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings

        from app.services.ai_extractor import ExtractionError
        mock_extract.side_effect = ExtractionError("Claude API failed")

        from app.main import app
        client = TestClient(app)
        response = client.post("/api/search", json={"query": "tolkien hobbit"})
        assert response.status_code == 502

    @patch("app.services.matcher.get_settings")
    @patch("app.config.get_settings")
    @patch("app.api.routes.extract_fields")
    @patch("app.api.routes.OpenLibraryClient")
    def test_no_results_returns_empty_candidates(self, mock_ol_class, mock_extract, mock_get_settings, mock_matcher_settings):
        mock_settings = MagicMock()
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.allowed_origins = "http://localhost:5173"
        mock_settings.log_level = "INFO"
        mock_settings.open_library_base_url = "https://openlibrary.org"
        mock_settings.open_library_covers_url = "https://covers.openlibrary.org"
        mock_settings.max_candidates = 5
        mock_get_settings.return_value = mock_settings
        mock_matcher_settings.return_value = mock_settings

        mock_extract.return_value = ExtractedFields(title="xyznonexistent", author=None, keywords=[])

        mock_client = AsyncMock()
        mock_client.search_books.return_value = []
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_ol_class.return_value = mock_client

        from app.main import app
        client = TestClient(app)
        response = client.post("/api/search", json={"query": "xyznonexistent"})

        assert response.status_code == 200
        data = response.json()
        assert data["candidates"] == []
        assert data["total_results"] == 0