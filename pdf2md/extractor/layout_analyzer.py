"""Layout analysis for PDF pages."""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

import pdfplumber

from pdf2md.utils.logger import get_logger

logger = get_logger()


class TextRegionType(Enum):
    """Types of text regions on a page."""

    HEADER = "header"
    FOOTER = "footer"
    BODY = "body"
    EDGE = "edge"
    SIDEBAR = "sidebar"


@dataclass
class TextRegion:
    """Represents a region of text on a page."""

    region_type: TextRegionType
    x0: float
    y0: float
    x1: float
    y1: float
    text: str

    @property
    def width(self) -> float:
        """Get region width."""
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        """Get region height."""
        return self.y1 - self.y0

    @property
    def center_x(self) -> float:
        """Get region center X coordinate."""
        return (self.x0 + self.x1) / 2

    @property
    def center_y(self) -> float:
        """Get region center Y coordinate."""
        return (self.y0 + self.y1) / 2


@dataclass
class LayoutInfo:
    """Information about page layout."""

    width: float
    height: float
    header_region: Optional[TextRegion]
    footer_region: Optional[TextRegion]
    body_regions: List[TextRegion]
    edge_regions: List[TextRegion]
    sidebar_regions: List[TextRegion]
    has_images: bool
    has_tables: bool
    text_density: float

    def get_header_text(self) -> str:
        """Get header text."""
        return self.header_region.text if self.header_region else ""

    def get_footer_text(self) -> str:
        """Get footer text."""
        return self.footer_region.text if self.footer_region else ""

    def get_edge_texts(self) -> List[str]:
        """Get all edge text strings."""
        return [region.text for region in self.edge_regions]


