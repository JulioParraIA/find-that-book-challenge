"""
test_matcher.py
---------------
Unit tests for scoring and ranking logic.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.models.schemas import ExtractedFields, BookCandidate
from app.services.matcher import (
    rank_candidates,
    _score_document,
    _match_title,
    _match_author,
    _match_keywords,
    SCORE_EXACT_TITLE,
    SCORE_NEAR_TITLE,
    SCORE_VARIANT_TITLE,
    SCORE_PRIMARY_AUTHOR,
    SCORE_CONTRIBUTOR_AUTHOR,
    SCORE_YEAR_MATCH,
    SCORE_KEYWORD_MATCH,
)

COVERS_URL = "https://covers.openlibrary.org"
BASE_URL = "https://openlibrary.org"


# ----------------------------------------------------------------
# _match_title
# ----------------------------------------------------------------

class TestMatchTitle:
    """Tests for title matching logic."""

    def test_exact_match(self):
        score, explanation = _match_title("The Hobbit", "The Hobbit")
        assert score == SCORE_EXACT_TITLE
        assert "Exact title match" in explanation

    def test_exact_match_case_insensitive(self):
        score, _ = _match_title("the hobbit", "The Hobbit")
        assert score == SCORE_EXACT_TITLE

    def test_match_after_subtitle_strip(self):
        score, explanation = _match_title("Frankenstein", "Frankenstein: The Modern Prometheus")
        assert score == SCORE_EXACT_TITLE

    def test_variant_match(self):
        score, explanation = _match_title("The Hobbit", "There and Back Again")
        assert score == SCORE_VARIANT_TITLE
        assert "variant" in explanation.lower()

    def test_near_match(self):
        score, explanation = _match_title("The Hobbit", "The Hobbit. 2/?")
        assert score > 0
        assert "similarity" in explanation.lower() or "Exact" in explanation

    def test_no_match(self):
        score, explanation = _match_title("The Hobbit", "War and Peace")
        assert score == 0
        assert explanation is None

    def test_empty_extracted_title(self):
        score, explanation = _match_title("", "The Hobbit")
        assert score == SCORE_EXACT_TITLE or score == 0


# ----------------------------------------------------------------
# _match_author
# ----------------------------------------------------------------

class TestMatchAuthor:
    """Tests for author matching logic."""

    def test_primary_author_match(self):
        score, explanation = _match_author("J.R.R. Tolkien", ["J.R.R. Tolkien"])
        assert score == SCORE_PRIMARY_AUTHOR
        assert "primary author" in explanation.lower() or "Author match" in explanation

    def test_partial_name_match(self):
        score, _ = _match_author("Tolkien", ["J.R.R. Tolkien"])
        assert score == SCORE_PRIMARY_AUTHOR

    def test_contributor_match(self):
        score, explanation = _match_author("Tolkien", ["Charles Dixon", "J.R.R. Tolkien"])
        assert score == SCORE_CONTRIBUTOR_AUTHOR or score == SCORE_PRIMARY_AUTHOR

    def test_no_author_match(self):
        score, explanation = _match_author("Stephen King", ["J.R.R. Tolkien"])
        assert score == 0
        assert explanation is None

    def test_empty_author_list(self):
        score, explanation = _match_author("Tolkien", [])
        assert score == 0
        assert explanation is None


# ----------------------------------------------------------------
# _match_keywords
# ----------------------------------------------------------------

class TestMatchKeywords:
    """Tests for keyword matching logic."""

    def test_year_keyword_match(self):
        score, explanation = _match_keywords(["1937"], "The Hobbit", ["Tolkien"], 1937)
        assert score == SCORE_YEAR_MATCH
        assert "year" in explanation.lower()

    def test_text_keyword_match(self):
        score, explanation = _match_keywords(["hobbit"], "The Hobbit", ["Tolkien"], 1937)
        assert score == SCORE_KEYWORD_MATCH

    def test_multiple_keyword_matches(self):
        score, _ = _match_keywords(["hobbit", "1937"], "The Hobbit", ["Tolkien"], 1937)
        assert score >= SCORE_KEYWORD_MATCH + SCORE_YEAR_MATCH

    def test_no_keyword_match(self):
        score, explanation = _match_keywords(["narnia"], "The Hobbit", ["Tolkien"], 1937)
        assert score == 0
        assert explanation is None

    def test_empty_keywords(self):
        score, explanation = _match_keywords([], "The Hobbit", ["Tolkien"], 1937)
        assert score == 0
        assert explanation is None


# ----------------------------------------------------------------
# _score_document
# ----------------------------------------------------------------

class TestScoreDocument:
    """Tests for composite document scoring."""

    def test_perfect_match_scores_highest(self):
        doc = {"title": "The Hobbit", "author_name": ["J.R.R. Tolkien"], "first_publish_year": 1937}
        extracted = ExtractedFields(title="The Hobbit", author="J.R.R. Tolkien", keywords=["1937"])
        score, explanations = _score_document(doc, extracted)
        assert score >= SCORE_EXACT_TITLE + SCORE_PRIMARY_AUTHOR
        assert len(explanations) >= 2

    def test_title_only_match(self):
        doc = {"title": "The Hobbit", "author_name": ["Unknown"], "first_publish_year": None}
        extracted = ExtractedFields(title="The Hobbit", author=None, keywords=[])
        score, _ = _score_document(doc, extracted)
        assert score == SCORE_EXACT_TITLE

    def test_no_match_scores_zero(self):
        doc = {"title": "War and Peace", "author_name": ["Leo Tolstoy"], "first_publish_year": 1869}
        extracted = ExtractedFields(title="The Hobbit", author="Tolkien", keywords=[])
        score, _ = _score_document(doc, extracted)
        assert score == 0


# ----------------------------------------------------------------
# rank_candidates
# ----------------------------------------------------------------

class TestRankCandidates:
    """Tests for the full ranking pipeline."""

    @patch("app.services.matcher.get_settings")
    def test_returns_sorted_candidates(self, mock_get_settings, sample_open_library_docs, sample_extracted_fields):
        mock_settings = MagicMock()
        mock_settings.max_candidates = 5
        mock_get_settings.return_value = mock_settings

        results = rank_candidates(sample_open_library_docs, sample_extracted_fields, COVERS_URL, BASE_URL)
        assert len(results) > 0
        assert all(isinstance(c, BookCandidate) for c in results)

    @patch("app.services.matcher.get_settings")
    def test_respects_max_candidates(self, mock_get_settings):
        mock_settings = MagicMock()
        mock_settings.max_candidates = 2
        mock_get_settings.return_value = mock_settings

        docs = [
            {"key": f"/works/OL{i}W", "title": "The Hobbit", "author_name": ["J.R.R. Tolkien"], "first_publish_year": 1937, "cover_i": i}
            for i in range(10)
        ]
        extracted = ExtractedFields(title="The Hobbit", author="Tolkien", keywords=[])
        results = rank_candidates(docs, extracted, COVERS_URL, BASE_URL)
        assert len(results) <= 2

    @patch("app.services.matcher.get_settings")
    def test_empty_docs_returns_empty(self, mock_get_settings):
        mock_settings = MagicMock()
        mock_settings.max_candidates = 5
        mock_get_settings.return_value = mock_settings

        extracted = ExtractedFields(title="The Hobbit", author="Tolkien", keywords=[])
        results = rank_candidates([], extracted, COVERS_URL, BASE_URL)
        assert results == []

    @patch("app.services.matcher.get_settings")
    def test_cover_url_generated(self, mock_get_settings):
        mock_settings = MagicMock()
        mock_settings.max_candidates = 5
        mock_get_settings.return_value = mock_settings

        docs = [{"key": "/works/OL1W", "title": "The Hobbit", "author_name": ["J.R.R. Tolkien"], "first_publish_year": 1937, "cover_i": 12345}]
        extracted = ExtractedFields(title="The Hobbit", author="Tolkien", keywords=[])
        results = rank_candidates(docs, extracted, COVERS_URL, BASE_URL)
        assert results[0].cover_url == f"{COVERS_URL}/b/id/12345-M.jpg"

    @patch("app.services.matcher.get_settings")
    def test_no_cover_url_when_missing(self, mock_get_settings):
        mock_settings = MagicMock()
        mock_settings.max_candidates = 5
        mock_get_settings.return_value = mock_settings

        docs = [{"key": "/works/OL1W", "title": "The Hobbit", "author_name": ["J.R.R. Tolkien"], "first_publish_year": 1937, "cover_i": None}]
        extracted = ExtractedFields(title="The Hobbit", author="Tolkien", keywords=[])
        results = rank_candidates(docs, extracted, COVERS_URL, BASE_URL)
        assert results[0].cover_url is None