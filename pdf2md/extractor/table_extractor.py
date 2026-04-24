"""Table extraction from PDF pages."""

from dataclasses import dataclass
from typing import List, Optional, Tuple

import pdfplumber

from pdf2md.extractor.pdfplumber_types import TYPE_PAGE, TYPE_TABLE
from pdf2md.utils.logger import get_logger

logger = get_logger()


@dataclass
class TableCell:
    """Represents a single cell in a table."""

    text: str
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1

    def is_empty(self) -> bool:
        """Check if cell is empty."""
        return not self.text or not self.text.strip()

    def __str__(self) -> str:
        """Get cell text."""
        return self.text.strip()


@dataclass
class Table:
    """Represents a complete table."""

    cells: List[TableCell]
    num_rows: int
    num_cols: int

    def get_cell(self, row: int, col: int) -> Optional[TableCell]:
        """Get a cell by position.

        Args:
            row: Row index (0-indexed).
            col: Column index (0-indexed).

        Returns:
            TableCell or None if not found.
        """
        for cell in self.cells:
            if cell.row == row and cell.col == col:
                return cell
        return None

    def get_row(self, row: int) -> List[TableCell]:
        """Get all cells in a row.

        Args:
            row: Row index (0-indexed).

        Returns:
            List of cells in the row.
        """
        return [cell for cell in self.cells if cell.row == row]

    def get_col(self, col: int) -> List[TableCell]:
        """Get all cells in a column.

        Args:
            col: Column index (0-indexed).

        Returns:
            List of cells in the column.
        """
        return [cell for cell in self.cells if cell.col == col]

    def is_empty(self) -> bool:
        """Check if table has any content."""
        if not self.cells:
            return True

        return all(cell.is_empty() for cell in self.cells)

    def get_header_cells(self) -> List[TableCell]:
        """Get header cells (first row).

        Returns:
            List of header cells.
        """
        return self.get_row(0)

    def has_header(self) -> bool:
        """Check if table has a header."""
        return self.num_rows > 0 and any(not cell.is_empty() for cell in self.get_row(0))

    def get_dimensions(self) -> Tuple[int, int]:
        """Get table dimensions.

        Returns:
            Tuple of (num_rows, num_cols).
        """
        return (self.num_rows, self.num_cols)

    def to_markdown(self) -> str:
        """Convert table to Markdown format.

        Returns:
            Markdown formatted table string.
        """
        if not self.cells:
            return ""

        # Build row by row
        lines = []

        for row_idx in range(self.num_rows):
            row_cells = self.get_row(row_idx)
            row_values = []
            col_counts = {}

            # Fill cells considering spans
            for col_idx in range(self.num_cols):
                cell = self.get_cell(row_idx, col_idx)

                if cell:
                    row_values.append(str(cell))
                    # Handle colspan
                    if cell.colspan > 1:
                        col_counts[col_idx] = cell.colspan - 1
                elif col_idx in col_counts and col_counts[col_idx] > 0:
                    # This cell is part of a colspan
                    row_values.append("")
                    col_counts[col_idx] -= 1
                else:
                    row_values.append("")

            # Create separator row after first row
            if row_idx == 0:
                separator = ["---" for _ in range(self.num_cols)]
                lines.append("| " + " | ".join(row_values) + " |")
                lines.append("| " + " | ".join(separator) + " |")
            else:
                lines.append("| " + " | ".join(row_values) + " |")

        return "\n".join(lines)


class TableExtractor:
    """Extracts tables from PDF pages."""

    def __init__(self, tolerance: int = 5) -> None:
        """Initialize the table extractor.

        Args:
            tolerance: Tolerance for table detection.
        """
        self.tolerance = tolerance

    def extract(self, page: TYPE_PAGE) -> List[Table]:
        """Extract tables from a PDF page.

        Args:
            page: pdfplumber Page object.

        Returns:
            List of Table objects.
        """
        tables = []

        if not hasattr(page, "find_tables"):
            logger.debug("Table extraction not available")
            return tables

        try:
            pdfplumber_tables = page.find_tables()

            if not pdfplumber_tables:
                logger.debug(f"No tables found on page")
                return tables

            logger.debug(f"Found {len(pdfplumber_tables)} table(s) on page")

            for idx, pdfplumber_table in enumerate(pdfplumber_tables):
                try:
                    table = self._convert_pdfplumber_table(pdfplumber_table)
                    if table:
                        tables.append(table)
                        logger.debug(
                            f"Extracted table {idx + 1}: {table.num_rows}x{table.num_cols}"
                        )
                except Exception as e:
                    logger.error(f"Error extracting table {idx + 1}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error finding tables: {e}")

        return tables

    def _convert_pdfplumber_table(
        self, pdfplumber_table: pdfplumber.table.Table
    ) -> Optional[Table]:
        """Convert pdfplumber Table to our Table format.

        Args:
            pdfplumber_table: pdfplumber Table object.

        Returns:
            Table object, or None if conversion failed.
        """
        try:
            table_data = pdfplumber_table.extract()

            if not table_data:
                return None

            num_rows = len(table_data)
            num_cols = len(table_data[0]) if table_data else 0

            if num_rows == 0 or num_cols == 0:
                return None

            cells = []

            for row_idx, row in enumerate(table_data):
                for col_idx, cell_text in enumerate(row):
                    cell = TableCell(
                        text=str(cell_text) if cell_text else "",
                        row=row_idx,
                        col=col_idx,
                    )
                    cells.append(cell)

            return Table(cells=cells, num_rows=num_rows, num_cols=num_cols)

        except Exception as e:
            logger.error(f"Error converting table: {e}")
            return None

    def has_tables(self, page: TYPE_PAGE) -> bool:
        """Check if page contains any tables.

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

    def get_table_count(self, page: TYPE_PAGE) -> int:
        """Get number of tables on a page.

        Args:
            page: pdfplumber Page object.

        Returns:
            Number of tables found.
        """
        if not hasattr(page, "find_tables"):
            return 0

        try:
            tables = page.find_tables()
            return len(tables)
        except Exception:
            return 0

    def extract_as_text(
        self, page: TYPE_TABLE, separator: str = " | "
    ) -> str:
        """Extract table as plain text.

        Args:
            page: pdfplumber Table object.
            separator: Column separator.

        Returns:
            Plain text representation of table.
        """
        try:
            table_data = page.extract()

            if not table_data:
                return ""

            lines = []
            for row in table_data:
                line = separator.join(str(cell) if cell else "" for cell in row)
                lines.append(line)

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Error extracting table as text: {e}")
            return ""