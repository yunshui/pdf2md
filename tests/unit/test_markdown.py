"""Unit tests for Markdown module."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from unittest.mock import Mock

import pytest

from pdf2md.markdown.table_formatter import TableFormatter
from pdf2md.markdown.linker import Linker


@dataclass
class MockTableCell:
    """Mock TableCell for testing."""
    text: str
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1


@dataclass
class MockTable:
    """Mock Table for testing."""
    cells: List[MockTableCell]
    num_rows: int
    num_cols: int

    def get_cell(self, row: int, col: int) -> Optional[MockTableCell]:
        """Get cell at position."""
        for cell in self.cells:
            if (
                cell.row <= row < cell.row + cell.row_span
                and cell.col <= col < cell.col + cell.col_span
            ):
                return cell
        return None


@dataclass
class MockImageInfo:
    """Mock ImageInfo for testing."""
    path: str
    width: int = 100
    height: int = 100
    page_number: int = 1


class TestTableFormatter:
    """Test cases for TableFormatter class."""

    def test_init_default(self):
        """Test TableFormatter initialization with default parameters."""
        formatter = TableFormatter()
        assert formatter.max_column_width == 100

    def test_init_custom(self):
        """Test TableFormatter initialization with custom parameters."""
        formatter = TableFormatter(max_column_width=200)
        assert formatter.max_column_width == 200

    def test_format_table_empty(self):
        """Test formatting an empty table."""
        formatter = TableFormatter()
        table = MockTable(cells=[], num_rows=0, num_cols=0)
        result = formatter.format_table(table)
        assert result == ""

    def test_format_table_simple(self):
        """Test formatting a simple table."""
        formatter = TableFormatter()
        cells = [
            MockTableCell("Header 1", 0, 0),
            MockTableCell("Header 2", 0, 1),
            MockTableCell("Row 1 Col 1", 1, 0),
            MockTableCell("Row 1 Col 2", 1, 1),
        ]
        table = MockTable(cells=cells, num_rows=2, num_cols=2)

        result = formatter.format_table(table)
        assert "| Header 1 | Header 2 |" in result
        assert "| Row 1 Col 1 | Row 1 Col 2 |" in result
        assert "|---|" in result

    def test_format_table_with_pipe(self):
        """Test formatting table with pipe characters (should be escaped)."""
        formatter = TableFormatter()
        cells = [
            MockTableCell("A|B", 0, 0),
            MockTableCell("C|D", 0, 1),
        ]
        table = MockTable(cells=cells, num_rows=1, num_cols=2)

        result = formatter.format_table(table)
        assert "\\|" in result  # Pipe should be escaped

    def test_format_table_truncate(self):
        """Test truncating long text in cells."""
        formatter = TableFormatter(max_column_width=10)
        long_text = "This is a very long text that should be truncated"
        cells = [
            MockTableCell(long_text, 0, 0),
        ]
        table = MockTable(cells=cells, num_rows=1, num_cols=1)

        result = formatter.format_table(table)
        assert "..." in result
        assert len(result) < len(long_text) + 20

    def test_format_table_list(self):
        """Test formatting multiple tables."""
        formatter = TableFormatter()
        cells1 = [
            MockTableCell("T1 H1", 0, 0),
            MockTableCell("T1 D1", 1, 0),
        ]
        cells2 = [
            MockTableCell("T2 H1", 0, 0),
            MockTableCell("T2 D1", 1, 0),
        ]
        tables = [
            MockTable(cells=cells1, num_rows=2, num_cols=1),
            MockTable(cells=cells2, num_rows=2, num_cols=1),
        ]

        result = formatter.format_table_list(tables)
        assert "### Table 1" in result
        assert "### Table 2" in result
        assert "T1 H1" in result
        assert "T2 H1" in result

    def test_format_table_list_empty(self):
        """Test formatting empty table list."""
        formatter = TableFormatter()
        result = formatter.format_table_list([])
        assert result == ""

    def test_format_cell_text_empty(self):
        """Test formatting empty cell text."""
        formatter = TableFormatter()
        result = formatter._format_cell_text("")
        assert result == ""

    def test_format_cell_text_none(self):
        """Test formatting None cell text."""
        formatter = TableFormatter()
        result = formatter._format_cell_text(None)
        assert result == ""

    def test_calculate_column_widths(self):
        """Test calculating column widths."""
        formatter = TableFormatter()
        cells = [
            MockTableCell("Short", 0, 0),
            MockTableCell("A very long header", 0, 1),
            MockTableCell("Medium text", 1, 0),
            MockTableCell("Data", 1, 1),
        ]
        table = MockTable(cells=cells, num_rows=2, num_cols=2)

        widths = formatter.calculate_column_widths(table)
        assert widths[0] == max(5, 12)  # max("Short", "Medium text")
        assert widths[1] == max(18, 4)  # max("A very long header", "Data")

    def test_calculate_column_widths_empty(self):
        """Test calculating widths for empty table."""
        formatter = TableFormatter()
        table = MockTable(cells=[], num_rows=0, num_cols=0)

        widths = formatter.calculate_column_widths(table)
        assert widths == []

    def test_format_with_alignment_default(self):
        """Test formatting table with default (left) alignment."""
        formatter = TableFormatter()
        cells = [
            MockTableCell("H1", 0, 0),
            MockTableCell("H2", 0, 1),
            MockTableCell("D1", 1, 0),
            MockTableCell("D2", 1, 1),
        ]
        table = MockTable(cells=cells, num_rows=2, num_cols=2)

        result = formatter.format_with_alignment(table)
        assert "---|" in result  # Left alignment indicator

    def test_format_with_alignment_center(self):
        """Test formatting table with center alignment."""
        formatter = TableFormatter()
        cells = [MockTableCell("H1", 0, 0)]
        table = MockTable(cells=cells, num_rows=1, num_cols=1)

        result = formatter.format_with_alignment(table, alignments=["center"])
        assert ":---:" in result  # Center alignment indicator

    def test_format_with_alignment_right(self):
        """Test formatting table with right alignment."""
        formatter = TableFormatter()
        cells = [MockTableCell("H1", 0, 0)]
        table = MockTable(cells=cells, num_rows=1, num_cols=1)

        result = formatter.format_with_alignment(table, alignments=["right"])
        assert "---:" in result  # Right alignment indicator

    def test_format_with_alignment_mixed(self):
        """Test formatting table with mixed alignments."""
        formatter = TableFormatter()
        cells = [
            MockTableCell("H1", 0, 0),
            MockTableCell("H2", 0, 1),
            MockTableCell("H3", 0, 2),
        ]
        table = MockTable(cells=cells, num_rows=1, num_cols=3)

        result = formatter.format_with_alignment(
            table, alignments=["left", "center", "right"]
        )
        assert "---|" in result
        assert ":---:" in result
        assert "---:" in result


class TestLinker:
    """Test cases for Linker class."""

    def test_init_default(self):
        """Test Linker initialization with default parameters."""
        linker = Linker()
        assert linker.base_path == Path.cwd()

    def test_init_with_base_path(self):
        """Test Linker initialization with base_path."""
        linker = Linker(base_path=Path("/test"))
        assert linker.base_path == Path("/test")

    def test_create_image_link(self):
        """Test creating image link."""
        linker = Linker()
        image_info = MockImageInfo(path="/test/assets/image.png")

        result = linker.create_image_link(image_info)
        assert result.startswith("![")
        assert result.endswith("]")
        assert "image.png" in result

    def test_create_image_link_with_output_dir(self):
        """Test creating image link with output directory."""
        linker = Linker(base_path=Path("/output"))
        image_info = MockImageInfo(path="/output/assets/image.png")

        result = linker.create_image_link(image_info, Path("/output"))
        assert "assets/image.png" in result

    def test_create_image_link_with_size(self):
        """Test creating image link with size specification."""
        linker = Linker()
        image_info = MockImageInfo(path="/test/assets/image.png")

        result = linker.create_image_link_with_size(image_info, max_width=200)
        assert '<img src=' in result
        assert 'width="200"' in result

    def test_create_section_link(self):
        """Test creating section link."""
        linker = Linker()
        result = linker.create_section_link("Section Title")
        assert "[Section Title]" in result
        assert result.endswith(")")

    def test_create_section_link_with_file(self):
        """Test creating section link with file path."""
        linker = Linker()
        result = linker.create_section_link(
            "Section Title", section_file="docs/section1.md"
        )
        assert "docs/section1.md" in result

    def test_create_section_link_with_anchor(self):
        """Test creating section link with custom anchor."""
        linker = Linker()
        result = linker.create_section_link(
            "Section Title", anchor="custom-anchor"
        )
        assert "custom-anchor" in result

    def test_create_toc_link(self):
        """Test creating TOC link."""
        linker = Linker()
        result = linker.create_toc_link("Chapter 1", "docs/chapter1.md")
        assert "- [Chapter 1]" in result
        assert "docs/chapter1.md" in result

    def test_create_toc_link_with_page(self):
        """Test creating TOC link with page number."""
        linker = Linker()
        result = linker.create_toc_link(
            "Chapter 1", "docs/chapter1.md", page_number=10
        )
        assert "(page 10)" in result

    def test_get_relative_path(self):
        """Test getting relative path."""
        linker = Linker(base_path=Path("/output"))
        target = Path("/output/assets/image.png")
        relative = linker._get_relative_path(target, Path("/output"))
        assert "assets/image.png" in relative

    def test_get_image_alt_text(self):
        """Test generating image alt text."""
        linker = Linker()
        image_info = MockImageInfo(path="/assets/my_test_image.png")

        alt_text = linker._get_image_alt_text(image_info)
        assert "My Test Image" == alt_text or alt_text == "My Test Image"

    def test_create_anchor(self):
        """Test creating anchor from text."""
        linker = Linker()
        anchor = linker._create_anchor("Section Title Here")
        assert anchor == "section-title-here"

    def test_create_anchor_special_chars(self):
        """Test creating anchor with special characters."""
        linker = Linker()
        anchor = linker._create_anchor("Section @#$%^&*()")
        assert "@" not in anchor
        assert "#" not in anchor

    def test_create_image_gallery(self):
        """Test creating image gallery."""
        linker = Linker()
        images = [
            MockImageInfo(path="/assets/img1.png"),
            MockImageInfo(path="/assets/img2.png"),
        ]

        result = linker.create_image_gallery(images)
        assert "## Images" in result
        assert "img1.png" in result
        assert "img2.png" in result

    def test_create_image_gallery_empty(self):
        """Test creating empty image gallery."""
        linker = Linker()
        result = linker.create_image_gallery([])
        assert result == ""

    def test_update_image_links(self):
        """Test updating image links in markdown."""
        linker = Linker()
        markdown = "![Old Image](/old/path/image.png)"
        mappings = {"/old/path/image.png": "/new/path/image.png"}

        result = linker.update_image_links(markdown, mappings)
        assert "/new/path/image.png" in result
        assert "/old/path/image.png" not in result

    def test_update_image_links_multiple(self):
        """Test updating multiple image links."""
        linker = Linker()
        markdown = "![Img1](/path1/img.png) and ![Img2](/path2/img.png)"
        mappings = {
            "/path1/img.png": "/new1/img.png",
            "/path2/img.png": "/new2/img.png",
        }

        result = linker.update_image_links(markdown, mappings)
        assert "/new1/img.png" in result
        assert "/new2/img.png" in result
        assert "/path1/img.png" not in result
        assert "/path2/img.png" not in result