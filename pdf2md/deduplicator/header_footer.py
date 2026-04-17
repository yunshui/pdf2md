"""Header and footer deduplication across pages."""

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional

from pdf2md.core.page_processor import PageData
from pdf2md.extractor import TextRegion
from pdf2md.utils.logger import get_logger

logger = get_logger()


@dataclass
class HeaderFooterContent:
    """Represents header or footer content."""

    content: str
    page_numbers: List[int]
    frequency: int
    is_header: bool  # True for header, False for footer

    def is_candidate_for_deduplication(
        self, min_frequency: int = 2, min_pages_ratio: float = 0.3
    ) -> bool:
        """Check if content is a candidate for deduplication.

        Args:
            min_frequency: Minimum number of occurrences.
            min_pages_ratio: Minimum ratio of pages this appears on.

        Returns:
            True if content should be deduplicated.
        """
        return self.frequency >= min_frequency

    def __str__(self) -> str:
        """Get string representation."""
        type_str = "Header" if self.is_header else "Footer"
        return f"{type_str}: {self.content} ({self.frequency} pages)"


class HeaderFooterDeduplicator:
    """Detects and deduplicates repeated headers and footers across pages."""

    def __init__(
        self,
        min_frequency: int = 2,
        similarity_threshold: float = 0.9,
        ignore_page_numbers: bool = True,
    ) -> None:
        """Initialize the header/footer deduplicator.

        Args:
            min_frequency: Minimum frequency to consider for deduplication.
            similarity_threshold: Similarity threshold for content matching.
            ignore_page_numbers: Whether to ignore page numbers in content.
        """
        self.min_frequency = min_frequency
        self.similarity_threshold = similarity_threshold
        self.ignore_page_numbers = ignore_page_numbers

    def deduplicate(
        self,
        pages_data: List[PageData],
        chapter_boundaries: Optional[List] = None,
    ) -> Dict[int, Dict[str, str]]:
        """Deduplicate headers and footers across pages.

        Args:
            pages_data: List of processed page data.
            chapter_boundaries: Optional chapter boundaries for chapter-level dedup.

        Returns:
            Dictionary mapping page numbers to deduplicated header/footer content.
        """
        logger.info("Analyzing headers and footers for deduplication...")

        if not pages_data:
            return {}

        # Collect headers and footers from all pages
        headers_by_page: Dict[int, str] = {}
        footers_by_page: Dict[int, str] = {}

        for page_data in pages_data:
            header_text = page_data.layout.get_header_text().strip()
            footer_text = page_data.layout.get_footer_text().strip()

            if header_text:
                headers_by_page[page_data.page_number] = header_text
            if footer_text:
                footers_by_page[page_data.page_number] = footer_text

        # Group similar content
        header_groups = self._group_similar_content(headers_by_page)
        footer_groups = self._group_similar_content(footers_by_page)

        # Find candidates for deduplication
        header_candidates = self._find_candidates(header_groups)
        footer_candidates = self._find_candidates(footer_groups)

        # Apply chapter-level dedup if chapter boundaries provided
        if chapter_boundaries:
            header_candidates = self._filter_by_chapters(
                header_candidates, chapter_boundaries
            )
            footer_candidates = self._filter_by_chapters(
                footer_candidates, chapter_boundaries
            )

        # Build result dictionary
        result: Dict[int, Dict[str, str]] = {}

        for page_num in range(1, len(pages_data) + 1):
            result[page_num] = {"header": "", "footer": ""}

        # Assign deduplicated headers to chapter start pages only
        for header in header_candidates:
            if header.page_numbers:
                # Assign to first page in chapter
                result[header.page_numbers[0]]["header"] = header.content

        # Assign deduplicated footers to chapter start pages only
        for footer in footer_candidates:
            if footer.page_numbers:
                # Assign to first page in chapter
                result[footer.page_numbers[0]]["footer"] = footer.content

        logger.info(
            f"Deduplication complete: "
            f"{len(header_candidates)} headers, {len(footer_candidates)} footers"
        )

        return result

    def _group_similar_content(
        self, content_by_page: Dict[int, str]
    ) -> List[HeaderFooterContent]:
        """Group similar header/footer content.

        Args:
            content_by_page: Dictionary mapping page numbers to content.

        Returns:
            List of grouped content with page numbers.
        """
        if not content_by_page:
            return []

        groups = []

        for page_num, content in content_by_page.items():
            # Normalize content
            normalized = self._normalize_content(content)

            # Try to match existing group
            matched = False
            for group in groups:
                if self._is_similar(normalized, group.content):
                    group.page_numbers.append(page_num)
                    group.frequency += 1
                    matched = True
                    break

            # Create new group if no match
            if not matched:
                groups.append(
                    HeaderFooterContent(
                        content=content,
                        page_numbers=[page_num],
                        frequency=1,
                        is_header=True,  # Will be set by caller
                    )
                )

        return groups

    def _find_candidates(
        self, groups: List[HeaderFooterContent]
    ) -> List[HeaderFooterContent]:
        """Find candidates for deduplication.

        Args:
            groups: List of content groups.

        Returns:
            List of candidates.
        """
        return [g for g in groups if g.is_candidate_for_deduplication(self.min_frequency)]

    def _filter_by_chapters(
        self,
        candidates: List[HeaderFooterContent],
        chapter_boundaries: List,
    ) -> List[HeaderFooterContent]:
        """Filter candidates by chapter boundaries.

        Only keep candidates that span entire chapters or appear
        consistently within chapters.

        Args:
            candidates: List of content candidates.
            chapter_boundaries: Chapter boundary information.

        Returns:
            Filtered list of candidates.
        """
        if not chapter_boundaries:
            return candidates

        filtered = []

        for candidate in candidates:
            # Check if content appears in a consistent pattern across chapters
            if self._is_chapter_consistent(candidate, chapter_boundaries):
                filtered.append(candidate)

        return filtered

    def _is_chapter_consistent(
        self, candidate: HeaderFooterContent, chapter_boundaries: List
    ) -> bool:
        """Check if header/footer is consistent within chapters.

        Args:
            candidate: Header/footer content.
            chapter_boundaries: Chapter boundary information.

        Returns:
            True if content is chapter-consistent.
        """
        # This is a simplified check
        # A full implementation would:
        # 1. Group pages by chapter
        # 2. Check if content appears in all pages of a chapter
        # 3. Verify consistency across chapters

        # For now, just check if frequency is reasonably high
        return candidate.frequency >= self.min_frequency

    def _normalize_content(self, content: str) -> str:
        """Normalize content for comparison.

        Args:
            content: Content to normalize.

        Returns:
            Normalized content.
        """
        # Remove extra whitespace
        normalized = " ".join(content.split())

        # Remove page numbers if configured
        if self.ignore_page_numbers:
            normalized = self._remove_page_numbers(normalized)

        return normalized

    def _remove_page_numbers(self, content: str) -> str:
        """Remove page numbers from content.

        Args:
            content: Content to process.

        Returns:
            Content with page numbers removed.
        """
        # Remove common page number patterns
        # This is a basic implementation
        import re

        # Remove "Page X" or similar
        content = re.sub(r"page\s*\d+", "", content, flags=re.IGNORECASE)

        # Remove standalone numbers at end
        content = re.sub(r"\s*\d+\s*$", "", content)

        return content.strip()

    def _is_similar(self, content1: str, content2: str) -> bool:
        """Check if two content strings are similar.

        Args:
            content1: First content string.
            content2: Second content string.

        Returns:
            True if content is similar above threshold.
        """
        if not content1 or not content2:
            return content1 == content2

        # Simple string comparison
        if content1 == content2:
            return True

        # Calculate similarity ratio
        from difflib import SequenceMatcher

        similarity = SequenceMatcher(None, content1, content2).ratio()

        return similarity >= self.similarity_threshold

    def get_unique_headers(self, pages_data: List[PageData]) -> List[str]:
        """Get list of unique headers across all pages.

        Args:
            pages_data: List of processed page data.

        Returns:
            List of unique header texts.
        """
        headers = set()
        for page_data in pages_data:
            header = page_data.layout.get_header_text().strip()
            if header:
                normalized = self._normalize_content(header)
                headers.add(normalized)
        return list(headers)

    def get_unique_footers(self, pages_data: List[PageData]) -> List[str]:
        """Get list of unique footers across all pages.

        Args:
            pages_data: List of processed page data.

        Returns:
            List of unique footer texts.
        """
        footers = set()
        for page_data in pages_data:
            footer = page_data.layout.get_footer_text().strip()
            if footer:
                normalized = self._normalize_content(footer)
                footers.add(normalized)
        return list(footers)