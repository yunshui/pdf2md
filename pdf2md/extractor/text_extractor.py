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

    def __post_init__(self):
        """Initialize additional properties."""
        # Ensure elements are sorted in reading order
        if self.elements:
            self._ensure_reading_order()

    def _ensure_reading_order(self) -> None:
        """Ensure text elements are sorted in reading order."""
        # Group by lines and sort within each line
        lines = self._group_elements_by_lines()
        sorted_elements = []
        for line in lines:
            line_sorted = sorted(line, key=lambda el: el.x0)
            sorted_elements.extend(line_sorted)
        self.elements = sorted_elements

    def _group_elements_by_lines(self) -> List[List[TextElement]]:
        """Group text elements into lines based on y coordinates."""
        if not self.elements:
            return []

        sorted_by_y = sorted(self.elements, key=lambda el: el.y0)
        lines = []
        current_line = [sorted_by_y[0]]

        for element in sorted_by_y[1:]:
            line_threshold = 10.0
            if abs(element.y0 - current_line[0].y0) <= line_threshold:
                current_line.append(element)
            else:
                lines.append(current_line)
                current_line = [element]

        if current_line:
            lines.append(current_line)

        return lines

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

        # Use extract_text_objects for better text extraction
        try:
            text_objects = page.extract_text_objects(layout_tolerance=5)
        except AttributeError:
            # Fall back to character-level extraction if extract_text_objects is not available
            text_objects = []

        if text_objects:
            # Process text objects (which contain words/phrases)
            for obj in text_objects:
                try:
                    if obj.get("object_type") != "char":
                        continue

                    element = TextElement(
                        text=obj.get("text", ""),
                        x0=obj.get("x0", 0),
                        y0=obj.get("top", 0),
                        x1=obj.get("x1", 0),
                        y1=obj.get("bottom", 0),
                        font_name=obj.get("fontname", ""),
                        font_size=obj.get("size", 0),
                        font_color=self._format_color(obj.get("non_stroking_color")),
                        is_bold="bold" in obj.get("fontname", "").lower(),
                        is_italic="italic" in obj.get("fontname", "").lower(),
                    )
                    elements.append(element)
                except Exception as e:
                    logger.debug(f"Error processing text object: {e}")
                    continue
        else:
            # Fall back to character-level extraction
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

        # Sort elements in reading order
        elements = self._sort_elements_by_reading_order(elements)

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

    def _sort_elements_by_reading_order(self, elements: List[TextElement]) -> List[TextElement]:
        """Sort text elements in reading order.

        This implements a proper reading order algorithm that handles:
        - Multi-column layouts
        - Complex text arrangements
        - Proper line-by-line ordering

        Args:
            elements: List of TextElement objects.

        Returns:
            Sorted list of TextElement objects.
        """
        if not elements:
            return []

        # Group elements by lines (similar y coordinates)
        lines = self._group_elements_by_lines(elements)

        # Sort lines from top to bottom
        sorted_lines = sorted(lines, key=lambda line: self._get_line_y_position(line))

        # For multi-column layouts, sort elements within each line
        # Use a more sophisticated approach to detect columns
        column_layout = self._detect_column_layout(sorted_lines)

        # Flatten the sorted lines
        sorted_elements = []
        for line in sorted_lines:
            if column_layout == "multi":
                # For multi-column, sort elements by x position
                line_sorted = sorted(line, key=lambda el: el.x0)
            else:
                # For single column, just sort by x position (left to right)
                line_sorted = sorted(line, key=lambda el: el.x0)
            sorted_elements.extend(line_sorted)

        return sorted_elements

    def _detect_column_layout(self, lines: List[List[TextElement]]) -> str:
        """Detect if the document has a multi-column layout.

        Args:
            lines: List of lines.

        Returns:
            "multi" if multi-column, "single" otherwise.
        """
        if not lines:
            return "single"

        # Simplified column detection
        # Check if there are consistent vertical gaps in x positions
        x_positions = []
        for line in lines:
            for element in line:
                x_positions.append(element.x0)

        if not x_positions:
            return "single"

        x_positions.sort()

        # Check for significant gaps
        gaps = 0
        for i in range(1, len(x_positions)):
            gap = x_positions[i] - x_positions[i-1]
            if gap > 100:  # Large gap suggests column boundary
                gaps += 1

        # If multiple gaps, likely multi-column
        return "multi" if gaps >= 3 else "single"

    def _group_elements_by_lines(self, elements: List[TextElement]) -> List[List[TextElement]]:
        """Group text elements into lines based on y coordinates.

        Args:
            elements: List of TextElement objects.

        Returns:
            List of lines, each line is a list of TextElement objects.
        """
        if not elements:
            return []

        # Sort elements by y position
        sorted_by_y = sorted(elements, key=lambda el: el.y0)

        lines = []
        current_line = [sorted_by_y[0]]

        for element in sorted_by_y[1:]:
            # Check if element is on the same line
            line_threshold = 10.0  # Pixels threshold for being on same line
            if abs(element.y0 - current_line[0].y0) <= line_threshold:
                current_line.append(element)
            else:
                lines.append(current_line)
                current_line = [element]

        if current_line:
            lines.append(current_line)

        return lines

    def _get_line_y_position(self, line: List[TextElement]) -> float:
        """Get the y position of a line.

        Args:
            line: List of TextElement objects.

        Returns:
            Y position of the line.
        """
        if not line:
            return 0.0

        # Use the median y position to be robust
        y_positions = [el.y0 for el in line]
        y_positions.sort()
        return y_positions[len(y_positions) // 2]

    def _merge_adjacent_elements(self, elements: List[TextElement]) -> List[TextElement]:
        """Merge adjacent text elements with same formatting.

        This improved merging logic handles:
        - Font size variations within reasonable tolerance
        - Different fonts on same line (for mixed formatting)
        - Proper word boundaries and spacing

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

            # Check if elements can be merged
            if self._can_merge(previous, current):
                # Merge text with appropriate spacing
                if previous.text and not previous.text.endswith((' ', '\n', '\t')):
                    # Check if we need to add a space
                    if self._needs_space_between(previous, current):
                        previous.text += ' '
                previous.text += current.text

                # Update bounding box
                previous.x0 = min(previous.x0, current.x0)
                previous.y0 = min(previous.y0, current.y0)
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
        # Skip empty elements
        if not elem1.text or not elem2.text:
            return False

        # Must be on same line (similar y position)
        line_tolerance = 10.0
        if abs(elem1.y0 - elem2.y0) > line_tolerance:
            return False

        # Must be close horizontally (gap smaller than typical word/phrase gap)
        gap = elem2.x0 - elem1.x1
        max_gap = 50.0  # Increased tolerance for larger gaps in Chinese
        if gap > max_gap:
            return False

        # Check if they should be merged based on text content
        try:
            last_char = elem1.text.rstrip()[-1]
            first_char = elem2.text[0]
        except IndexError:
            return False

        # Don't merge if previous ends with punctuation and current starts with new text
        if last_char in '.!?。！？;；：':
            if first_char.isupper() or first_char.isdigit():
                return False

        # Check if elements have very different font sizes (likely different sections)
        if elem1.font_size > 0 and elem2.font_size > 0:
            if abs(elem1.font_size - elem2.font_size) > 2.0:
                return False

        return True

    def _needs_space_between(self, elem1: TextElement, elem2: TextElement) -> bool:
        """Determine if a space is needed between two text elements.

        Args:
            elem1: First element.
            elem2: Second element.

        Returns:
            True if a space is needed.
        """
        if not elem1.text or not elem2.text:
            return False

        # Check if gap suggests separate words
        gap = elem2.x0 - elem1.x1

        # Large gap usually indicates separate words
        if gap > 5.0:
            return True

        # Check if characters should be separated
        try:
            last_char = elem1.text[-1]
            first_char = elem2.text[0]
        except IndexError:
            return True  # Safer to add space if indexing fails

        # Common cases where space is needed
        if last_char in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789':
            if first_char in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789':
                return True

        # Chinese characters usually don't need spaces
        if self._is_chinese_char(last_char) and self._is_chinese_char(first_char):
            return False

        return False

    @staticmethod
    def _is_chinese_char(char: str) -> bool:
        """Check if a character is Chinese.

        Args:
            char: Character to check.

        Returns:
            True if character is Chinese.
        """
        if not char:
            return False

        # Unicode ranges for Chinese characters
        char_code = ord(char)
        return (
            (0x4E00 <= char_code <= 0x9FFF) or  # CJK Unified Ideographs
            (0x3400 <= char_code <= 0x4DBF) or  # CJK Unified Ideographs Extension A
            (0x20000 <= char_code <= 0x2A6DF) or  # CJK Unified Ideographs Extension B
            (0xF900 <= char_code <= 0xFAFF)  # CJK Compatibility Ideographs
        )

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