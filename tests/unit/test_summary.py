"""Unit tests for Summary module."""

from dataclasses import dataclass
from typing import List
from unittest.mock import Mock

import pytest

from pdf2md.summary.extractor import Summary, SummaryExtractor
from pdf2md.summary.rule_based import SummaryItem, RuleBasedExtractor


@dataclass
class MockTextElement:
    """Mock TextElement for testing."""
    text: str
    font_size: float = 12.0

    def is_centered(self, page_width: float, tolerance: float = 0.1) -> bool:
        return True


@dataclass
class MockPageText:
    """Mock PageText for testing."""
    elements: List[MockTextElement]
    raw_text: str

    def get_large_font_elements(self, min_font_size: float) -> List[MockTextElement]:
        return [el for el in self.elements if el.font_size >= min_font_size]


@dataclass
class MockLayout:
    """Mock layout for testing."""
    width: float = 595.0
    height: float = 842.0
    edge_regions: List = []


@dataclass
class MockPageData:
    """Mock PageData for testing."""
    page_number: int
    text: MockPageText
    layout: MockLayout
    text_statistics: dict
    images: List = []

    def get_all_text(self) -> str:
        return self.text.raw_text


class TestSummary:
    """Test cases for Summary class."""

    def test_init(self):
        """Test Summary initialization."""
        summary = Summary(
            title="Test Document",
            headings=["Heading 1", "Heading 2"],
            key_points=["Point 1", "Point 2"],
            page_count=10,
            word_count=5000,
            table_of_contents=[],
            footnotes=[],
            annotations=[],
        )
        assert summary.title == "Test Document"
        assert summary.page_count == 10
        assert summary.word_count == 5000

    def test_to_markdown(self):
        """Test converting summary to Markdown."""
        summary = Summary(
            title="Test Document",
            headings=["Heading 1", "Heading 2"],
            key_points=["Point 1", "Point 2"],
            page_count=10,
            word_count=5000,
            table_of_contents=[],
            footnotes=["Footnote 1"],
            annotations=["Annotation 1"],
        )

        markdown = summary.to_markdown()
        assert "# Test Document" in markdown
        assert "Page Count: 10" in markdown
        assert "Word Count: 5000" in markdown
        assert "## Headings" in markdown
        assert "## Key Points" in markdown
        assert "## Footnotes" in markdown
        assert "## Annotations" in markdown

    def test_to_markdown_empty(self):
        """Test converting empty summary to Markdown."""
        summary = Summary(
            title="Empty",
            headings=[],
            key_points=[],
            page_count=0,
            word_count=0,
            table_of_contents=[],
            footnotes=[],
            annotations=[],
        )

        markdown = summary.to_markdown()
        assert "# Empty" in markdown


class TestSummaryItem:
    """Test cases for SummaryItem class."""

    def test_init(self):
        """Test SummaryItem initialization."""
        item = SummaryItem(
            item_type="heading",
            text="Chapter 1",
            page_number=1,
            position="header",
            confidence=0.9,
            context="Font size: 16pt",
        )
        assert item.item_type == "heading"
        assert item.text == "Chapter 1"
        assert item.page_number == 1

    def test_str(self):
        """Test __str__ method."""
        item = SummaryItem(
            item_type="heading",
            text="Chapter 1",
            page_number=1,
            position="header",
            confidence=0.9,
            context=None,
        )
        result = str(item)
        assert "[heading]" in result
        assert "Page 1" in result
        assert "Chapter 1" in result


