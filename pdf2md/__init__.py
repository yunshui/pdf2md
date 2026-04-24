"""
PDF to Markdown Converter

A Python-based tool for converting PDF files to Markdown format with
multilingual OCR support (Chinese/English), high-fidelity formatting
preservation, and key summary extraction.

Example:
    >>> from pdf2md.core import Pipeline
    >>> pipeline = Pipeline()
    >>> result = pipeline.process_file("/path/to/document.pdf")
"""

__version__ = "0.1.1"
__author__ = "pdf2md Team"
__license__ = "MIT"
__email__ = "noreply@example.com"

# Export main classes for convenience
from pdf2md.core import Pipeline, ProcessingResult as ProcessResult
from pdf2md.utils import FileManager, ProgressTracker, get_logger

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "Pipeline",
    "ProcessResult",
    "FileManager",
    "ProgressTracker",
    "get_logger",
]