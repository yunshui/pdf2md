"""Unit tests for Extractor module."""

from dataclasses import dataclass
from typing import List, Optional
from unittest.mock import Mock, MagicMock

import pytest

from pdf2md.extractor.text_extractor import TextElement, PageText, TextExtractor


class MockPage:
    """Mock pdfplumber Page for testing."""

    def __init__(self, chars: Optional[List[dict]] = None):
        self.chars = chars or []
        self.width = 595.0  # A4 width in points
        self.height = 842.0  # A4 height in points

    def extract_text(self) -> Optional[str]:
        """Mock extract_text."""
        if not self.chars:
            return None
        return " ".join(char.get("text", "") for char in self.chars)


class TestTextElement:
    """Test cases for TextElement class."""

    def test_init(self):
        """Test TextElement initialization."""
        elem = TextElement(
            text="Test",
            x0=0.0,
            y0=0.0,
            x1=100.0,
            y1=50.0,
            font_name="Arial",
            font_size=12.0,
        )
        assert elem.text == "Test"
        assert elem.width == 100.0
        assert elem.height == 50.0

    def test_width_property(self):
        """Test width property calculation."""
        elem = TextElement(text="Test", x0=10.0, y0=0.0, x1=50.0, y1=10.0)
        assert elem.width == 40.0

    def test_height_property(self):
        """Test height property calculation."""
        elem = TextElement(text="Test", x0=0.0, y0=10.0, x1=50.0, y1=30.0)
        assert elem.height == 20.0

    def test_is_heading_true(self):
        """Test is_heading returns True for heading."""
        elem = TextElement(
            text="Heading",
            x0=0.0,
            y0=0.0,
            x1=100.0,
            y1=50.0,
            font_size=16.0,
            is_bold=True,
        )
        assert elem.is_heading()

    def test_is_heading_false_small_font(self):
        """Test is_heading returns False for small font."""
        elem = TextElement(
            text="Text",
            x0=0.0,
            y0=0.0,
            x1=100.0,
            y1=50.0,
            font_size=10.0,
            is_bold=True,
        )
        assert not elem.is_heading()

    def test_is_heading_false_not_bold(self):
        """Test is_heading returns False for non-bold text."""
        elem = TextElement(
            text="Text",
            x0=0.0,
            y0=0.0,
            x1=100.0,
            y1=50.0,
            font_size=16.0,
            is_bold=False,
        )
        assert not elem.is_heading()

    def test_is_centered_true(self):
        """Test is_centered returns True for centered text."""
        elem = TextElement(
            text="Centered",
            x0=200.0,
            y0=0.0,
            x1=395.0,
            y1=50.0,
        )
        # Page width 595, center at 297.5
        # Text center: (200+395)/2 = 297.5
        assert elem.is_centered(595.0)

    def test_is_centered_false(self):
        """Test is_centered returns False for non-centered text."""
        elem = TextElement(
            text="Left aligned",
            x0=50.0,
            y0=0.0,
            x1=150.0,
            y1=50.0,
        )
        assert not elem.is_centered(595.0)


class TestPageText:
    """Test cases for PageText class."""

    def test_init(self):
        """Test PageText initialization."""
        page_text = PageText(elements=[], raw_text="")
        assert page_text.elements == []
        assert page_text.raw_text == ""

    def test_get_text_by_position(self):
        """Test getting text within bounding box."""
        elem1 = TextElement(text="Inside", x0=10, y0=10, x1=50, y1=30)
        elem2 = TextElement(text="Outside", x0=100, y0=10, x1=150, y1=30)
        page_text = PageText(elements=[elem1, elem2], raw_text="")

        result = page_text.get_text_by_position(0, 0, 60, 40)
        assert "Inside" in result
        assert "Outside" not in result

    def test_get_headings(self):
        """Test getting heading elements."""
        heading = TextElement(
            text="Heading",
            x0=0.0,
            y0=0.0,
            x1=100.0,
            y1=50.0,
            font_size=16.0,
            is_bold=True,
        )
        text = TextElement(
            text="Normal text",
            x0=0.0,
            y0=60.0,
            x1=100.0,
            y1=110.0,
            font_size=12.0,
            is_bold=False,
        )
        page_text = PageText(elements=[heading, text], raw_text="")

        headings = page_text.get_headings(min_font_size=14.0)
        assert len(headings) == 1
        assert headings[0].text == "Heading"

    def test_get_large_font_elements(self):
        """Test getting large font elements."""
        large_elem = TextElement(
            text="Large",
            x0=0.0,
            y0=0.0,
            x1=100.0,
            y1=50.0,
            font_size=18.0,
        )
        small_elem = TextElement(
            text="Small",
            x0=0.0,
            y0=60.0,
            x1=100.0,
            y1=110.0,
            font_size=10.0,
        )
        page_text = PageText(elements=[large_elem, small_elem], raw_text="")

        large = page_text.get_large_font_elements(min_font_size=16.0)
        assert len(large) == 1
        assert large[0].text == "Large"


