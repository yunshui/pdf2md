"""Summary extraction from PDF content."""

from dataclasses import dataclass
from typing import Dict, List, Optional

from pdf2md.core.page_processor import PageData
from pdf2md.summary.rule_based import RuleBasedExtractor
from pdf2md.utils.logger import get_logger

logger = get_logger()


@dataclass
class Summary:
    """Represents a document summary."""

    title: str
    headings: List[str]
    key_points: List[str]
    page_count: int
    word_count: int
    table_of_contents: List[dict]
    footnotes: List[str]
    annotations: List[str]

    def to_markdown(self) -> str:
        """Convert summary to Markdown format.

        Returns:
            Markdown formatted summary.
        """
        lines = []

        lines.append(f"# {self.title}\n")
        lines.append(f"**Page Count**: {self.page_count}\n")
        lines.append(f"**Word Count**: {self.word_count}\n")

        if self.headings:
            lines.append("## Headings\n")
            for heading in self.headings:
                lines.append(f"- {heading}")
            lines.append("")

        if self.key_points:
            lines.append("## Key Points\n")
            for point in self.key_points:
                lines.append(f"- {point}")
            lines.append("")

        if self.table_of_contents:
            lines.append("## Table of Contents\n")
            for item in self.table_of_contents:
                lines.append(f"{item['level'] * '#'} {item['title']} (page {item['page']})")
            lines.append("")

        if self.footnotes:
            lines.append("## Footnotes\n")
            for idx, note in enumerate(self.footnotes, start=1):
                lines.append(f"{idx}. {note}")
            lines.append("")

        if self.annotations:
            lines.append("## Annotations\n")
            for annotation in self.annotations:
                lines.append(f"- {annotation}")
            lines.append("")

        return "\n".join(lines)


