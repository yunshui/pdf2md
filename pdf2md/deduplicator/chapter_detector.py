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
        r"^Appendix\s+[A-Z0-9]+",  # Appendix A
        r"^附录\s*[A-Z0-9]?",  # 附录
        r"^Index\s*$",  # Index
        r"^References\s*$",  # References
        r"^Bibliography\s*$",  # Bibliography
        r"^Conclusion\s*$",  # Conclusion
        r"^Abstract\s*$",  # Abstract
        r"^Introduction\s*$",  # Introduction
    ]

    # Heading font size threshold (points)
    MIN_HEADING_FONT_SIZE = 14.0
    MIN_LARGE_HEADING_FONT_SIZE = 16.0
    TOP_PAGE_RATIO = 0.2  # Heading must be in top 20% of page

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

        # Detect from visual structure changes
        structure_boundaries = self._detect_from_structure(pages_data)
        boundaries.extend(structure_boundaries)

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

        # Score headings and pick the best one
        scored_headings = []

        for heading in headings:
            text = heading.text.strip()
            score = 0

            # Pattern matching gets high score
            if self._is_chapter_pattern(text):
                score += 100
                scored_headings.append((score, heading, "pattern"))
            elif self._is_likely_chapter_heading(heading, page_data):
                score += 50
                scored_headings.append((score, heading, "font_position"))
            # Additional checks for large, distinctive headings
            elif heading.font_size >= self.MIN_LARGE_HEADING_FONT_SIZE:
                # Check if at top of page
                top_threshold = page_data.layout.height * (1 - self.TOP_PAGE_RATIO)
                if heading.y1 >= top_threshold:
                    score += 20
                    scored_headings.append((score, heading, "position"))

        # Sort by score and take the best one
        if scored_headings:
            scored_headings.sort(key=lambda x: -x[0])
            best_score, best_heading, detection_method = scored_headings[0]

            if best_score > 0:
                boundaries.append(
                    ChapterBoundary(
                        chapter_number=0,
                        page_number=page_data.page_number,
                        title=best_heading.text.strip(),
                        heading_element=best_heading,
                        is_detected_by=detection_method,
                    )
                )

        return boundaries

    def _detect_from_structure(
        self, pages_data: List[PageData]
    ) -> List[ChapterBoundary]:
        """Detect chapters from structural changes in the document.

        Args:
            pages_data: List of processed page data.

        Returns:
            List of ChapterBoundary objects.
        """
        boundaries = []

        if len(pages_data) < 2:
            return boundaries

        # Look for significant layout or text density changes
        for i in range(1, len(pages_data)):
            prev_page = pages_data[i - 1]
            curr_page = pages_data[i]

            # Check for layout change
            if self._has_layout_change(prev_page, curr_page):
                # Check if current page has large heading
                headings = curr_page.text.get_large_font_elements(
                    min_font_size=self.MIN_HEADING_FONT_SIZE
                )
                if headings:
                    best_heading = max(headings, key=lambda h: h.font_size)
                    boundaries.append(
                        ChapterBoundary(
                            chapter_number=0,
                            page_number=curr_page.page_number,
                            title=best_heading.text.strip(),
                            heading_element=best_heading,
                            is_detected_by="structure",
                        )
                    )

            # Check for text density change (could indicate new chapter)
            if self._has_density_change(prev_page, curr_page):
                # Only add if not already detected by other methods
                if not any(b.page_number == curr_page.page_number for b in boundaries):
                    headings = curr_page.text.get_large_font_elements(
                        min_font_size=self.MIN_HEADING_FONT_SIZE
                    )
                    if headings:
                        best_heading = max(headings, key=lambda h: h.font_size)
                        boundaries.append(
                            ChapterBoundary(
                                chapter_number=0,
                                page_number=curr_page.page_number,
                                title=best_heading.text.strip(),
                                heading_element=best_heading,
                                is_detected_by="density",
                            )
                        )

        return boundaries

    def _has_layout_change(self, prev_page: PageData, curr_page: PageData) -> bool:
        """Check if there's a significant layout change between pages.

        Args:
            prev_page: Previous page data.
            curr_page: Current page data.

        Returns:
            True if layout changed significantly.
        """
        # Check for change in number of columns (approximated by text regions)
        if len(prev_page.layout.body_regions) != len(curr_page.layout.body_regions):
            return True

        # Check for change in page width/height (indicates different page type)
        width_change = abs(prev_page.layout.width - curr_page.layout.width)
        height_change = abs(prev_page.layout.height - curr_page.layout.height)

        # More than 10% change is significant
        if width_change > prev_page.layout.width * 0.1:
            return True
        if height_change > prev_page.layout.height * 0.1:
            return True

        return False

    def _has_density_change(self, prev_page: PageData, curr_page: PageData) -> bool:
        """Check if there's a significant text density change between pages.

        Args:
            prev_page: Previous page data.
            curr_page: Current page data.

        Returns:
            True if text density changed significantly.
        """
        prev_density = prev_page.layout.text_density
        curr_density = curr_page.layout.text_density

        # If density is zero on one page but not the other
        if (prev_density == 0) != (curr_density == 0):
            return True

        # More than 30% change is significant
        if prev_density > 0 and curr_density > 0:
            density_change = abs(prev_density - curr_density) / max(prev_density, curr_density)
            return density_change > 0.3

        return False

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
        self, heading: TextElement, page_data: PageData
    ) -> bool:
        """Check if a heading is likely a chapter heading.

        Args:
            heading: Text element.
            page_data: Page data containing layout information.

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
        if not heading.is_centered(page_data.layout.width, self.center_tolerance):
            return False

        # Must be near top of page (in top 20%)
        top_threshold = page_data.layout.height * (1 - self.TOP_PAGE_RATIO)
        # Note: PDF coordinates are from bottom-left, so top of page has higher y value
        if heading.y1 < top_threshold:
            return False

        # Check if heading is significantly larger than other text on page
        # Font size should be at least 1.3x the median font size
        all_elements = page_data.text.elements
        if all_elements:
            font_sizes = [e.font_size for e in all_elements if e.font_size > 0]
            if font_sizes:
                median_font_size = sorted(font_sizes)[len(font_sizes) // 2]
                if heading.font_size < median_font_size * 1.3:
                    return False

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
                # Priority: outline > pattern > font_position > structure > density > position
                existing = next(
                    (b for b in deduplicated if b.page_number == boundary.page_number),
                    None,
                )
                if existing:
                    priority = {
                        "outline": 6,
                        "pattern": 5,
                        "font_position": 4,
                        "structure": 3,
                        "density": 2,
                        "position": 1,
                    }
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