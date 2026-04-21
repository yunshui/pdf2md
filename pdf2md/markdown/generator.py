"""Markdown generation from processed page data."""

from pathlib import Path
from typing import List, Optional

from pdf2md.core.page_processor import PageData
from pdf2md.extractor import Table
from pdf2md.markdown.linker import Linker
from pdf2md.markdown.table_formatter import TableFormatter
from pdf2md.utils.logger import get_logger

logger = get_logger()


class MarkdownGenerator:
    """Generates Markdown output from processed PDF data."""

    def __init__(
        self,
        base_output_dir: Optional[Path] = None,
        include_images: bool = True,
        include_tables: bool = True,
        include_ocr_text: bool = True,
    ) -> None:
        """Initialize the Markdown generator.

        Args:
            base_output_dir: Base output directory.
            include_images: Whether to include images.
            include_tables: Whether to include tables.
            include_ocr_text: Whether to include OCR-extracted text.
        """
        self.base_output_dir = base_output_dir or Path.cwd()
        self.include_images = include_images
        self.include_tables = include_tables
        self.include_ocr_text = include_ocr_text

        # Initialize helpers
        self.linker = Linker(base_output_dir)
        self.table_formatter = TableFormatter()

    def generate_main_file(
        self,
        pages_data: List[PageData],
        source_file: str,
        output_dir: Path,
        document_summary: Optional["Summary"] = None,
    ) -> str:
        """Generate the main Markdown file.

        Args:
            pages_data: List of processed page data.
            source_file: Source PDF file path.
            output_dir: Output directory.
            document_summary: Optional document summary.

        Returns:
            Path to generated file.
        """
        logger.info(f"Generating main Markdown file...")

        output_path = output_dir / f"{Path(source_file).stem}.md"

        lines = []

        # Header
        lines.extend(self._generate_header(source_file))

        # Table of contents
        lines.extend(self._generate_toc(pages_data, document_summary))

        # Summary
        lines.extend(self._generate_summary(pages_data, document_summary))

        # Content placeholder (full content in docs/)
        lines.append("\n## Content\n")
        lines.append("*Full content available in the docs/ directory.*\n")

        # Edge text
        lines.extend(self._generate_edge_text_section(pages_data))

        # Footer
        lines.extend(self._generate_footer(source_file))

        # Write file
        content = "\n".join(lines)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Generated main file: {output_path}")

        return str(output_path)

    def generate_detail_files(
        self,
        pages_data: List[PageData],
        output_dir: Path,
        chapter_boundaries: Optional[List] = None,
    ) -> List[str]:
        """Generate detailed content files.

        Args:
            pages_data: List of processed page data.
            output_dir: Output directory.
            chapter_boundaries: Optional chapter boundaries.

        Returns:
            List of generated file paths.
        """
        logger.info("Generating detail files...")

        docs_dir = output_dir / "docs"
        docs_dir.mkdir(exist_ok=True)

        generated_files = []

        if not chapter_boundaries:
            # Generate single file with all content
            file_path = docs_dir / "complete_content.md"
            content = self._generate_complete_content(pages_data)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            generated_files.append(str(file_path))
        else:
            # Generate one file per chapter
            for boundary in chapter_boundaries:
                chapter_pages = [
                    p
                    for p in pages_data
                    if p.page_number == boundary.page_number
                ]

                if chapter_pages:
                    file_path = docs_dir / f"chapter_{boundary.chapter_number}.md"
                    content = self._generate_chapter_content(chapter_pages, boundary)

                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)

                    generated_files.append(str(file_path))

        logger.info(f"Generated {len(generated_files)} detail file(s)")

        return generated_files

    def _generate_header(self, source_file: str) -> List[str]:
        """Generate document header.

        Args:
            source_file: Source file path.

        Returns:
            List of header lines.
        """
        title = Path(source_file).stem
        title = title.replace("_", " ").replace("-", " ").title()

        return [
            f"# {title}\n",
            f"*Generated from: `{source_file}`*\n",
        ]

    def _generate_toc(self, pages_data: List[PageData], document_summary: Optional["Summary"] = None) -> List[str]:
        """Generate table of contents.

        Args:
            pages_data: List of processed page data.
            document_summary: Optional document summary.

        Returns:
            List of TOC lines.
        """
        lines = ["## Table of Contents\n"]

        if document_summary and document_summary.table_of_contents:
            # Use extracted TOC
            for item in document_summary.table_of_contents:
                level_prefix = "#" * item["level"]
                lines.append(f"{level_prefix} {item['title']} (page {item['page']})")
            lines.append("")
        else:
            # Fallback to simple TOC
            lines.append("- [Introduction](./docs/complete_content.md)\n")
            lines.append("- [Summary](#summary)\n")
            lines.append("- [Images](#images)\n")
            lines.append("- [Edge Text](#edge-text)\n")

        return lines

    def _generate_summary(self, pages_data: List[PageData], document_summary: Optional["Summary"] = None) -> List[str]:
        """Generate summary section.

        Args:
            pages_data: List of processed page data.
            document_summary: Optional document summary.

        Returns:
            List of summary lines.
        """
        lines = ["\n## Summary\n"]

        if document_summary:
            # Use extracted summary
            lines.append(f"**Title**: {document_summary.title}\n")
            lines.append(f"**Page Count**: {document_summary.page_count}\n")
            lines.append(f"**Word Count**: {document_summary.word_count}\n")

            if document_summary.key_points:
                lines.append("\n### Key Points\n")
                for point in document_summary.key_points:
                    lines.append(f"- {point}")
                lines.append("")

            if document_summary.headings:
                lines.append("\n### Headings\n")
                for heading in document_summary.headings:
                    lines.append(f"- {heading}")
                lines.append("")

            if document_summary.footnotes:
                lines.append("\n### Footnotes\n")
                for idx, note in enumerate(document_summary.footnotes, start=1):
                    lines.append(f"{idx}. {note}")
                lines.append("")

            if document_summary.annotations:
                lines.append("\n### Annotations\n")
                for annotation in document_summary.annotations:
                    lines.append(f"- {annotation}")
                lines.append("")
        else:
            # Fallback to statistics
            # Statistics
            total_pages = len(pages_data)
            total_words = sum(p.text_statistics.get("word_count", 0) for p in pages_data)
            total_images = sum(len(p.images) for p in pages_data)
            total_tables = sum(len(p.tables) for p in pages_data)

            lines.extend(
                [
                    "- **Total Pages**: " + str(total_pages),
                    "- **Total Words**: " + str(total_words),
                    "- **Images**: " + str(total_images),
                    "- **Tables**: " + str(total_tables),
                    "",
                ]
            )

            # Page-by-page summary table
            lines.append("| Page | Words | Images | Tables | OCR Used |")
            lines.append("|------|-------|--------|--------|----------|")

            for page_data in pages_data:
                ocr_used = "Yes" if (page_data.ocr_result and page_data.ocr_result.text) else "No"
                lines.append(
                    f"| {page_data.page_number} | "
                    f"{page_data.text_statistics.get('word_count', 0)} | "
                    f"{len(page_data.images)} | "
                    f"{len(page_data.tables)} | "
                    f"{ocr_used} |"
                )

        return lines

    def _generate_complete_content(self, pages_data: List[PageData]) -> str:
        """Generate complete content from all pages.

        Args:
            pages_data: List of processed page data.

        Returns:
            Complete content string.
        """
        lines = []

        for page_data in pages_data:
            # Page header
            lines.append(f"\n## Page {page_data.page_number}\n")

            # Body text (excluding edge text)
            if page_data.body_text:
                lines.append(page_data.body_text)
                lines.append("")

            # Images
            if self.include_images and page_data.images:
                for image_info in page_data.images:
                    link = self.linker.create_image_link(image_info, self.base_output_dir / "assets")
                    lines.append(link)
                    lines.append("")

            # Tables
            if self.include_tables and page_data.tables:
                table_lines = self.table_formatter.format_table_list(page_data.tables)
                if table_lines:
                    lines.append("\n### Tables\n")
                    lines.append(table_lines)
                    lines.append("")

            # OCR text
            if self.include_ocr_text and page_data.ocr_result and page_data.ocr_result.text:
                lines.append("\n### OCR Extracted Text\n")
                lines.append(page_data.ocr_result.text)
                lines.append("")

        return "\n".join(lines)

    def _generate_chapter_content(
        self, pages_data: List[PageData], boundary
    ) -> str:
        """Generate content for a single chapter.

        Args:
            pages_data: List of processed page data for this chapter.
            boundary: Chapter boundary information.

        Returns:
            Chapter content string.
        """
        lines = []

        # Chapter heading
        chapter_title = boundary.title or f"Chapter {boundary.chapter_number}"
        lines.append(f"# {chapter_title}\n")

        # Add page content
        for page_data in pages_data:
            lines.append(f"\n## Page {page_data.page_number}\n")
            lines.append(page_data.body_text if page_data.body_text else "*No text*")
            lines.append("")

        return "\n".join(lines)

    def _generate_edge_text_section(self, pages_data: List[PageData]) -> List[str]:
        """Generate edge text section.

        Args:
            pages_data: List of processed page data.

        Returns:
            List of edge text lines.
        """
        from pdf2md.deduplicator import EdgeTextHandler

        edge_handler = EdgeTextHandler()
        edge_texts = edge_handler.extract_edge_text(pages_data)

        if not edge_texts:
            return []

        lines = ["\n## Edge Text\n"]

        edge_markdown = edge_handler.format_edge_text(edge_texts, format="markdown")

        if edge_markdown:
            lines.append(edge_markdown)

        return lines

    def _generate_footer(self, source_file: str) -> List[str]:
        """Generate document footer.

        Args:
            source_file: Source file path.

        Returns:
            List of footer lines.
        """
        return [
            "\n---\n",
            "*This document was generated by PDF to Markdown Converter.*",
        ]

    def generate_single_file(
        self,
        pages_data: List[PageData],
        source_file: str,
        output_dir: Path,
        document_summary: Optional["Summary"] = None,
    ) -> str:
        """Generate a single Markdown file (without separate docs/).

        Args:
            pages_data: List of processed page data.
            source_file: Source file path.
            output_dir: Output directory.
            document_summary: Optional document summary.

        Returns:
            Path to generated file.
        """
        logger.info(f"Generating single Markdown file...")

        output_path = output_dir / f"{Path(source_file).stem}.md"

        lines = []

        # Header
        lines.extend(self._generate_header(source_file))

        # Summary
        lines.extend(self._generate_summary(pages_data, document_summary))

        # Complete content
        complete_content = self._generate_complete_content(pages_data)
        lines.append("\n## Content\n")
        lines.append(complete_content)

        # Edge text
        lines.extend(self._generate_edge_text_section(pages_data))

        # Footer
        lines.extend(self._generate_footer(source_file))

        # Write file
        content = "\n".join(lines)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Generated single file: {output_path}")

        return str(output_path)

    def determine_output_format(
        self,
        pages_data: List[PageData],
    ) -> str:
        """Determine whether to use single-file or multi-file output.

        Args:
            pages_data: List of processed page data.

        Returns:
            "single" or "multi".
        """
        # Check if document has images
        has_images = any(p.images for p in pages_data)

        if has_images:
            return "multi"  # Always use multi-file format for images

        # Check page count
        page_count = len(pages_data)
        if page_count < 10:
            return "single"

        return "multi"