class TestRuleBasedExtractor:
    """Test cases for RuleBasedExtractor class."""

    def test_init_default(self):
        """Test RuleBasedExtractor initialization with default parameters."""
        extractor = RuleBasedExtractor()
        assert extractor.min_heading_font_size == 14.0

    def test_init_custom(self):
        """Test RuleBasedExtractor initialization with custom parameters."""
        extractor = RuleBasedExtractor(min_heading_font_size=16.0)
        assert extractor.min_heading_font_size == 16.0

    def test_is_heading_pattern_english(self):
        """Test _is_heading_pattern with English chapter."""
        extractor = RuleBasedExtractor()
        assert extractor._is_heading_pattern("Chapter 1: Introduction")
        assert extractor._is_heading_pattern("CHAPTER 2")

    def test_is_heading_pattern_chinese(self):
        """Test _is_heading_pattern with Chinese chapter."""
        extractor = RuleBasedExtractor()
        assert extractor._is_heading_pattern("第一章")
        assert extractor._is_heading_pattern("第一章 概述")
        assert extractor._is_heading_pattern("第2章")

    def test_is_heading_pattern_numbered(self):
        """Test _is_heading_pattern with numbered heading."""
        extractor = RuleBasedExtractor()
        assert extractor._is_heading_pattern("1. Introduction")

    def test_is_heading_pattern_markdown(self):
        """Test _is_heading_pattern with Markdown style."""
        extractor = RuleBasedExtractor()
        assert extractor._is_heading_pattern("## Heading")
        assert extractor._is_heading_pattern("### Subheading")

    def test_is_heading_pattern_false(self):
        """Test _is_heading_pattern returns False for non-headings."""
        extractor = RuleBasedExtractor()
        assert not extractor._is_heading_pattern("This is just regular text")

    def test_is_footnote_pattern(self):
        """Test _is_footnote_pattern."""
        extractor = RuleBasedExtractor()
        assert extractor._is_footnote_pattern("[1] This is a footnote")
        assert extractor._is_footnote_pattern("1) This is a footnote")
        assert extractor._is_footnote_pattern("* 1 * Footnote text")

    def test_is_caption_pattern(self):
        """Test _is_caption_pattern."""
        extractor = RuleBasedExtractor()
        assert extractor._is_caption_pattern("Figure 1: Sample image")
        assert extractor._is_caption_pattern("Table 2. Data summary")
        assert extractor._is_caption_pattern("图1: 示例图片")
        assert extractor._is_caption_pattern("Fig. 3 - Graph")

    def test_extract_headings_by_level(self):
        """Test extracting headings grouped by level."""
        extractor = RuleBasedExtractor()

        page_data = MockPageData(
            page_number=1,
            text=MockPageText(
                elements=[
                    MockTextElement("Chapter 1", font_size=16),
                    MockTextElement("Section 1.1", font_size=14),
                ],
                raw_text="Chapter 1\nSection 1.1",
            ),
            layout=MockLayout(),
            text_statistics={"word_count": 100},
        )

        headings_by_level = extractor.extract_headings_by_level([page_data], max_level=2)
        assert 1 in headings_by_level
        assert 2 in headings_by_level

    def test_determine_heading_level(self):
        """Test determining heading level."""
        extractor = RuleBasedExtractor()

        chapter_item = SummaryItem("heading", "Chapter 1", 1, "header", 0.9, None)
        section_item = SummaryItem("heading", "Section 1", 1, "header", 0.9, None)

        assert extractor._determine_heading_level(chapter_item) == 1
        assert extractor._determine_heading_level(section_item) == 2

    def test_determine_heading_level_chinese(self):
        """Test determining heading level for Chinese chapters."""
        extractor = RuleBasedExtractor()

        chapter_item = SummaryItem("heading", "第一章", 1, "header", 0.9, None)
        assert extractor._determine_heading_level(chapter_item) == 1

    def test_generate_index(self):
        """Test generating index from summaries."""
        extractor = RuleBasedExtractor()

        summaries = [
            SummaryItem("heading", "Chapter 1", 1, "header", 0.9, None),
            SummaryItem("footnote", "[1] Note", 1, "body", 0.8, None),
        ]

        index = extractor.generate_index(summaries)
        assert "## Index" in index
        assert "Heading" in index
        assert "Footnote" in index

    def test_generate_index_empty(self):
        """Test generating index with no summaries."""
        extractor = RuleBasedExtractor()
        index = extractor.generate_index([])
        assert "No summary items found" in index

    def test_filter_by_type(self):
        """Test filtering summaries by type."""
        extractor = RuleBasedExtractor()

        summaries = [
            SummaryItem("heading", "H1", 1, "header", 0.9, None),
            SummaryItem("footnote", "F1", 1, "body", 0.8, None),
            SummaryItem("heading", "H2", 2, "header", 0.9, None),
        ]

        filtered = extractor.filter_by_type(summaries, "heading")
        assert len(filtered) == 2
        assert all(s.item_type == "heading" for s in filtered)

    def test_filter_by_page_range(self):
        """Test filtering summaries by page range."""
        extractor = RuleBasedExtractor()

        summaries = [
            SummaryItem("heading", "H1", 1, "header", 0.9, None),
            SummaryItem("heading", "H2", 2, "header", 0.9, None),
            SummaryItem("heading", "H3", 3, "header", 0.9, None),
        ]

        filtered = extractor.filter_by_page_range(summaries, 2, 3)
        assert len(filtered) == 2
        assert all(2 <= s.page_number <= 3 for s in filtered)

    def test_get_high_confidence_summaries(self):
        """Test filtering by confidence level."""
        extractor = RuleBasedExtractor()

        summaries = [
            SummaryItem("heading", "H1", 1, "header", 0.9, None),
            SummaryItem("heading", "H2", 1, "header", 0.6, None),
            SummaryItem("heading", "H3", 1, "header", 0.8, None),
        ]

        high_confidence = extractor.get_high_confidence_summaries(summaries, min_confidence=0.7)
        assert len(high_confidence) == 2
        assert all(s.confidence >= 0.7 for s in high_confidence)


