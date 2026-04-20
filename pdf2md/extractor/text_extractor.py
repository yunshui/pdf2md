"""Text extraction from PDF pages."""

from dataclasses import dataclass
from typing import List, Optional

import pdfplumber

from pdf2md.extractor.pdfplumber_types import TYPE_PAGE
from pdf2md.utils.logger import get_logger

logger = get_logger()


@dataclass
class TextElement:
    """Represents a text element with its properties."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    font_name: str = ""
    font_size: float = 0.0
    font_color: str = ""
    is_bold: bool = False
    is_italic: bool = False

    @property
    def width(self) -> float:
        """Get text element width."""
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        """Get text element height."""
        return self.y1 - self.y0

    def is_heading(self, min_font_size: float = 14.0) -> bool:
        """Check if this text element is a heading.

        Args:
            min_font_size: Minimum font size to be considered a heading.

        Returns:
            True if element is likely a heading.
        """
        return (
            self.font_size >= min_font_size
            and self.is_bold
            and len(self.text.strip()) < 100
        )

    def is_centered(self, page_width: float, tolerance: float = 0.1) -> bool:
        """Check if text is centered on the page.

        Args:
            page_width: Width of the page.
            tolerance: Tolerance for centering (as ratio of page width).

        Returns:
            True if text is centered.
        """
        center_x = (self.x0 + self.x1) / 2
        page_center = page_width / 2
        return abs(center_x - page_center) < (page_width * tolerance)


@dataclass
class PageText:
    """Represents all text extracted from a page."""

    elements: List[TextElement]
    raw_text: str

    def get_text_by_position(self, x0: float, y0: float, x1: float, y1: float) -> str:
        """Get text within a bounding box.

        Args:
            x0: Left coordinate.
            y0: Top coordinate.
            x1: Right coordinate.
            y1: Bottom coordinate.

        Returns:
            Text within the bounding box, sorted by reading order.
        """
        matching_elements = [
            el
            for el in self.elements
            if (el.x0 >= x0 and el.y0 >= y0 and el.x1 <= x1 and el.y1 <= y1)
        ]

        # Sort by reading order (top to bottom, left to right)
        matching_elements.sort(key=lambda el: (-el.y0, el.x0))

        return "\n".join(el.text for el in matching_elements)

    def get_headings(self, min_font_size: float = 14.0) -> List[TextElement]:
        """Get all heading elements.

        Args:
            min_font_size: Minimum font size for headings.

        Returns:
            List of heading elements.
        """
        return [el for el in self.elements if el.is_heading(min_font_size)]

    def get_large_font_elements(
        self, min_font_size: float = 16.0
    ) -> List[TextElement]:
        """Get elements with large font size.

        Args:
            min_font_size: Minimum font size.

        Returns:
            List of large font elements.
        """
        return [el for el in self.elements if el.font_size >= min_font_size]


class TextExtractor:
    """Extracts text content from PDF pages."""

    def __init__(self, preserve_formatting: bool = True) -> None:
        """Initialize the text extractor.

        Args:
            preserve_formatting: Whether to preserve font information.
        """
        self.preserve_formatting = preserve_formatting

    def extract(self, page: TYPE_PAGE) -> PageText:
        """Extract text from a PDF page.

        Args:
            page: pdfplumber Page object.

        Returns:
            PageText with extracted text elements.
        """
        if not hasattr(page, "chars") or not page.chars:
            logger.debug("No text characters found on page")
            return PageText(elements=[], raw_text="")

        elements = []
        raw_text = ""

        try:
            # Extract raw text
            raw_text = page.extract_text() or ""

            # Extract text elements with formatting
            if self.preserve_formatting:
                elements = self._extract_text_elements(page)
            else:
                elements = self._extract_plain_text_elements(page)

            logger.debug(f"Extracted {len(elements)} text elements from page")

        except Exception as e:
            logger.error(f"Error extracting text from page: {e}")
            return PageText(elements=[], raw_text="")

        return PageText(elements=elements, raw_text=raw_text)

    def _extract_text_elements(self, page: TYPE_PAGE) -> List[TextElement]:
        """Extract text elements with formatting information.

        Args:
            page: pdfplumber Page object.

        Returns:
            List of TextElement objects.
        """
        elements = []

        for char in page.chars:
            try:
                element = TextElement(
                    text=char.get("text", ""),
                    x0=char.get("x0", 0),
                    y0=char.get("top", 0),
                    x1=char.get("x1", 0),
                    y1=char.get("bottom", 0),
                    font_name=char.get("fontname", ""),
                    font_size=char.get("size", 0),
                    font_color=self._format_color(char.get("non_stroking_color")),
                    is_bold="bold" in char.get("fontname", "").lower(),
                    is_italic="italic" in char.get("fontname", "").lower(),
                )
                elements.append(element)
            except Exception as e:
                logger.debug(f"Error processing character: {e}")
                continue

        # Merge adjacent characters with same formatting
        elements = self._merge_adjacent_elements(elements)

        return elements

    def _extract_plain_text_elements(self, page: TYPE_PAGE) -> List[TextElement]:
        """Extract text without formatting information.

        Args:
            page: pdfplumber Page object.

        Returns:
            List of TextElement objects with minimal information.
        """
        elements = []

        for char in page.chars:
            try:
                element = TextElement(
                    text=char.get("text", ""),
                    x0=char.get("x0", 0),
                    y0=char.get("top", 0),
                    x1=char.get("x1", 0),
                    y1=char.get("bottom", 0),
                )
                elements.append(element)
            except Exception as e:
                logger.debug(f"Error processing character: {e}")
                continue

        return elements

    def _merge_adjacent_elements(self, elements: List[TextElement]) -> List[TextElement]:
        """Merge adjacent text elements with same formatting.

        Args:
            elements: List of TextElement objects.

        Returns:
            Merged list of TextElement objects.
        """
        if not elements:
            return []

        merged = [elements[0]]

        for current in elements[1:]:
            previous = merged[-1]

            # Check if elements can be merged (similar formatting and position)
            if self._can_merge(previous, current):
                # Merge text
                previous.text += current.text
                # Update bounding box
                previous.x1 = max(previous.x1, current.x1)
                previous.y1 = max(previous.y1, current.y1)
            else:
                merged.append(current)

        return merged

    def _can_merge(self, elem1: TextElement, elem2: TextElement) -> bool:
        """Check if two elements can be merged.

        Args:
            elem1: First element.
            elem2: Second element.

        Returns:
            True if elements can be merged.
        """
        # Must have same font and size
        if elem1.font_name != elem2.font_name or abs(elem1.font_size - elem2.font_size) > 0.1:
            return False

        # Must be on same line (similar y position)
        line_tolerance = 5.0
        if abs(elem1.y0 - elem2.y0) > line_tolerance:
            return False

        # Must be close horizontally (gap smaller than typical word gap)
        gap = elem2.x0 - elem1.x1
        if gap > 20.0:  # Typical word gap threshold
            return False

        return True

    @staticmethod
    def _format_color(color_value: Optional[tuple]) -> str:
        """Format a color tuple to hex string.

        Args:
            color_value: Color tuple (r, g, b).

        Returns:
            Hex color string.
        """
        if not color_value or len(color_value) < 3:
            return ""

        r = int(color_value[0] * 255)
        g = int(color_value[1] * 255)
        b = int(color_value[2] * 255)

        return f"#{r:02x}{g:02x}{b:02x}"

    def get_text_statistics(self, page_text: PageText) -> dict:
        """Get statistics about extracted text.

        Args:
            page_text: PageText object.

        Returns:
            Dictionary with text statistics.
        """
        if not page_text.elements:
            return {
                "character_count": 0,
                "word_count": 0,
                "line_count": 0,
                "avg_font_size": 0.0,
                "has_large_font": False,
            }

        char_count = sum(len(el.text) for el in page_text.elements)
        word_count = len(page_text.raw_text.split())

        # Estimate line count based on unique y positions
        unique_y_positions = set(int(el.y0) for el in page_text.elements)
        line_count = len(unique_y_positions)

        # Calculate average font size
        font_sizes = [el.font_size for el in page_text.elements if el.font_size > 0]
        avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 0.0

        # Check for large fonts (potential headings)
        has_large_font = any(el.font_size >= 16.0 for el in page_text.elements)

        return {
            "character_count": char_count,
            "word_count": word_count,
            "line_count": line_count,
            "avg_font_size": avg_font_size,
            "has_large_font": has_large_font,
        }