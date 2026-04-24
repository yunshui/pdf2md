"""Table formatter for Markdown conversion."""

from typing import List, Optional, Tuple

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

        # Detect column alignments from content
        alignments = self._detect_alignments(table)

        # Format with detected alignments
        return self.format_with_alignment(table, alignments)

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

        # Clean up text
        text = text.strip()

        # Handle multiline text
        text = " ".join(text.split())

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

    def _detect_alignments(self, table: Table) -> List[str]:
        """Detect column alignments based on cell content.

        Args:
            table: Table object.

        Returns:
            List of alignments ("left", "center", "right").
        """
        if not table.cells:
            return ["left"] * table.num_cols

        alignments = []

        for col_idx in range(table.num_cols):
            # Get cells for this column
            if hasattr(table, 'get_col'):
                col_cells = table.get_col(col_idx)
            else:
                # Fallback: manually filter cells by column
                col_cells = [cell for cell in table.cells if cell.col == col_idx]

            # Count alignment indicators
            left_count = 0
            center_count = 0
            right_count = 0
            empty_count = 0

            for cell in col_cells:
                if not cell:
                    empty_count += 1
                    continue

                # Check if cell has is_empty method (for testing compatibility)
                if hasattr(cell, 'is_empty'):
                    if cell.is_empty():
                        empty_count += 1
                        continue
                else:
                    # Fallback: check text directly
                    if not cell.text or not cell.text.strip():
                        empty_count += 1
                        continue

                text = cell.text.strip()

                # Check for alignment patterns
                # Center: text is mostly short numbers or single characters
                if len(text) <= 5 and text.isdigit():
                    center_count += 1
                # Right: numbers (especially monetary values)
                elif any(c.isdigit() for c in text):
                    if any(c in text for c in ['.', ',', '%', '$', '€', '£', '¥']):
                        right_count += 1
                    else:
                        left_count += 1
                # Left: text content
                else:
                    left_count += 1

            # Determine alignment
            if center_count > 0 and center_count >= left_count and center_count >= right_count:
                alignments.append("center")
            elif right_count > left_count:
                alignments.append("right")
            else:
                alignments.append("left")

        return alignments

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

        # Build cell grid considering spans
        cell_grid = self._build_cell_grid(table)

        for row_idx in range(table.num_rows):
            row_values = []

            for col_idx in range(table.num_cols):
                cell_text = cell_grid[row_idx][col_idx]
                if cell_text:
                    # Format cell text
                    formatted_text = self._format_cell_text(cell_text)
                    row_values.append(formatted_text)
                else:
                    row_values.append("")

            if row_idx == 0:
                # Header row with separator
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
                # Data row
                lines.append("| " + " | ".join(row_values) + " |")

        return "\n".join(lines)

    def _build_cell_grid(self, table: Table) -> List[List[str]]:
        """Build a 2D grid of cell text, handling colspan and rowspan.

        Args:
            table: Table object.

        Returns:
            2D list of cell text (or empty strings for spanned cells).
        """
        grid = [["" for _ in range(table.num_cols)] for _ in range(table.num_rows)]

        # Handle rowspan/colspan
        span_map = {}  # Track which cells are covered by spans

        for cell in table.cells:
            text = self._format_cell_text(cell.text)

            # Place cell in grid, handling spans
            for row_offset in range(cell.rowspan):
                for col_offset in range(cell.colspan):
                    target_row = cell.row + row_offset
                    target_col = cell.col + col_offset

                    if target_row < table.num_rows and target_col < table.num_cols:
                        span_key = (target_row, target_col)

                        if row_offset == 0 and col_offset == 0:
                            # Primary cell position
                            grid[target_row][target_col] = text
                            span_map[span_key] = "primary"
                        else:
                            # Spanned position - mark but keep empty
                            span_map[span_key] = "spanned"

        return grid

    def format_as_html(self, table: Table, caption: Optional[str] = None) -> str:
        """Format table as HTML (for better formatting control).

        Args:
            table: Table object.
            caption: Optional table caption.

        Returns:
            HTML formatted table string.
        """
        if not table.cells:
            return ""

        alignments = self._detect_alignments(table)

        html_parts = ["<table>"]

        # Add caption if provided
        if caption:
            html_parts.append(f"<caption>{caption}</caption>")

        # Build table rows
        for row_idx in range(table.num_rows):
            html_parts.append("<tr>")

            for col_idx in range(table.num_cols):
                cell = table.get_cell(row_idx, col_idx)

                if cell:
                    # Determine cell type
                    tag = "th" if row_idx == 0 else "td"

                    # Get alignment
                    align = alignments[col_idx] if col_idx < len(alignments) else "left"

                    # Build cell attributes
                    attrs = [f'align="{align}"']

                    if cell.colspan > 1:
                        attrs.append(f'colspan="{cell.colspan}"')

                    if cell.rowspan > 1:
                        attrs.append(f'rowspan="{cell.rowspan}"')

                    attr_str = " " + " ".join(attrs)

                    # Format text
                    text = self._format_cell_text(cell.text)

                    html_parts.append(f"<{tag}{attr_str}>{text}</{tag}>")
                else:
                    # Empty cell (part of span)
                    tag = "th" if row_idx == 0 else "td"
                    html_parts.append(f"<{tag}></{tag}>")

            html_parts.append("</tr>")

        html_parts.append("</table>")

        return "\n".join(html_parts)