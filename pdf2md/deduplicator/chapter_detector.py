"""Chapter boundary detection for PDF pages."""

import re
from dataclasses import dataclass
from typing import List, Optional

from pdf2md.core.page_processor import PageData
from pdf2md.extractor import TextElement, TextRegionType
from pdf2md.utils.logger import get_logger

logger = get_logger()


@dataclass
class ChapterBoundary:
    """Represents a chapter boundary in the document."""

    chapter_number: int
    page_number: int
    title: str
    heading_element: Optional[TextElement]
    is_detected_by: str  # How it was detected (font, pattern, outline, etc.)

    def __str__(self) -> str:
        """Get string representation."""
        prefix = f"Chapter {self.chapter_number}" if self.chapter_number > 0 else ""
        title = f": {self.title}" if self.title else ""
        return f"{prefix}{title} (page {self.page_number})"


class ChapterDetector:
    """Detects chapter boundaries in PDF documents."""

    # Common chapter patterns
    CHAPTER_PATTERNS = [
        r"^Chapter\s+\d+",  # Chapter 1
        r"^第[一二三四五六七八九十百千万]+章",  # 第一章
        r"^第\d+章",  # 第1章
        r"^Section\s+\d+",  # Section 1
        r"^§\s*\d+",  # § 1
        r"^Part\s+[IVXLCDM]+",  # Part I
        r"^PART\s+[IVXLCDM]+",  # PART I
    ]

    # Heading font size threshold (points)
    MIN_HEADING_FONT_SIZE = 14.0
    MIN_LARGE_HEADING_FONT_SIZE = 16.0

    def __init__(
        self,
        min_font_size: float = 14.0,
        center_tolerance: float = 0.1,
        use_outline: bool = True,
    ) -> None:
        """Initialize the chapter detector.

        Args:
            min_font_size: Minimum font size for headings.
            center_tolerance: Tolerance for centering detection (0.0 to 1.0).
            use_outline: Whether to use PDF outline if available.
        """
        self.min_font_size = min_font_size
        self.center_tolerance = center_tolerance
        self.use_outline = use_outline

        # Compile regex patterns
        self._compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.CHAPTER_PATTERNS
        ]

    def detect_chapters(
        self,
        pages_data: List[PageData],
        pdf_outline: Optional[List] = None,
    ) -> List[ChapterBoundary]:
        """Detect chapter boundaries from processed pages.

        Args:
            pages_data: List of processed page data.
            pdf_outline: Optional PDF outline/bookmarks.

        Returns:
            List of ChapterBoundary objects.
        """
        logger.info("Detecting chapter boundaries...")

        boundaries = []

        # Try PDF outline first
        if self.use_outline and pdf_outline:
            outline_boundaries = self._detect_from_outline(pdf_outline, pages_data)
            if outline_boundaries:
                logger.info(f"Found {len(outline_boundaries)} chapters from PDF outline")
                boundaries.extend(outline_boundaries)
                return boundaries

        # Detect from page content
        for page_data in pages_data:
            page_boundaries = self._detect_from_page(page_data)
            boundaries.extend(page_boundaries)

        # Sort by page number and deduplicate nearby detections
        boundaries = self._sort_and_deduplicate(boundaries)

        # Assign chapter numbers
        for idx, boundary in enumerate(boundaries, start=1):
            boundary.chapter_number = idx

        logger.info(f"Detected {len(boundaries)} chapter boundaries")

        return boundaries

    def _detect_from_outline(
        self, outline: List, pages_data: List[PageData]
    ) -> List[ChapterBoundary]:
        """Detect chapters from PDF outline.

        Args:
            outline: PDF outline/bookmarks.
            pages_data: List of processed page data.

        Returns:
            List of ChapterBoundary objects.
        """
        boundaries = []

        # Create page number lookup
        page_map = {page.page_number: page for page in pages_data}

        # Process outline items
        for item in outline:
            try:
                title = item.get("title", "")
                page_num = item.get("page", 0)

                if page_num > 0 and page_num in page_map:
                    boundaries.append(
                        ChapterBoundary(
                            chapter_number=0,
                            page_number=page_num,
                            title=title,
                            heading_element=None,
                            is_detected_by="outline",
                        )
                    )
            except (TypeError, AttributeError):
                continue

        return boundaries

    def _detect_from_page(self, page_data: PageData) -> List[ChapterBoundary]:
        """Detect chapters from a single page.

        Args:
            page_data: Processed page data.

        Returns:
            List of ChapterBoundary objects.
        """
        boundaries = []

        # Check headings on the page
        headings = page_data.text.get_large_font_elements(
            min_font_size=self.MIN_HEADING_FONT_SIZE
        )

        for heading in headings:
            # Check if heading matches chapter pattern
            text = heading.text.strip()

            if self._is_chapter_pattern(text):
                boundaries.append(
                    ChapterBoundary(
                        chapter_number=0,
                        page_number=page_data.page_number,
                        title=text,
                        heading_element=heading,
                        is_detected_by="pattern",
                    )
                )
            elif self._is_likely_chapter_heading(heading, page_data.layout.width):
                # Large, centered heading at top of page
                boundaries.append(
                    ChapterBoundary(
                        chapter_number=0,
                        page_number=page_data.page_number,
                        title=text,
                        heading_element=heading,
                        is_detected_by="font_position",
                    )
                )

        return boundaries

    def _is_chapter_pattern(self, text: str) -> bool:
        """Check if text matches a chapter pattern.

        Args:
            text: Text to check.

        Returns:
            True if text matches a chapter pattern.
        """
        for pattern in self._compiled_patterns:
            if pattern.match(text.strip()):
                return True
        return False

    def _is_likely_chapter_heading(
        self, heading: TextElement, page_width: float
    ) -> bool:
        """Check if a heading is likely a chapter heading.

        Args:
            heading: Text element.
            page_width: Page width.

        Returns:
            True if heading is likely a chapter heading.
        """
        # Must have large font
        if heading.font_size < self.MIN_LARGE_HEADING_FONT_SIZE:
            return False

        # Must be bold
        if not heading.is_bold:
            return False

        # Must be centered
        if not heading.is_centered(page_width, self.center_tolerance):
            return False

        # Should be near top of page
        # This is a simplified check; a real implementation would need
        # page height to determine "near top"
        return True

    def _sort_and_deduplicate(self, boundaries: List[ChapterBoundary]) -> List[ChapterBoundary]:
        """Sort boundaries by page number and remove duplicates.

        Args:
            boundaries: List of chapter boundaries.

        Returns:
            Sorted and deduplicated list.
        """
        if not boundaries:
            return []

        # Sort by page number
        boundaries.sort(key=lambda b: b.page_number)

        # Remove duplicates (same page, similar title)
        deduplicated = []
        seen_pages = set()

        for boundary in boundaries:
            if boundary.page_number not in seen_pages:
                deduplicated.append(boundary)
                seen_pages.add(boundary.page_number)
            else:
                # Keep the one with better detection method
                # Priority: outline > pattern > font_position
                existing = next(
                    (b for b in deduplicated if b.page_number == boundary.page_number),
                    None,
                )
                if existing:
                    priority = {"outline": 3, "pattern": 2, "font_position": 1}
                    if priority.get(boundary.is_detected_by, 0) > priority.get(
                        existing.is_detected_by, 0
                    ):
                        deduplicated.remove(existing)
                        deduplicated.append(boundary)

        return deduplicated

    def get_chapter_pages(
        self, boundaries: List[ChapterBoundary], total_pages: int
    ) -> dict:
        """Get page ranges for each chapter.

        Args:
            boundaries: List of chapter boundaries.
            total_pages: Total number of pages in document.

        Returns:
            Dictionary mapping chapter number to (start_page, end_page) tuples.
        """
        if not boundaries:
            return {1: (1, total_pages)}

        chapter_ranges = {}

        for i, boundary in enumerate(boundaries):
            start_page = boundary.page_number

            # End page is next chapter's start - 1, or last page
            if i + 1 < len(boundaries):
                end_page = boundaries[i + 1].page_number - 1
            else:
                end_page = total_pages

            chapter_ranges[boundary.chapter_number] = (start_page, end_page)

        return chapter_ranges

    def get_page_chapter(
        self, page_number: int, boundaries: List[ChapterBoundary]
    ) -> Optional[int]:
        """Get the chapter number for a given page.

        Args:
            page_number: Page number.
            boundaries: List of chapter boundaries.

        Returns:
            Chapter number, or None if page is before first chapter.
        """
        for boundary in reversed(boundaries):
            if boundary.page_number <= page_number:
                return boundary.chapter_number
        return None

    def has_chapters(self, pages_data: List[PageData]) -> bool:
        """Check if document has chapters.

        Args:
            pages_data: List of processed page data.

        Returns:
            True if chapters are detected.
        """
        boundaries = self.detect_chapters(pages_data)
        return len(boundaries) > 0