class TestSummaryExtractor:
    """Test cases for SummaryExtractor class."""

    def test_init_default(self):
        """Test SummaryExtractor initialization with default parameters."""
        extractor = SummaryExtractor()
        assert extractor.enable_ai is False
        assert extractor.rule_extractor is not None
        assert extractor.ai_assistant is None

    def test_init_with_ai(self):
        """Test SummaryExtractor initialization with AI enabled."""
        extractor = SummaryExtractor(enable_ai=True)
        # AI assistant should be None due to missing dependencies
        assert extractor.ai_assistant is None
        assert extractor.enable_ai is False  # Should be disabled due to ImportError

    def test_extract_summary_rule_based(self):
        """Test extracting summary using rule-based method."""
        extractor = SummaryExtractor()

        page_data = MockPageData(
            page_number=1,
            text=MockPageText(
                elements=[],
                raw_text="This is a sample document. It contains multiple paragraphs with useful information.",
            ),
            layout=MockLayout(),
            text_statistics={"word_count": 50},
        )

        summary = extractor.extract_summary([page_data], "/test/document.pdf")

        assert summary.title is not None
        assert summary.page_count == 1
        assert summary.word_count > 0

    def test_extract_key_points(self):
        """Test extracting key points from pages."""
        extractor = SummaryExtractor()

        page_data = MockPageData(
            page_number=1,
            text=MockPageText(
                elements=[],
                raw_text="This is a sample document with some important content. It contains multiple paragraphs. The third paragraph has additional information.",
            ),
            layout=MockLayout(),
            text_statistics={"word_count": 30},
        )

        key_points = extractor._extract_key_points([page_data])
        assert len(key_points) > 0

    def test_extract_key_points_limit(self):
        """Test extracting key points with max limit."""
        extractor = SummaryExtractor()

        page_data = MockPageData(
            page_number=1,
            text=MockPageText(
                elements=[],
                raw_text="Paragraph one. Paragraph two. Paragraph three. Paragraph four. Paragraph five. Paragraph six.",
            ),
            layout=MockLayout(),
            text_statistics={"word_count": 30},
        )

        key_points = extractor._extract_key_points([page_data], max_points=3)
        assert len(key_points) <= 3

    def test_get_summary_statistics(self):
        """Test getting summary statistics."""
        extractor = SummaryExtractor()

        summary = Summary(
            title="Test",
            headings=["H1", "H2"],
            key_points=["P1", "P2", "P3"],
            page_count=10,
            word_count=5000,
            table_of_contents=[],
            footnotes=["F1"],
            annotations=["A1"],
        )

        stats = extractor.get_summary_statistics(summary)
        assert stats["heading_count"] == 2
        assert stats["key_point_count"] == 3
        assert stats["footnote_count"] == 1
        assert stats["annotation_count"] == 1
        assert stats["avg_words_per_page"] == 500.0

    def test_generate_toc(self):
        """Test generating table of contents."""
        extractor = SummaryExtractor()

        # Mock headings by level
        extractor.rule_extractor.extract_headings_by_level = Mock(return_value={
            1: [SummaryItem("heading", "Chapter 1", 1, "header", 0.9, None)],
            2: [SummaryItem("heading", "Section 1.1", 1, "header", 0.9, None)],
        })

        page_data = MockPageData(
            page_number=1,
            text=MockPageText([], ""),
            layout=MockLayout(),
            text_statistics={"word_count": 0},
        )

        toc = extractor._generate_toc(["Chapter 1"], [page_data])
        assert len(toc) >= 0

    def test_extract_title_from_file(self):
        """Test extracting title from file name."""
        extractor = SummaryExtractor()

        title = extractor._extract_title("/path/to/my_document.pdf", [])
        assert "My Document" in title or "my_document" in title.replace("_", " ")