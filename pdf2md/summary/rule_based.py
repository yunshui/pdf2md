"""Rule-based summary extraction from PDF content."""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from pdf2md.core.page_processor import PageData
from pdf2md.extractor import TextElement
from pdf2md.utils.logger import get_logger

logger = get_logger()


@dataclass
class SummaryItem:
    """Represents a single summary item."""

    item_type: str  # "heading", "annotation", "footnote", "caption"
    text: str
    page_number: int
    position: str  # "header", "footer", "body", "edge"
    confidence: float  # 0.0 to 1.0
    context: Optional[str]  # Additional context

    def __str__(self) -> str:
        """Get string representation."""
        return f"[{self.item_type}] Page {self.page_number}: {self.text}"


class RuleBasedExtractor:
    """Extracts summary information using rule-based patterns."""

    # Common heading patterns
    HEADING_PATTERNS = [
        r"^(Chapter|CHAPTER)\s+\d+[:\s].*",  # Chapter 1: Introduction
        r"^(第[一二三四五六七八九十百千万]+章)\s*",  # 第一章 概述
        r"^\d+\.\s+[A-Z][^.]+$",  # 1. Introduction
        r"^#{1,3}\s+.+",  # Markdown style headings
        r"^Part\s+[IVXLCDM]+\s*",  # Part I
        r"^Section\s+\d+[:\s].*",  # Section 1: Overview
    ]

    # Footnote patterns
    FOOTNOTE_PATTERNS = [
        r"^\[\d+\]\s+",  # [1] This is a footnote
        r"^\d+\)\s+",  # 1) This is a footnote
        r"^\*\s+\d+\s+\*.*$",  # * 1 * Footnote text
    ]

    # Caption patterns
    CAPTION_PATTERNS = [
        r"^(Figure|Table|Diagram|Chart)\s+\d+[:\.-].*",
        r"^(图|表)\s+\d+[:\.-].*",  # 图1、表2
        r"^(Fig|Tab|Ex)\.?\s+\d+[:\.-].*",
    ]

    # Annotation markers
    ANNOTATION_MARKERS = [
        "†", "‡", "‡‡",
        "*",
        "Note:",
        "注:",
        "Remark:",
    ]

    def __init__(self, min_heading_font_size: float = 14.0) -> None:
        """Initialize the rule-based extractor.

        Args:
            min_heading_font_size: Minimum font size for headings.
        """
        self.min_heading_font_size = min_heading_font_size

        # Compile regex patterns
        self._heading_patterns = [re.compile(p, re.IGNORECASE) for p in self.HEADING_PATTERNS]
        self._footnote_patterns = [re.compile(p) for p in self.FOOTNOTE_PATTERNS]
        self._caption_patterns = [re.compile(p, re.IGNORECASE) for p in self.CAPTION_PATTERNS]

    def extract_summaries(self, pages_data: List[PageData]) -> List[SummaryItem]:
        """Extract summary items from all pages.

        Args:
            pages_data: List of processed page data.

        Returns:
            List of SummaryItem objects.
        """
        logger.info("Extracting rule-based summaries...")

        summaries = []

        for page_data in pages_data:
            page_summaries = self._extract_from_page(page_data)
            summaries.extend(page_summaries)

        logger.info(f"Extracted {len(summaries)} summary items")

        return summaries

    def _extract_from_page(self, page_data: PageData) -> List[SummaryItem]:
        """Extract summary items from a single page.

        Args:
            page_data: Processed page data.

        Returns:
            List of SummaryItem objects.
        """
        summaries = []

        # Extract headings
        headings = self._extract_headings(page_data)
        summaries.extend(headings)

        # Extract footnotes and annotations
        footnotes = self._extract_footnotes(page_data)
        summaries.extend(footnotes)

        # Extract captions
        captions = self._extract_captions(page_data)
        summaries.extend(captions)

        # Extract annotations from edge text
        edge_annotations = self._extract_edge_annotations(page_data)
        summaries.extend(edge_annotations)

        return summaries

    def _extract_headings(self, page_data: PageData) -> List[SummaryItem]:
        """Extract headings from page.

        Args:
            page_data: Processed page data.

        Returns:
            List of SummaryItem objects.
        """
        summaries = []

        # Get large font elements (potential headings)
        large_elements = page_data.text.get_large_font_elements(self.min_heading_font_size)

        for element in large_elements:
            text = element.text.strip()

            # Check if text matches heading pattern
            if self._is_heading_pattern(text):
                summaries.append(
                    SummaryItem(
                        item_type="heading",
                        text=text,
                        page_number=page_data.page_number,
                        position=self._determine_position(element, page_data.layout.width),
                        confidence=0.9,
                        context=f"Font size: {element.font_size}pt",
                    )
                )

        return summaries

    def _extract_footnotes(self, page_data: PageData) -> List[SummaryItem]:
        """Extract footnotes from page.

        Args:
            page_data: Processed page data.

        Returns:
            List of SummaryItem objects.
        """
        summaries = []

        # Check text for footnote patterns
        lines = page_data.body_text.split("\n")

        for line_idx, line in enumerate(lines):
            line = line.strip()

            # Check if line matches footnote pattern
            if self._is_footnote_pattern(line):
                summaries.append(
                    SummaryItem(
                        item_type="footnote",
                        text=line,
                        page_number=page_data.page_number,
                        position="body",
                        confidence=0.8,
                        context=None,
                    )
                )

        return summaries

    def _extract_captions(self, page_data: PageData) -> List[SummaryItem]:
        """Extract figure/table captions from page.

        Args:
            page_data: Processed page data.

        Returns:
            List of SummaryItem objects.
        """
        summaries = []

        # Check text for caption patterns
        lines = page_data.body_text.split("\n")

        for line in lines:
            line = line.strip()

            # Check if line matches caption pattern
            if self._is_caption_pattern(line):
                # Check if this is near an image or table
                position = self._determine_caption_position(line, page_data)

                summaries.append(
                    SummaryItem(
                        item_type="caption",
                        text=line,
                        page_number=page_data.page_number,
                        position=position,
                        confidence=0.85,
                        context=None,
                    )
                )

        return summaries

    def _extract_edge_annotations(self, page_data: PageData) -> List[SummaryItem]:
        """Extract annotations from edge text.

        Args:
            page_data: Processed page data.

        Returns:
            List of SummaryItem objects.
        """
        summaries = []

        for edge_region in page_data.layout.edge_regions:
            text = edge_region.text.strip()

            # Check if edge text contains annotation markers
            if any(marker in text for marker in self.ANNOTATION_MARKERS):
                summaries.append(
                    SummaryItem(
                        item_type="annotation",
                        text=text,
                        page_number=page_data.page_number,
                        position="edge",
                        confidence=0.7,
                        context="Edge text",
                    )
                )

        return summaries

    def _is_heading_pattern(self, text: str) -> bool:
        """Check if text matches a heading pattern.

        Args:
            text: Text to check.

        Returns:
            True if text is a heading.
        """
        for pattern in self._heading_patterns:
            if pattern.match(text.strip()):
                return True
        return False

    def _is_footnote_pattern(self, text: str) -> bool:
        """Check if text matches a footnote pattern.

        Args:
            text: Text to check.

        Returns:
            True if text is a footnote.
        """
        for pattern in self._footnote_patterns:
            if pattern.match(text.strip()):
                return True
        return False

    def _is_caption_pattern(self, text: str) -> bool:
        """Check if text matches a caption pattern.

        Args:
            text: Text to check.

        Returns:
            True if text is a caption.
        """
        for pattern in self._caption_patterns:
            if pattern.match(text.strip()):
                return True
        return False

    def _determine_position(
        self, element: TextElement, page_width: float
    ) -> str:
        """Determine the position of a text element.

        Args:
            element: Text element.
            page_width: Page width.

        Returns:
            Position string.
        """
        # Check if centered (likely heading)
        if element.is_centered(page_width, tolerance=0.1):
            return "header"

        # Check if near top (likely header)
        if element.y0 < 50:
            return "header"

        # Check if near bottom (likely footer)
        if element.y1 > page_width - 50:
            return "footer"

        return "body"

    def _determine_caption_position(
        self, text: str, page_data: PageData
    ) -> str:
        """Determine position of a caption.

        Args:
            text: Caption text.
            page_data: Page data.

        Returns:
            Position string.
        """
        # Check if caption is near an image
        for image_info in page_data.images:
            # Check if caption text is close to image position
            # This is a simplified check
            if abs(image_info.y0 - page_data.layout.height / 2) < 100:
                return "body"

        return "body"

    def extract_headings_by_level(
        self, pages_data: List[PageData], max_level: int = 3
    ) -> Dict[int, List[SummaryItem]]:
        """Extract headings grouped by level.

        Args:
            pages_data: List of processed page data.
            max_level: Maximum heading level to extract.

        Returns:
            Dictionary mapping level numbers to heading lists.
        """
        headings_by_level = {level: [] for level in range(1, max_level + 1)}

        for page_data in pages_data:
            headings = self._extract_headings(page_data)

            for heading in headings:
                # Determine heading level based on font size or pattern
                level = self._determine_heading_level(heading)

                if level <= max_level:
                    headings_by_level[level].append(heading)

        return headings_by_level

    def _determine_heading_level(self, heading: SummaryItem) -> int:
        """Determine the hierarchical level of a heading.

        Args:
            heading: SummaryItem.

        Returns:
            Heading level (1 = highest).
        """
        text = heading.text.strip()

        # Check for chapter-level headings
        if re.match(r"^(Chapter|CHAPTER)\s+\d+", text, re.IGNORECASE):
            return 1

        if re.match(r"^第[一二三四五六七八九十百千万]+章", text):
            return 1

        # Check for section-level headings
        if re.match(r"^Section\s+\d+", text, re.IGNORECASE):
            return 2

        if re.match(r"^\d+\.\s+", text):
            return 2

        # Default to level 3
        return 3

    def generate_index(self, summaries: List[SummaryItem]) -> str:
        """Generate an index from summary items.

        Args:
            summaries: List of summary items.

        Returns:
            Formatted index string.
        """
        if not summaries:
            return "*No summary items found.*"

        lines = ["## Index\n"]

        # Group by type
        by_type = {}
        for item in summaries:
            if item.item_type not in by_type:
                by_type[item.item_type] = []
            by_type[item.item_type].append(item)

        # Output by type
        for item_type in ["heading", "annotation", "footnote", "caption"]:
            if item_type in by_type and by_type[item_type]:
                lines.append(f"### {item_type.title()}\n")

                for item in by_type[item_type]:
                    lines.append(f"- {item.text} (page {item.page_number})")

                lines.append("")

        return "\n".join(lines)

    def filter_by_type(
        self, summaries: List[SummaryItem], item_type: str
    ) -> List[SummaryItem]:
        """Filter summaries by item type.

        Args:
            summaries: List of summary items.
            item_type: Item type to filter by.

        Returns:
            Filtered list of summaries.
        """
        return [s for s in summaries if s.item_type == item_type]

    def filter_by_page_range(
        self, summaries: List[SummaryItem], start_page: int, end_page: int
    ) -> List[SummaryItem]:
        """Filter summaries by page range.

        Args:
            summaries: List of summary items.
            start_page: Start page number.
            end_page: End page number.

        Returns:
            Filtered list of summaries.
        """
        return [
            s
            for s in summaries
            if start_page <= s.page_number <= end_page
        ]

    def get_high_confidence_summaries(
        self, summaries: List[SummaryItem], min_confidence: float = 0.7
    ) -> List[SummaryItem]:
        """Get high-confidence summary items.

        Args:
            summaries: List of summary items.
            min_confidence: Minimum confidence threshold.

        Returns:
            Filtered list of summaries.
        """
        return [s for s in summaries if s.confidence >= min_confidence]