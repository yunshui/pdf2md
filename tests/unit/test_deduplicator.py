"""Unit tests for Deduplicator module."""

from dataclasses import dataclass
from typing import List, Optional
from unittest.mock import Mock

import pytest

from pdf2md.deduplicator.chapter_detector import ChapterBoundary, ChapterDetector
from pdf2md.deduplicator.header_footer import HeaderFooterContent, HeaderFooterDeduplicator
from pdf2md.deduplicator.edge_text import EdgeText, EdgeTextHandler


@dataclass
class MockTextElement:
    """Mock TextElement for testing."""
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    font_size: float = 12.0
    is_bold: bool = False

    def is_centered(self, page_width: float, tolerance: float = 0.1) -> bool:
        """Check if text is centered."""
        center_x = (self.x0 + self.x1) / 2
        page_center = page_width / 2
        return abs(center_x - page_center) < (page_width * tolerance)


@dataclass
class MockLayout:
    """Mock layout for testing."""
    width: float = 595.0
    height: float = 842.0

    def get_header_text(self) -> str:
        return ""

    def get_footer_text(self) -> str:
        return ""

    @property
    def edge_regions(self) -> list:
        return []


@dataclass
class MockPageText:
    """Mock PageText for testing."""
    elements: List[MockTextElement]

    def get_large_font_elements(self, min_font_size: float) -> List[MockTextElement]:
        return [el for el in self.elements if el.font_size >= min_font_size]


@dataclass
class MockPageData:
    """Mock PageData for testing."""
    page_number: int
    text: MockPageText
    layout: MockLayout


class TestChapterBoundary:
    """Test cases for ChapterBoundary class."""

    def test_init(self):
        """Test ChapterBoundary initialization."""
        boundary = ChapterBoundary(
            chapter_number=1,
            page_number=5,
            title="Introduction",
            heading_element=None,
            is_detected_by="pattern",
        )
        assert boundary.chapter_number == 1
        assert boundary.page_number == 5
        assert boundary.title == "Introduction"

    def test_str_with_chapter(self):
        """Test __str__ with chapter number."""
        boundary = ChapterBoundary(
            chapter_number=1,
            page_number=5,
            title="Introduction",
            heading_element=None,
            is_detected_by="pattern",
        )
        result = str(boundary)
        assert "Chapter 1" in result
        assert "Introduction" in result
        assert "page 5" in result

    def test_str_without_chapter(self):
        """Test __str__ without chapter number."""
        boundary = ChapterBoundary(
            chapter_number=0,
            page_number=5,
            title="Title",
            heading_element=None,
            is_detected_by="pattern",
        )
        result = str(boundary)
        assert "page 5" in result


