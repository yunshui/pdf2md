"""Table formatter for Markdown conversion."""

from typing import List, Optional

from pdf2md.extractor import Table, TableCell


class TableFormatter:
    """Formats tables as Markdown."""

    def __init__(self, max_column_width: int = 100) -> None:
        """Initialize the table formatter.

        Args:
            max_column_width: Maximum width for table columns.
        """
        self.max_column_width = max_column_width

    def format_table(self, table: Table) -> str:
        """Format a table as Markdown.

        Args:
            table: Table object.

        Returns:
            Markdown formatted table string.
        """
        if not table.cells:
            return ""

        lines = []

        # Process each row
        for row_idx in range(table.num_rows):
            row_values = []

            # Get cells for this row, handling spans
            for col_idx in range(table.num_cols):
                cell = table.get_cell(row_idx, col_idx)

                if cell:
                    text = self._format_cell_text(cell.text)
                    row_values.append(text)
                else:
                    # Empty cell or spanned cell placeholder
                    row_values.append("")

            # Create separator after first row
            if row_idx == 0:
                lines.append("| " + " | ".join(row_values) + " |")
                lines.append("| " + " | ".join(["---" for _ in range(table.num_cols)]) + " |")
            else:
                lines.append("| " + " | ".join(row_values) + " |")

        return "\n".join(lines)

    def format_table_list(self, tables: List[Table]) -> str:
        """Format multiple tables as Markdown.

        Args:
            tables: List of Table objects.

        Returns:
            Combined Markdown string.
        """
        formatted_tables = []

        for idx, table in enumerate(tables, start=1):
            formatted = self.format_table(table)
            if formatted:
                formatted_tables.append(f"### Table {idx}\n\n{formatted}\n")

        return "\n".join(formatted_tables)

    def _format_cell_text(self, text: str) -> str:
        """Format cell text for Markdown.

        Args:
            text: Cell text.

        Returns:
            Formatted text.
        """
        if not text:
            return ""

        # Escape pipe characters (they have special meaning in tables)
        text = text.replace("|", "\\|")

        # Truncate if too long
        if len(text) > self.max_column_width:
            text = text[: self.max_column_width - 3] + "..."

        return text

    def calculate_column_widths(self, table: Table) -> List[int]:
        """Calculate optimal column widths for a table.

        Args:
            table: Table object.

        Returns:
            List of column widths in characters.
        """
        if not table.cells:
            return []

        widths = [0] * table.num_cols

        for row_idx in range(table.num_rows):
            for col_idx in range(table.num_cols):
                cell = table.get_cell(row_idx, col_idx)
                if cell:
                    text_width = len(cell.text)
                    widths[col_idx] = max(widths[col_idx], text_width)

        return widths

    def format_with_alignment(
        self,
        table: Table,
        alignments: Optional[List[str]] = None,
    ) -> str:
        """Format table with column alignments.

        Args:
            table: Table object.
            alignments: List of alignments ("left", "center", "right"). None for default left.

        Returns:
            Markdown formatted table string.
        """
        if not table.cells:
            return ""

        if alignments is None:
            alignments = ["left"] * table.num_cols

        lines = []

        for row_idx in range(table.num_rows):
            row_values = []

            for col_idx in range(table.num_cols):
                cell = table.get_cell(row_idx, col_idx)
                text = self._format_cell_text(cell.text) if cell else ""
                row_values.append(text)

            if row_idx == 0:
                lines.append("| " + " | ".join(row_values) + " |")

                # Create separator with alignment
                sep_parts = []
                for idx, align in enumerate(alignments):
                    if align == "center":
                        sep_parts.append(":---:")
                    elif align == "right":
                        sep_parts.append("---:")
                    else:  # left
                        sep_parts.append("---")
                lines.append("| " + " | ".join(sep_parts) + " |")
            else:
                lines.append("| " + " | ".join(row_values) + " |")

        return "\n".join(lines)