class TestTextExtractor:
    """Test cases for TextExtractor class."""

    def test_init_default(self):
        """Test TextExtractor initialization with default parameters."""
        extractor = TextExtractor()
        assert extractor.preserve_formatting is True

    def test_init_with_preserve_formatting(self):
        """Test TextExtractor initialization with preserve_formatting=False."""
        extractor = TextExtractor(preserve_formatting=False)
        assert extractor.preserve_formatting is False

    def test_extract_no_chars(self):
        """Test extracting from page with no characters."""
        extractor = TextExtractor()
        page = MockPage(chars=None)

        result = extractor.extract(page)
        assert result.raw_text == ""
        assert result.elements == []

    def test_extract_with_chars(self):
        """Test extracting from page with characters."""
        extractor = TextExtractor()
        chars = [
            {"text": "Hello", "x0": 0, "top": 0, "x1": 30, "bottom": 10, "fontname": "Arial", "size": 12, "non_stroking_color": (0, 0, 0)},
            {"text": " ", "x0": 30, "top": 0, "x1": 40, "bottom": 10, "fontname": "Arial", "size": 12, "non_stroking_color": (0, 0, 0)},
            {"text": "World", "x0": 40, "top": 0, "x1": 70, "bottom": 10, "fontname": "Arial", "size": 12, "non_stroking_color": (0, 0, 0)},
        ]
        page = MockPage(chars=chars)

        result = extractor.extract(page)
        assert "Hello" in result.raw_text
        assert "World" in result.raw_text

    def test_format_color_with_tuple(self):
        """Test _format_color with color tuple."""
        result = TextExtractor._format_color((1.0, 0.5, 0.0))
        assert result == "#ff8000"

    def test_format_color_with_none(self):
        """Test _format_color with None."""
        result = TextExtractor._format_color(None)
        assert result == ""

    def test_format_color_with_short_tuple(self):
        """Test _format_color with short tuple."""
        result = TextExtractor._format_color((0.5, 0.5))
        assert result == ""

    def test_get_text_statistics_empty(self):
        """Test getting statistics for empty text."""
        extractor = TextExtractor()
        page_text = PageText(elements=[], raw_text="")
        stats = extractor.get_text_statistics(page_text)
        assert stats["character_count"] == 0
        assert stats["word_count"] == 0
        assert stats["line_count"] == 0
        assert stats["avg_font_size"] == 0.0
        assert stats["has_large_font"] is False

    def test_get_text_statistics_with_content(self):
        """Test getting statistics with content."""
        extractor = TextExtractor()
        elem = TextElement(
            text="Sample text content",
            x0=0.0,
            y0=0.0,
            x1=100.0,
            y1=50.0,
            font_size=12.0,
        )
        page_text = PageText(elements=[elem], raw_text="Sample text content")
        stats = extractor.get_text_statistics(page_text)
        assert stats["character_count"] == 20
        assert stats["word_count"] == 3
        assert stats["line_count"] == 1
        assert stats["avg_font_size"] == 12.0
        assert stats["has_large_font"] is False

    def test_get_text_statistics_large_font(self):
        """Test detecting large fonts."""
        extractor = TextExtractor()
        elem = TextElement(
            text="Heading",
            x0=0.0,
            y0=0.0,
            x1=100.0,
            y1=50.0,
            font_size=18.0,
        )
        page_text = PageText(elements=[elem], raw_text="Heading")
        stats = extractor.get_text_statistics(page_text)
        assert stats["has_large_font"] is True

    def test_can_merge_true(self):
        """Test _can_merge returns True for mergeable elements."""
        extractor = TextExtractor()
        elem1 = TextElement(
            text="Hello",
            x0=0.0,
            y0=0.0,
            x1=30.0,
            y1=10.0,
            font_name="Arial",
            font_size=12.0,
        )
        elem2 = TextElement(
            text="World",
            x0=35.0,
            y0=0.0,
            x1=65.0,
            y1=10.0,
            font_name="Arial",
            font_size=12.0,
        )
        assert extractor._can_merge(elem1, elem2)

    def test_can_merge_false_different_font(self):
        """Test _can_merge returns False for different fonts."""
        extractor = TextExtractor()
        elem1 = TextElement(
            text="Hello",
            x0=0.0,
            y0=0.0,
            x1=30.0,
            y1=10.0,
            font_name="Arial",
            font_size=12.0,
        )
        elem2 = TextElement(
            text="World",
            x0=35.0,
            y0=0.0,
            x1=65.0,
            y1=10.0,
            font_name="Times",
            font_size=12.0,
        )
        assert not extractor._can_merge(elem1, elem2)

    def test_can_merge_false_different_line(self):
        """Test _can_merge returns False for different lines."""
        extractor = TextExtractor()
        elem1 = TextElement(
            text="Line1",
            x0=0.0,
            y0=0.0,
            x1=30.0,
            y1=10.0,
            font_name="Arial",
            font_size=12.0,
        )
        elem2 = TextElement(
            text="Line2",
            x0=0.0,
            y0=20.0,
            x1=30.0,
            y1=30.0,
            font_name="Arial",
            font_size=12.0,
        )
        assert not extractor._can_merge(elem1, elem2)

    def test_can_merge_false_large_gap(self):
        """Test _can_merge returns False for large horizontal gap."""
        extractor = TextExtractor()
        elem1 = TextElement(
            text="Word1",
            x0=0.0,
            y0=0.0,
            x1=30.0,
            y1=10.0,
            font_name="Arial",
            font_size=12.0,
        )
        elem2 = TextElement(
            text="Word2",
            x0=100.0,
            y0=0.0,
            x1=130.0,
            y1=10.0,
            font_name="Arial",
            font_size=12.0,
        )
        assert not extractor._can_merge(elem1, elem2)


# Tests for ImageExtractor, TableExtractor, and LayoutAnalyzer would follow similar patterns
# They would require mock objects for image data, table structures, and layout regions
# Due to complexity and dependencies, integration tests would be more appropriate for these components