class TestChapterDetector:
    """Test cases for ChapterDetector class."""

    def test_init_default(self):
        """Test ChapterDetector initialization with default parameters."""
        detector = ChapterDetector()
        assert detector.min_font_size == 14.0
        assert detector.center_tolerance == 0.1
        assert detector.use_outline is True

    def test_init_custom(self):
        """Test ChapterDetector initialization with custom parameters."""
        detector = ChapterDetector(
            min_font_size=16.0,
            center_tolerance=0.05,
            use_outline=False,
        )
        assert detector.min_font_size == 16.0
        assert detector.center_tolerance == 0.05
        assert detector.use_outline is False

    def test_is_chapter_pattern_english(self):
        """Test _is_chapter_pattern with English chapter."""
        detector = ChapterDetector()
        assert detector._is_chapter_pattern("Chapter 1")
        assert detector._is_chapter_pattern("CHAPTER 2: Introduction")

    def test_is_chapter_pattern_chinese(self):
        """Test _is_chapter_pattern with Chinese chapter."""
        detector = ChapterDetector()
        assert detector._is_chapter_pattern("第一章")
        assert detector._is_chapter_pattern("第一章")
        assert detector._is_chapter_pattern("第2章")

    def test_is_chapter_pattern_section(self):
        """Test _is_chapter_pattern with section."""
        detector = ChapterDetector()
        assert detector._is_chapter_pattern("Section 1")
        assert detector._is_chapter_pattern("§ 1")

    def test_is_chapter_pattern_part(self):
        """Test _is_chapter_pattern with part."""
        detector = ChapterDetector()
        assert detector._is_chapter_pattern("Part I")
        assert detector._is_chapter_pattern("PART II")

    def test_is_chapter_pattern_false(self):
        """Test _is_chapter_pattern returns False for non-chapter text."""
        detector = ChapterDetector()
        assert not detector._is_chapter_pattern("This is just text")
        assert not detector._is_chapter_pattern("Chapter")  # Missing number

    def test_is_likely_chapter_heading_true(self):
        """Test _is_likely_chapter_heading returns True."""
        detector = ChapterDetector()
        heading = MockTextElement(
            text="Chapter Title",
            x0=200.0,
            y0=50.0,
            x1=395.0,
            y1=100.0,
            font_size=18.0,
            is_bold=True,
        )
        # Centered on 595 page, large font, bold
        assert detector._is_likely_chapter_heading(heading, 595.0)

    def test_is_likely_chapter_heading_small_font(self):
        """Test _is_likely_chapter_heading returns False for small font."""
        detector = ChapterDetector()
        heading = MockTextElement(
            text="Text",
            x0=200.0,
            y0=50.0,
            x1=395.0,
            y1=100.0,
            font_size=12.0,
            is_bold=True,
        )
        assert not detector._is_likely_chapter_heading(heading, 595.0)

    def test_is_likely_chapter_heading_not_bold(self):
        """Test _is_likely_chapter_heading returns False for non-bold."""
        detector = ChapterDetector()
        heading = MockTextElement(
            text="Title",
            x0=200.0,
            y0=50.0,
            x1=395.0,
            y1=100.0,
            font_size=18.0,
            is_bold=False,
        )
        assert not detector._is_likely_chapter_heading(heading, 595.0)

    def test_is_likely_chapter_heading_not_centered(self):
        """Test _is_likely_chapter_heading returns False for non-centered."""
        detector = ChapterDetector()
        heading = MockTextElement(
            text="Title",
            x0=50.0,
            y0=50.0,
            x1=200.0,
            y1=100.0,
            font_size=18.0,
            is_bold=True,
        )
        assert not detector._is_likely_chapter_heading(heading, 595.0)

    def test_detect_chapters_from_outline(self):
        """Test detecting chapters from PDF outline."""
        detector = ChapterDetector()
        outline = [
            {"title": "Introduction", "page": 1},
            {"title": "Chapter 1", "page": 3},
            {"title": "Chapter 2", "page": 10},
        ]
        pages_data = [
            MockPageData(page_number=i, text=MockPageText([]), layout=MockLayout())
            for i in range(1, 15)
        ]

        boundaries = detector.detect_chapters(pages_data, pdf_outline=outline)
        assert len(boundaries) == 3
        assert boundaries[0].title == "Introduction"
        assert boundaries[1].title == "Chapter 1"
        assert boundaries[2].title == "Chapter 2"

    def test_detect_chapters_empty(self):
        """Test detecting chapters with no chapters found."""
        detector = ChapterDetector()
        pages_data = [MockPageData(page_number=1, text=MockPageText([]), layout=MockLayout())]

        boundaries = detector.detect_chapters(pages_data)
        assert len(boundaries) == 0

    def test_get_chapter_pages_no_chapters(self):
        """Test get_chapter_pages with no chapters."""
        detector = ChapterDetector()
        chapter_ranges = detector.get_chapter_pages([], total_pages=10)
        assert chapter_ranges == {1: (1, 10)}

    def test_get_chapter_pages_with_chapters(self):
        """Test get_chapter_pages with chapters."""
        detector = ChapterDetector()
        boundaries = [
            ChapterBoundary(chapter_number=1, page_number=1, title="Ch1", heading_element=None, is_detected_by="pattern"),
            ChapterBoundary(chapter_number=2, page_number=5, title="Ch2", heading_element=None, is_detected_by="pattern"),
        ]
        chapter_ranges = detector.get_chapter_pages(boundaries, total_pages=10)
        assert chapter_ranges[1] == (1, 4)
        assert chapter_ranges[2] == (5, 10)

    def test_get_page_chapter(self):
        """Test get_page_chapter."""
        detector = ChapterDetector()
        boundaries = [
            ChapterBoundary(chapter_number=1, page_number=1, title="Ch1", heading_element=None, is_detected_by="pattern"),
            ChapterBoundary(chapter_number=2, page_number=5, title="Ch2", heading_element=None, is_detected_by="pattern"),
        ]
        assert detector.get_page_chapter(3, boundaries) == 1
        assert detector.get_page_chapter(5, boundaries) == 2
        assert detector.get_page_chapter(10, boundaries) == 2
        assert detector.get_page_chapter(1, boundaries) == 1

    def test_has_chapters_true(self):
        """Test has_chapters returns True."""
        detector = ChapterDetector()
        heading = MockTextElement(
            text="Chapter 1",
            x0=0.0,
            y0=0.0,
            x1=100.0,
            y1=50.0,
            font_size=16.0,
        )
        pages_data = [
            MockPageData(
                page_number=1,
                text=MockPageText([heading]),
                layout=MockLayout(),
            )
        ]
        assert detector.has_chapters(pages_data)

    def test_has_chapters_false(self):
        """Test has_chapters returns False."""
        detector = ChapterDetector()
        pages_data = [MockPageData(page_number=1, text=MockPageText([]), layout=MockLayout())]
        assert not detector.has_chapters(pages_data)


