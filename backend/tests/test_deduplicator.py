"""
test_deduplicator.py
--------------------
Unit tests for deduplication and author resolution.
"""

import pytest
from app.services.deduplicator import (
    deduplicate_results,
    _select_best_edition,
    resolve_primary_author,
)


# ----------------------------------------------------------------
# deduplicate_results
# ----------------------------------------------------------------

class TestDeduplicateResults:
    """Tests for the deduplicate_results function."""

    def test_removes_duplicate_works(self):
        docs = [
            {"key": "/works/OL1W", "title": "The Hobbit", "cover_i": 123, "edition_count": 200},
            {"key": "/works/OL1W", "title": "The Hobbit", "cover_i": None, "edition_count": 10},
        ]
        result = deduplicate_results(docs)
        assert len(result) == 1

    def test_keeps_different_works(self):
        docs = [
            {"key": "/works/OL1W", "title": "The Hobbit"},
            {"key": "/works/OL2W", "title": "The Lord of the Rings"},
        ]
        result = deduplicate_results(docs)
        assert len(result) == 2

    def test_empty_list(self):
        assert deduplicate_results([]) == []

    def test_single_document(self):
        docs = [{"key": "/works/OL1W", "title": "The Hobbit"}]
        result = deduplicate_results(docs)
        assert len(result) == 1

    def test_doc_without_key_kept(self):
        docs = [
            {"title": "Unknown Book"},
            {"title": "Another Unknown"},
        ]
        result = deduplicate_results(docs)
        assert len(result) == 2

    def test_selects_best_edition_from_duplicates(self):
        docs = [
            {"key": "/works/OL1W", "title": "The Hobbit", "cover_i": None, "edition_count": 5},
            {"key": "/works/OL1W", "title": "The Hobbit", "cover_i": 123, "edition_count": 200, "first_publish_year": 1937, "author_name": ["Tolkien"]},
        ]
        result = deduplicate_results(docs)
        assert len(result) == 1
        assert result[0]["cover_i"] == 123


# ----------------------------------------------------------------
# _select_best_edition
# ----------------------------------------------------------------

class TestSelectBestEdition:
    """Tests for the _select_best_edition function."""

    def test_single_edition(self):
        editions = [{"title": "The Hobbit", "cover_i": 123}]
        result = _select_best_edition(editions)
        assert result["title"] == "The Hobbit"

    def test_prefers_edition_with_cover(self):
        editions = [
            {"title": "The Hobbit", "cover_i": None, "edition_count": 5},
            {"title": "The Hobbit", "cover_i": 123, "edition_count": 5},
        ]
        result = _select_best_edition(editions)
        assert result["cover_i"] == 123

    def test_prefers_edition_with_more_data(self):
        editions = [
            {"title": "The Hobbit", "cover_i": None},
            {"title": "The Hobbit", "cover_i": 123, "first_publish_year": 1937, "author_name": ["Tolkien"], "edition_count": 200},
        ]
        result = _select_best_edition(editions)
        assert result["cover_i"] == 123
        assert result["first_publish_year"] == 1937

    def test_prefers_higher_edition_count(self):
        editions = [
            {"title": "The Hobbit", "cover_i": 100, "edition_count": 10},
            {"title": "The Hobbit", "cover_i": 200, "edition_count": 500},
        ]
        result = _select_best_edition(editions)
        assert result["edition_count"] == 500


# ----------------------------------------------------------------
# resolve_primary_author
# ----------------------------------------------------------------

class TestResolvePrimaryAuthor:
    """Tests for the resolve_primary_author function."""

    def test_single_author(self):
        assert resolve_primary_author(["J.R.R. Tolkien"]) == "J.R.R. Tolkien"

    def test_empty_list(self):
        assert resolve_primary_author([]) == "Unknown Author"

    def test_filters_illustrator(self):
        result = resolve_primary_author(["J.R.R. Tolkien", "Alan Lee (Illustrator)"])
        assert result == "J.R.R. Tolkien"

    def test_filters_editor(self):
        result = resolve_primary_author(["Douglas Anderson (Editor)", "J.R.R. Tolkien"])
        assert result == "J.R.R. Tolkien"

    def test_filters_translator(self):
        result = resolve_primary_author(["Manuel Figueroa (Translator)", "Gabriel García Márquez"])
        assert result == "Gabriel García Márquez"

    def test_all_contributors_returns_first(self):
        result = resolve_primary_author(["Person A (Illustrator)", "Person B (Editor)"])
        assert result == "Person A (Illustrator)"

    def test_multiple_real_authors_returns_first(self):
        result = resolve_primary_author(["Neil Gaiman", "Terry Pratchett"])
        assert result == "Neil Gaiman"

    def test_narrator_filtered(self):
        result = resolve_primary_author(["Stephen Fry (Narrator)", "J.R.R. Tolkien"])
        assert result == "J.R.R. Tolkien"