"""
test_normalizer.py
------------------
Unit tests for text normalization functions.
"""

import pytest
from app.services.normalizer import (
    normalize_text,
    strip_subtitle,
    is_variant_match,
    compute_similarity,
)


# ----------------------------------------------------------------
# normalize_text
# ----------------------------------------------------------------

class TestNormalizeText:
    """Tests for the normalize_text function."""

    def test_lowercase_conversion(self):
        assert normalize_text("The HOBBIT") == "the hobbit"

    def test_diacritics_removal(self):
        assert normalize_text("Les Misérables") == "les miserables"
        assert normalize_text("García Márquez") == "garcia marquez"

    def test_punctuation_stripping(self):
        assert normalize_text("Hello, World!") == "hello world"
        assert normalize_text("Dr. Jekyll & Mr. Hyde") == "dr jekyll mr hyde"

    def test_whitespace_collapsing(self):
        assert normalize_text("  multiple   spaces  ") == "multiple spaces"

    def test_none_input(self):
        assert normalize_text(None) == ""

    def test_empty_string(self):
        assert normalize_text("") == ""

    def test_numbers_preserved(self):
        assert normalize_text("Fahrenheit 451") == "fahrenheit 451"

    def test_unicode_normalization(self):
        assert normalize_text("café") == "cafe"

    def test_mixed_content(self):
        result = normalize_text("  Tolkien's 'The Hobbit' (1937)  ")
        assert result == "tolkiens the hobbit 1937"


# ----------------------------------------------------------------
# strip_subtitle
# ----------------------------------------------------------------

class TestStripSubtitle:
    """Tests for the strip_subtitle function."""

    def test_colon_separator(self):
        assert strip_subtitle("Frankenstein: The Modern Prometheus") == "Frankenstein"

    def test_dash_separator(self):
        assert strip_subtitle("The Hobbit - There and Back Again") == "The Hobbit"

    def test_semicolon_separator(self):
        assert strip_subtitle("Title; Subtitle Here") == "Title"

    def test_em_dash_separator(self):
        assert strip_subtitle("Title — Subtitle") == "Title"

    def test_no_subtitle(self):
        assert strip_subtitle("The Hobbit") == "The Hobbit"

    def test_empty_string(self):
        assert strip_subtitle("") == ""

    def test_only_first_separator_split(self):
        assert strip_subtitle("A: B: C") == "A"


# ----------------------------------------------------------------
# is_variant_match
# ----------------------------------------------------------------

class TestIsVariantMatch:
    """Tests for the is_variant_match function."""

    def test_exact_match(self):
        assert is_variant_match("The Hobbit", "The Hobbit") is True

    def test_case_insensitive_match(self):
        assert is_variant_match("the hobbit", "THE HOBBIT") is True

    def test_known_variant_hobbit(self):
        assert is_variant_match("The Hobbit", "There and Back Again") is True

    def test_known_variant_frankenstein(self):
        assert is_variant_match("Frankenstein", "The Modern Prometheus") is True

    def test_known_variant_moby_dick(self):
        assert is_variant_match("Moby Dick", "The Whale") is True

    def test_no_variant_match(self):
        assert is_variant_match("The Hobbit", "Harry Potter") is False

    def test_unrelated_titles(self):
        assert is_variant_match("1984", "Animal Farm") is False


# ----------------------------------------------------------------
# compute_similarity
# ----------------------------------------------------------------

class TestComputeSimilarity:
    """Tests for the compute_similarity function."""

    def test_identical_strings(self):
        assert compute_similarity("the hobbit", "the hobbit") == 1.0

    def test_completely_different(self):
        assert compute_similarity("the hobbit", "war peace") == 0.0

    def test_partial_overlap(self):
        sim = compute_similarity("the hobbit adventure", "the hobbit")
        assert 0.0 < sim < 1.0

    def test_empty_first_string(self):
        assert compute_similarity("", "the hobbit") == 0.0

    def test_empty_second_string(self):
        assert compute_similarity("the hobbit", "") == 0.0

    def test_both_empty(self):
        assert compute_similarity("", "") == 0.0

    def test_case_insensitive(self):
        assert compute_similarity("The Hobbit", "the hobbit") == 1.0

    def test_symmetry(self):
        sim_ab = compute_similarity("hobbit adventure", "hobbit journey")
        sim_ba = compute_similarity("hobbit journey", "hobbit adventure")
        assert sim_ab == sim_ba