class TestHeaderFooterContent:
    """Test cases for HeaderFooterContent class."""

    def test_init(self):
        """Test HeaderFooterContent initialization."""
        content = HeaderFooterContent(
            content="Page 1",
            page_numbers=[1, 2, 3],
            frequency=3,
            is_header=True,
        )
        assert content.content == "Page 1"
        assert content.frequency == 3
        assert content.is_header is True

    def test_is_candidate_for_deduplication_true(self):
        """Test is_candidate_for_deduplication returns True."""
        content = HeaderFooterContent(
            content="Header",
            page_numbers=[1, 2, 3],
            frequency=3,
            is_header=True,
        )
        assert content.is_candidate_for_deduplication(min_frequency=2)

    def test_is_candidate_for_deduplication_false(self):
        """Test is_candidate_for_deduplication returns False."""
        content = HeaderFooterContent(
            content="Header",
            page_numbers=[1],
            frequency=1,
            is_header=True,
        )
        assert not content.is_candidate_for_deduplication(min_frequency=2)

    def test_str_header(self):
        """Test __str__ for header."""
        content = HeaderFooterContent(
            content="Header text",
            page_numbers=[1, 2],
            frequency=2,
            is_header=True,
        )
        result = str(content)
        assert "Header" in result
        assert "Header text" in result
        assert "2 pages" in result

    def test_str_footer(self):
        """Test __str__ for footer."""
        content = HeaderFooterContent(
            content="Footer text",
            page_numbers=[1, 2],
            frequency=2,
            is_header=False,
        )
        result = str(content)
        assert "Footer" in result


