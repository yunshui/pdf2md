"""Edge text detection and handling."""

from collections import defaultdict
from dataclasses import dataclass
from typing import List, Optional

from pdf2md.core.page_processor import PageData
from pdf2md.extractor import TextRegion, TextRegionType
from pdf2md.utils.logger import get_logger

logger = get_logger()


@dataclass
class EdgeText:
    """Represents text found at page edges."""

    text: str
    page_number: int
    position: str  # "left", "right", "top", "bottom"
    x0: float
    y0: float
    x1: float
    y1: float

    def __str__(self) -> str:
        """Get string representation."""
        return f"[{self.position} page {self.page_number}]: {self.text}"


class EdgeTextHandler:
    """Detects and handles edge text in PDF pages."""

    def __init__(
        self,
        edge_margin: float = 30.0,
        deduplicate_across_pages: bool = True,
    ) -> None:
        """Initialize the edge text handler.

        Args:
            edge_margin: Margin from page edges in points.
            deduplicate_across_pages: Whether to deduplicate edge text across pages.
        """
        self.edge_margin = edge_margin
        self.deduplicate_across_pages = deduplicate_across_pages

    def extract_edge_text(self, pages_data: List[PageData]) -> List[EdgeText]:
        """Extract edge text from all pages.

        Args:
            pages_data: List of processed page data.

        Returns:
            List of edge text objects.
        """
        logger.info("Extracting edge text...")

        edge_texts = []

        for page_data in pages_data:
            page_edge_texts = self._extract_from_page(page_data)
            edge_texts.extend(page_edge_texts)

        logger.info(f"Found {len(edge_texts)} edge text items")

        if self.deduplicate_across_pages:
            edge_texts = self._deduplicate(edge_texts)

        return edge_texts

    def _extract_from_page(self, page_data: PageData) -> List[EdgeText]:
        """Extract edge text from a single page.

        Args:
            page_data: Processed page data.

        Returns:
            List of edge text objects.
        """
        edge_texts = []

        width = page_data.layout.width
        height = page_data.layout.height

        # Get edge regions from layout analysis
        for region in page_data.layout.edge_regions:
            if region.region_type != TextRegionType.EDGE:
                continue

            # Determine position
            position = self._determine_position(region, width, height)

            edge_text = EdgeText(
                text=region.text.strip(),
                page_number=page_data.page_number,
                position=position,
                x0=region.x0,
                y0=region.y0,
                x1=region.x1,
                y1=region.y1,
            )

            edge_texts.append(edge_text)

        return edge_texts

    def _determine_position(
        self, region: TextRegion, page_width: float, page_height: float
    ) -> str:
        """Determine which edge a text region is on.

        Args:
            region: Text region.
            page_width: Page width.
            page_height: Page height.

        Returns:
            Position string ("left", "right", "top", "bottom").
        """
        # Calculate distances from each edge
        left_dist = region.x0
        right_dist = page_width - region.x1
        top_dist = region.y0
        bottom_dist = page_height - region.y1

        # Find minimum distance
        distances = {
            "left": left_dist,
            "right": right_dist,
            "top": top_dist,
            "bottom": bottom_dist,
        }

        min_pos = min(distances, key=distances.get)

        return min_pos

    def _deduplicate(self, edge_texts: List[EdgeText]) -> List[EdgeText]:
        """Deduplicate edge text across pages.

        Args:
            edge_texts: List of edge text objects.

        Returns:
            Deduplicated list.
        """
        if not edge_texts:
            return []

        # Group by normalized text and position
        groups = defaultdict(list)

        for edge_text in edge_texts:
            key = (self._normalize_text(edge_text.text), edge_text.position)
            groups[key].append(edge_text)

        # For each group, keep only the first occurrence
        deduplicated = []

        for group in groups.values():
            # Sort by page number
            group.sort(key=lambda et: et.page_number)

            # Keep first occurrence
            deduplicated.append(group[0])

        return deduplicated

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison.

        Args:
            text: Text to normalize.

        Returns:
            Normalized text.
        """
        # Remove extra whitespace
        return " ".join(text.split()).lower()

    def get_edge_text_by_position(
        self, edge_texts: List[EdgeText], position: str
    ) -> List[EdgeText]:
        """Get edge text for a specific position.

        Args:
            edge_texts: List of edge text objects.
            position: Position to filter by.

        Returns:
            Filtered list of edge text.
        """
        return [et for et in edge_texts if et.position == position]

    def get_edge_text_by_page(
        self, edge_texts: List[EdgeText], page_number: int
    ) -> List[EdgeText]:
        """Get edge text for a specific page.

        Args:
            edge_texts: List of edge text objects.
            page_number: Page number.

        Returns:
            Filtered list of edge text.
        """
        return [et for et in edge_texts if et.page_number == page_number]

    def format_edge_text(
        self, edge_texts: List[EdgeText], format: str = "markdown"
    ) -> str:
        """Format edge text for output.

        Args:
            edge_texts: List of edge text objects.
            format: Output format ("markdown", "plain", "list").

        Returns:
            Formatted string.
        """
        if not edge_texts:
            return ""

        if format == "markdown":
            return self._format_markdown(edge_texts)
        elif format == "plain":
            return self._format_plain(edge_texts)
        elif format == "list":
            return self._format_list(edge_texts)
        else:
            return self._format_plain(edge_texts)

    def _format_markdown(self, edge_texts: List[EdgeText]) -> str:
        """Format edge text as Markdown.

        Args:
            edge_texts: List of edge text objects.

        Returns:
            Markdown formatted string (without header, as it's added by caller).
        """
        lines = []

        # Group by position
        by_position = defaultdict(list)
        for et in edge_texts:
            by_position[et.position].append(et)

        for position in ["left", "right", "top", "bottom"]:
            if position in by_position:
                lines.append(f"### {position.title()}")
                for et in by_position[position]:
                    lines.append(f"- Page {et.page_number}: {et.text}")
                lines.append("")

        return "\n".join(lines)

    def _format_plain(self, edge_texts: List[EdgeText]) -> str:
        """Format edge text as plain text.

        Args:
            edge_texts: List of edge text objects.

        Returns:
            Plain text string.
        """
        lines = []

        for et in edge_texts:
            lines.append(f"[{et.position}] Page {et.page_number}: {et.text}")

        return "\n".join(lines)

    def _format_list(self, edge_texts: List[EdgeText]) -> str:
        """Format edge text as a simple list.

        Args:
            edge_texts: List of edge text objects.

        Returns:
            List formatted string.
        """
        return "\n".join(et.text for et in edge_texts)

    def remove_edge_text_from_body(
        self, pages_data: List[PageData], edge_texts: List[EdgeText]
    ) -> None:
        """Remove edge text from page body content.

        Args:
            pages_data: List of page data (modified in place).
            edge_texts: List of edge text to remove.
        """
        # Group edge texts by page number
        edge_by_page = defaultdict(list)
        for et in edge_texts:
            edge_by_page[et.page_number].append(et)

        # Remove edge text from each page
        for page_data in pages_data:
            if page_data.page_number in edge_by_page:
                page_edge_texts = edge_by_page[page_data.page_number]
                self._remove_from_page_content(page_data, page_edge_texts)

    def _remove_from_page_content(
        self, page_data: PageData, edge_texts: List[EdgeText]
    ) -> None:
        """Remove edge text from page content.

        Args:
            page_data: Page data (modified in place).
            edge_texts: Edge texts to remove.
        """
        # This is a placeholder for the actual implementation
        # The complete implementation would need to modify the text content
        # by removing or masking the edge text portions

        for edge_text in edge_texts:
            # Remove edge text from layout regions
            page_data.layout.edge_regions = [
                r
                for r in page_data.layout.edge_regions
                if not (
                    abs(r.x0 - edge_text.x0) < 1.0
                    and abs(r.y0 - edge_text.y0) < 1.0
                )
            ]

    def get_edge_text_summary(self, edge_texts: List[EdgeText]) -> dict:
        """Get summary statistics about edge text.

        Args:
            edge_texts: List of edge text objects.

        Returns:
            Summary dictionary.
        """
        if not edge_texts:
            return {"total": 0, "by_position": {}, "by_page": {}}

        # Count by position
        by_position = defaultdict(int)
        for et in edge_texts:
            by_position[et.position] += 1

        # Count by page
        by_page = defaultdict(int)
        for et in edge_texts:
            by_page[et.page_number] += 1

        return {
            "total": len(edge_texts),
            "by_position": dict(by_position),
            "by_page": dict(by_page),
        }