class SummaryExtractor:
    """Extracts summary information from PDF documents."""

    def __init__(self, enable_ai: bool = False) -> None:
        """Initialize the summary extractor.

        Args:
            enable_ai: Whether to enable AI-enhanced summarization.
        """
        self.enable_ai = enable_ai
        self.rule_extractor = RuleBasedExtractor()
        self.ai_assistant = None

        if self.enable_ai:
            try:
                self.ai_assistant = AIAssistant()
                logger.info("AI assistant initialized")
            except ImportError:
                logger.warning("AI dependencies not available, using rule-based only")
                self.enable_ai = False

    def extract_summary(
        self,
        pages_data: List[PageData],
        source_file: str,
        summary_type: str = "rule_based",
    ) -> Summary:
        """Extract a summary from processed pages.

        Args:
            pages_data: List of processed page data.
            source_file: Source file path.
            summary_type: Type of summary ("rule_based" or "ai").

        Returns:
            Summary object.
        """
        logger.info(f"Extracting summary ({summary_type})...")

        # Extract title
        title = self._extract_title(source_file, pages_data)

        # Extract rule-based summaries
        rule_summaries = self.rule_extractor.extract_summaries(pages_data)

        # Generate summary
        if summary_type == "ai" and self.ai_assistant:
            return self._generate_ai_summary(pages_data, title, rule_summaries)
        else:
            return self._generate_rule_summary(pages_data, title, rule_summaries)

    def _generate_rule_summary(
        self,
        pages_data: List[PageData],
        title: str,
        rule_summaries: List,
    ) -> Summary:
        """Generate a summary using rule-based extraction.

        Args:
            pages_data: List of processed page data.
            title: Document title.
            rule_summaries: Rule-based summary items.

        Returns:
            Summary object.
        """
        # Extract headings
        headings = self._extract_headings_from_pages(pages_data)

        # Extract key points (first sentence of each paragraph)
        key_points = self._extract_key_points(pages_data)

        # Generate table of contents
        toc = self._generate_toc(headings, pages_data)

        # Extract footnotes and annotations
        footnotes = [s.text for s in rule_summaries if s.item_type == "footnote"]
        annotations = [s.text for s in rule_summaries if s.item_type == "annotation"]

        # Get statistics
        page_count = len(pages_data)
        word_count = sum(p.text_statistics.get("word_count", 0) for p in pages_data)

        return Summary(
            title=title,
            headings=headings,
            key_points=key_points,
            page_count=page_count,
            word_count=word_count,
            table_of_contents=toc,
            footnotes=footnotes,
            annotations=annotations,
        )

    def _generate_ai_summary(
        self,
        pages_data: List[PageData],
        title: str,
        rule_summaries: List,
    ) -> Summary:
        """Generate a summary using AI assistance.

        Args:
            pages_data: List of processed page data.
            title: Document title.
            rule_summaries: Rule-based summary items as context.

        Returns:
            Summary object.
        """
        # Collect all text from pages
        all_text = "\n\n".join(p.get_all_text() for p in pages_data)

        # Get AI-generated summary
        ai_summary = self.ai_assistant.generate_summary(
            title, all_text, rule_summaries
        )

        return Summary(
            title=title,
            headings=ai_summary.get("headings", []),
            key_points=ai_summary.get("key_points", []),
            page_count=len(pages_data),
            word_count=sum(p.text_statistics.get("word_count", 0) for p in pages_data),
            table_of_contents=ai_summary.get("table_of_contents", []),
            footnotes=[],
            annotations=[],
        )

    def _extract_title(
        self, source_file: str, pages_data: List[PageData]
    ) -> str:
        """Extract document title from file or first page.

        Args:
            source_file: Source file path.
            pages_data: List of processed page data.

        Returns:
            Document title.
        """
        # Use filename as base title
        from pathlib import Path

        title = Path(source_file).stem
        title = title.replace("_", " ").replace("-", " ").title()

        # Try to get title from first heading
        if pages_data:
            headings = self.rule_extractor.extract_headings_by_level(
                pages_data, max_level=1
            )
            if headings[1]:  # Level 1 headings
                title = headings[1][0].text

        return title

    def _extract_headings_from_pages(
        self, pages_data: List[PageData]
    ) -> List[str]:
        """Extract all headings from pages.

        Args:
            pages_data: List of processed page data.

        Returns:
            List of heading strings.
        """
        headings = []

        for page_data in pages_data:
            page_headings = self.rule_extractor._extract_headings(page_data)
            headings.extend([h.text for h in page_headings])

        return headings

    def _extract_key_points(
        self, pages_data: List[PageData], max_points: int = 10
    ) -> List[str]:
        """Extract key points from document.

        Args:
            pages_data: List of processed page data.
            max_points: Maximum number of key points.

        Returns:
            List of key point strings.
        """
        key_points = []

        for page_data in pages_data:
            paragraphs = page_data.body_text.split("\n\n")

            for paragraph in paragraphs:
                # Get first sentence
                sentences = paragraph.split(". ")
                if sentences:
                    first_sentence = sentences[0].strip()
                    if first_sentence and len(first_sentence) > 20:
                        key_points.append(first_sentence + ".")

                        if len(key_points) >= max_points:
                            break

            if len(key_points) >= max_points:
                break

        return key_points[:max_points]

    def _generate_toc(
        self, headings: List[str], pages_data: List[PageData]
    ) -> List[dict]:
        """Generate table of contents.

        Args:
            headings: List of heading strings.
            pages_data: List of processed page data.

        Returns:
            List of TOC items.
        """
        toc = []

        # Get heading levels from rule extractor
        headings_by_level = self.rule_extractor.extract_headings_by_level(
            pages_data, max_level=3
        )

        for level, items in headings_by_level.items():
            for item in items:
                toc.append({
                    "level": level,
                    "title": item.text,
                    "page": item.page_number,
                })

        return toc

    def generate_toc(self, summaries: List) -> str:
        """Generate a table of contents from summaries.

        Args:
            summaries: List of SummaryItem objects.

        Returns:
            Markdown formatted TOC.
        """
        # Filter headings only
        headings = [s for s in summaries if s.item_type == "heading"]

        if not headings:
            return "*No headings found.*"

        lines = ["## Table of Contents\n"]

        for heading in headings:
            indent = "  " * (self._determine_heading_level(heading) - 1)
            lines.append(f"{indent}- [{heading.text}](#page-{heading.page_number})")

        return "\n".join(lines)

    def _determine_heading_level(self, summary) -> int:
        """Determine heading level from summary item.

        Args:
            summary: SummaryItem object.

        Returns:
            Heading level.
        """
        return self.rule_extractor._determine_heading_level(summary)

    def get_summary_statistics(self, summary: Summary) -> Dict:
        """Get statistics about a summary.

        Args:
            summary: Summary object.

        Returns:
            Statistics dictionary.
        """
        return {
            "heading_count": len(summary.headings),
            "key_point_count": len(summary.key_points),
            "footnote_count": len(summary.footnotes),
            "annotation_count": len(summary.annotations),
            "toc_entries": len(summary.table_of_contents),
            "avg_words_per_page": (
                summary.word_count / summary.page_count if summary.page_count > 0 else 0
            ),
        }


# Optional AI Assistant (placeholder)
class AIAssistant:
    """AI-assisted summary generation."""

    def __init__(self):
        """Initialize the AI assistant."""
        # This is a placeholder for AI integration
        raise NotImplementedError("AI assistant requires explicit configuration")

    def generate_summary(
        self, title: str, content: str, context: List
    ) -> Dict:
        """Generate summary using AI.

        Args:
            title: Document title.
            content: Document content.
            context: Rule-based summary context.

        Returns:
            Dictionary with summary components.
        """
        raise NotImplementedError("AI assistant requires explicit configuration")