class TestHeaderFooterDeduplicator:
    """Test cases for HeaderFooterDeduplicator class."""

    def test_init_default(self):
        """Test HeaderFooterDeduplicator initialization with default parameters."""
        dedup = HeaderFooterDeduplicator()
        assert dedup.min_frequency == 2
        assert dedup.similarity_threshold == 0.9
        assert dedup.ignore_page_numbers is True

    def test_init_custom(self):
        """Test HeaderFooterDeduplicator initialization with custom parameters."""
        dedup = HeaderFooterDeduplicator(
            min_frequency=3,
            similarity_threshold=0.8,
            ignore_page_numbers=False,
        )
        assert dedup.min_frequency == 3
        assert dedup.similarity_threshold == 0.8
        assert dedup.ignore_page_numbers is False

    def test_deduplicate_empty(self):
        """Test deduplication with empty pages."""
        dedup = HeaderFooterDeduplicator()
        result = dedup.deduplicate([])
        assert result == {}

    def test_normalize_content(self):
        """Test content normalization."""
        dedup = HeaderFooterDeduplicator()
        normalized = dedup._normalize_content("  Multiple   spaces  ")
        assert normalized == "Multiple spaces"

    def test_remove_page_numbers(self):
        """Test removing page numbers."""
        dedup = HeaderFooterDeduplicator()
        result = dedup._remove_page_numbers("Page 123 footer")
        assert "123" not in result

    def test_is_similar_exact(self):
        """Test _is_similar with exact match."""
        dedup = HeaderFooterDeduplicator()
        assert dedup._is_similar("Same text", "Same text")

    def test_is_similar_different(self):
        """Test _is_similar with different text."""
        dedup = HeaderFooterDeduplicator()
        assert not dedup._is_similar("Text one", "Text two")

    def test_is_similar_threshold(self):
        """Test _is_similar with threshold."""
        dedup = HeaderFooterDeduplicator(similarity_threshold=0.5)
        # Similar but not exact
        assert dedup._is_similar("Text one two", "Text one three")


class TestEdgeText:
    """Test cases for EdgeText class."""

    def test_init(self):
        """Test EdgeText initialization."""
        edge_text = EdgeText(
            text="Note",
            page_number=1,
            position="left",
            x0=10.0,
            y0=50.0,
            x1=50.0,
            y1=100.0,
        )
        assert edge_text.text == "Note"
        assert edge_text.page_number == 1
        assert edge_text.position == "left"

    def test_str(self):
        """Test __str__ method."""
        edge_text = EdgeText(
            text="Note",
            page_number=1,
            position="left",
            x0=10.0,
            y0=50.0,
            x1=50.0,
            y1=100.0,
        )
        result = str(edge_text)
        assert "[left" in result
        assert "page 1]" in result
        assert "Note" in result


