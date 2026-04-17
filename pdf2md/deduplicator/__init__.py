"""Deduplication modules for pdf2md."""

from pdf2md.deduplicator.chapter_detector import ChapterBoundary, ChapterDetector
from pdf2md.deduplicator.edge_text import EdgeText, EdgeTextHandler
from pdf2md.deduplicator.header_footer import HeaderFooterContent, HeaderFooterDeduplicator

__all__ = [
    # Chapter detection
    "ChapterDetector",
    "ChapterBoundary",
    # Header/footer deduplication
    "HeaderFooterDeduplicator",
    "HeaderFooterContent",
    # Edge text handling
    "EdgeTextHandler",
    "EdgeText",
]