class LayoutAnalyzer:
    """Analyzes page layout to identify different text regions."""

    def __init__(
        self,
        header_height: float = 50.0,
        footer_height: float = 50.0,
        edge_margin: float = 30.0,
    ) -> None:
        """Initialize the layout analyzer.

        Args:
            header_height: Maximum height for header region.
            footer_height: Maximum height for footer region.
            edge_margin: Margin from page edges for edge text detection.
        """
        self.header_height = header_height
        self.footer_height = footer_height
        self.edge_margin = edge_margin

    def analyze(self, page: pdfplumber.Page) -> LayoutInfo:
        """Analyze the layout of a PDF page.

        Args:
            page: pdfplumber Page object.

        Returns:
            LayoutInfo with layout analysis results.
        """
        width = page.width
        height = page.height

        # Get text content
        text = page.extract_text() or ""
        words = page.extract_words() or []

        # Detect regions
        header_region = self._detect_header(page, words, width)
        footer_region = self._detect_footer(page, words, width, height)
        body_regions = self._detect_body(page, words, width, height)
        edge_regions = self._detect_edge_text(page, words, width, height)
        sidebar_regions = self._detect_sidebars(page, words, width, height)

        # Check for images and tables
        has_images = hasattr(page, "images") and len(page.images) > 0
        has_tables = self._has_tables(page)

        # Calculate text density
        text_density = self._calculate_text_density(page, words)

        logger.debug(
            f"Layout analysis: {len(body_regions)} body regions, "
            f"{len(edge_regions)} edge regions, "
            f"text density: {text_density:.2f}"
        )

        return LayoutInfo(
            width=width,
            height=height,
            header_region=header_region,
            footer_region=footer_region,
            body_regions=body_regions,
            edge_regions=edge_regions,
            sidebar_regions=sidebar_regions,
            has_images=has_images,
            has_tables=has_tables,
            text_density=text_density,
        )

    def _detect_header(
        self, page: pdfplumber.Page, words: List[dict], width: float
    ) -> Optional[TextRegion]:
        """Detect header region.

        Args:
            page: pdfplumber Page object.
            words: List of words on the page.
            width: Page width.

        Returns:
            TextRegion for header, or None if not found.
        """
        header_words = [
            w for w in words if w["top"] < self.header_height and w["bottom"] > 0
        ]

        if not header_words:
            return None

        # Calculate bounding box
        x0 = min(w["x0"] for w in header_words)
        y0 = min(w["top"] for w in header_words)
        x1 = max(w["x1"] for w in header_words)
        y1 = max(w["bottom"] for w in header_words)

        # Build text
        text = " ".join(w["text"] for w in header_words)

        return TextRegion(
            region_type=TextRegionType.HEADER,
            x0=x0,
            y0=y0,
            x1=x1,
            y1=y1,
            text=text,
        )

    def _detect_footer(
        self, page: pdfplumber.Page, words: List[dict], width: float, height: float
    ) -> Optional[TextRegion]:
        """Detect footer region.

        Args:
            page: pdfplumber Page object.
            words: List of words on the page.
            width: Page width.
            height: Page height.

        Returns:
            TextRegion for footer, or None if not found.
        """
        footer_top = height - self.footer_height
        footer_words = [
            w
            for w in words
            if w["top"] >= footer_top and w["bottom"] <= height
        ]

        if not footer_words:
            return None

        # Calculate bounding box
        x0 = min(w["x0"] for w in footer_words)
        y0 = min(w["top"] for w in footer_words)
        x1 = max(w["x1"] for w in footer_words)
        y1 = max(w["bottom"] for w in footer_words)

        # Build text
        text = " ".join(w["text"] for w in footer_words)

        return TextRegion(
            region_type=TextRegionType.FOOTER,
            x0=x0,
            y0=y0,
            x1=x1,
            y1=y1,
            text=text,
        )

    def _detect_body(
        self, page: pdfplumber.Page, words: List[dict], width: float, height: float
    ) -> List[TextRegion]:
        """Detect body text regions.

        Args:
            page: pdfplumber Page object.
            words: List of words on the page.
            width: Page width.
            height: Page height.

        Returns:
            List of TextRegion objects for body text.
        """
        # Filter out header and footer words
        body_words = [
            w
            for w in words
            if (
                w["top"] >= self.header_height
                and w["bottom"] <= height - self.footer_height
            )
        ]

        if not body_words:
            return []

        # Group words into lines (similar y coordinates)
        lines = self._group_words_by_line(body_words)

        # Group lines into paragraphs (vertical proximity)
        paragraphs = self._group_lines_to_paragraphs(lines)

        # Create regions for paragraphs
        regions = []
        for paragraph in paragraphs:
            if not paragraph:
                continue

            x0 = min(w["x0"] for w in paragraph)
            y0 = min(w["top"] for w in paragraph)
            x1 = max(w["x1"] for w in paragraph)
            y1 = max(w["bottom"] for w in paragraph)

            text = " ".join(w["text"] for w in paragraph)

            regions.append(
                TextRegion(
                    region_type=TextRegionType.BODY,
                    x0=x0,
                    y0=y0,
                    x1=x1,
                    y1=y1,
                    text=text,
                )
            )

        return regions

    def _detect_edge_text(
        self, page: pdfplumber.Page, words: List[dict], width: float, height: float
    ) -> List[TextRegion]:
        """Detect edge text (text in page margins).

        Args:
            page: pdfplumber Page object.
            words: List of words on the page.
            width: Page width.
            height: Page height.

        Returns:
            List of TextRegion objects for edge text.
        """
        edge_words = []

        # Check left edge
        left_edge = [w for w in words if w["x0"] < self.edge_margin]
        # Check right edge
        right_edge = [
            w for w in words if w["x1"] > width - self.edge_margin
        ]

        edge_words = left_edge + right_edge

        if not edge_words:
            return []

        # Group edge words into regions
        regions = []
        for word in edge_words:
            region = TextRegion(
                region_type=TextRegionType.EDGE,
                x0=word["x0"],
                y0=word["top"],
                x1=word["x1"],
                y1=word["bottom"],
                text=word["text"],
            )
            regions.append(region)

        return regions

    def _detect_sidebars(
        self, page: pdfplumber.Page, words: List[dict], width: float, height: float
    ) -> List[TextRegion]:
        """Detect sidebar regions (vertical text columns).

        Args:
            page: pdfplumber Page object.
            words: List of words on the page.
            width: Page width.
            height: Page height.

        Returns:
            List of TextRegion objects for sidebars.
        """
        # This is a simplified detection
        # A more sophisticated implementation would analyze column layout
        return []

    def _group_words_by_line(self, words: List[dict]) -> List[List[dict]]:
        """Group words into lines based on Y coordinates.

        Args:
            words: List of word dictionaries.

        Returns:
            List of lines, each line is a list of words.
        """
        if not words:
            return []

        # Sort by Y coordinate
        sorted_words = sorted(words, key=lambda w: w["top"])

        lines = []
        current_line = [sorted_words[0]]

        for word in sorted_words[1:]:
            # Check if word is on the same line (similar Y)
            if abs(word["top"] - current_line[0]["top"]) < 5.0:
                current_line.append(word)
            else:
                # Start new line
                lines.append(current_line)
                current_line = [word]

        if current_line:
            lines.append(current_line)

        # Sort words within each line by X coordinate
        for line in lines:
            line.sort(key=lambda w: w["x0"])

        return lines

    def _group_lines_to_paragraphs(
        self, lines: List[List[dict]], line_spacing: float = 20.0
    ) -> List[List[dict]]:
        """Group lines into paragraphs based on spacing.

        Args:
            lines: List of lines, each line is a list of words.
            line_spacing: Maximum spacing between lines in same paragraph.

        Returns:
            List of paragraphs, each paragraph is a list of words.
        """
        if not lines:
            return []

        paragraphs = []
        current_paragraph = []

        for i, line in enumerate(lines):
            if not current_paragraph:
                current_paragraph = line
            else:
                # Check spacing from previous line
                prev_line_bottom = max(w["bottom"] for w in current_paragraph)
                current_line_top = min(w["top"] for w in line)

                if current_line_top - prev_line_bottom < line_spacing:
                    # Same paragraph
                    current_paragraph.extend(line)
                else:
                    # New paragraph
                    paragraphs.append(current_paragraph)
                    current_paragraph = line

        if current_paragraph:
            paragraphs.append(current_paragraph)

        return paragraphs

    def _has_tables(self, page: pdfplumber.Page) -> bool:
        """Check if page contains tables.

        Args:
            page: pdfplumber Page object.

        Returns:
            True if tables are found.
        """
        if not hasattr(page, "find_tables"):
            return False

        try:
            tables = page.find_tables()
            return len(tables) > 0
        except Exception:
            return False

    def _calculate_text_density(self, page: pdfplumber.Page, words: List[dict]) -> float:
        """Calculate text density (text area / page area).

        Args:
            page: pdfplumber Page object.
            words: List of words on the page.

        Returns:
            Text density ratio (0.0 to 1.0).
        """
        if not words:
            return 0.0

        page_area = page.width * page.height
        if page_area == 0:
            return 0.0

        # Calculate total text bounding box area
        total_text_area = 0.0
        for word in words:
            word_width = word["x1"] - word["x0"]
            word_height = word["bottom"] - word["top"]
            total_text_area += word_width * word_height

        return total_text_area / page_area