class TestEdgeTextHandler:
    """Test cases for EdgeTextHandler class."""

    def test_init_default(self):
        """Test EdgeTextHandler initialization with default parameters."""
        handler = EdgeTextHandler()
        assert handler.edge_margin == 30.0
        assert handler.deduplicate_across_pages is True

    def test_init_custom(self):
        """Test EdgeTextHandler initialization with custom parameters."""
        handler = EdgeTextHandler(edge_margin=50.0, deduplicate_across_pages=False)
        assert handler.edge_margin == 50.0
        assert handler.deduplicate_across_pages is False

    def test_determine_position_left(self):
        """Test determining left position."""
        handler = EdgeTextHandler()
        mock_region = Mock()
        mock_region.x0 = 10.0
        mock_region.x1 = 50.0
        mock_region.y0 = 100.0
        mock_region.y1 = 150.0

        position = handler._determine_position(mock_region, 595.0, 842.0)
        assert position == "left"

    def test_determine_position_right(self):
        """Test determining right position."""
        handler = EdgeTextHandler()
        mock_region = Mock()
        mock_region.x0 = 550.0
        mock_region.x1 = 590.0
        mock_region.y0 = 100.0
        mock_region.y1 = 150.0

        position = handler._determine_position(mock_region, 595.0, 842.0)
        assert position == "right"

    def test_determine_position_top(self):
        """Test determining top position."""
        handler = EdgeTextHandler()
        mock_region = Mock()
        mock_region.x0 = 200.0
        mock_region.x1 = 400.0
        mock_region.y0 = 10.0
        mock_region.y1 = 50.0

        position = handler._determine_position(mock_region, 595.0, 842.0)
        assert position == "top"

    def test_determine_position_bottom(self):
        """Test determining bottom position."""
        handler = EdgeTextHandler()
        mock_region = Mock()
        mock_region.x0 = 200.0
        mock_region.x1 = 400.0
        mock_region.y0 = 800.0
        mock_region.y1 = 840.0

        position = handler._determine_position(mock_region, 595.0, 842.0)
        assert position == "bottom"

    def test_normalize_text(self):
        """Test text normalization."""
        handler = EdgeTextHandler()
        normalized = handler._normalize_text("  Test  TEXT  ")
        assert normalized == "test text"

    def test_get_edge_text_by_position(self):
        """Test filtering edge text by position."""
        handler = EdgeTextHandler()
        edge_texts = [
            EdgeText("Left note", 1, "left", 10, 10, 50, 50),
            EdgeText("Right note", 1, "right", 550, 10, 590, 50),
        ]

        filtered = handler.get_edge_text_by_position(edge_texts, "left")
        assert len(filtered) == 1
        assert filtered[0].text == "Left note"

    def test_get_edge_text_by_page(self):
        """Test filtering edge text by page."""
        handler = EdgeTextHandler()
        edge_texts = [
            EdgeText("Note 1", 1, "left", 10, 10, 50, 50),
            EdgeText("Note 2", 2, "left", 10, 10, 50, 50),
        ]

        filtered = handler.get_edge_text_by_page(edge_texts, 1)
        assert len(filtered) == 1
        assert filtered[0].text == "Note 1"

    def test_format_edge_text_markdown(self):
        """Test formatting edge text as markdown."""
        handler = EdgeTextHandler()
        edge_texts = [
            EdgeText("Note 1", 1, "left", 10, 10, 50, 50),
            EdgeText("Note 2", 2, "left", 10, 10, 50, 50),
        ]

        formatted = handler.format_edge_text(edge_texts, format="markdown")
        assert "## Edge Text" in formatted
        assert "### Left" in formatted
        assert "Note 1" in formatted
        assert "Note 2" in formatted

    def test_format_edge_text_plain(self):
        """Test formatting edge text as plain text."""
        handler = EdgeTextHandler()
        edge_texts = [EdgeText("Note", 1, "left", 10, 10, 50, 50)]

        formatted = handler.format_edge_text(edge_texts, format="plain")
        assert "[left]" in formatted
        assert "Page 1" in formatted
        assert "Note" in formatted

    def test_format_edge_text_list(self):
        """Test formatting edge text as list."""
        handler = EdgeTextHandler()
        edge_texts = [EdgeText("Note 1", 1, "left", 10, 10, 50, 50)]

        formatted = handler.format_edge_text(edge_texts, format="list")
        assert formatted == "Note 1"

    def test_get_edge_text_summary(self):
        """Test getting edge text summary."""
        handler = EdgeTextHandler()
        edge_texts = [
            EdgeText("Note 1", 1, "left", 10, 10, 50, 50),
            EdgeText("Note 2", 2, "left", 10, 10, 50, 50),
            EdgeText("Note 3", 1, "right", 10, 10, 50, 50),
        ]

        summary = handler.get_edge_text_summary(edge_texts)
        assert summary["total"] == 3
        assert summary["by_position"]["left"] == 2
        assert summary["by_position"]["right"] == 1
        assert summary["by_page"][1] == 2
        assert summary["by_page"][2] == 1

    def test_get_edge_text_summary_empty(self):
        """Test getting summary for empty edge texts."""
        handler = EdgeTextHandler()
        summary = handler.get_edge_text_summary([])
        assert summary["total"] == 0
        assert summary["by_position"] == {}
        assert summary["by_page"] == {}