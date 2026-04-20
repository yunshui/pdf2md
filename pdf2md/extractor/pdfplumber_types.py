"""Type compatibility fixes for pdfplumber."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # For type checking purposes, we'll use TYPE_PAGE
    try:
        from pdfplumber.pdfplumber import Page
        TYPE_PAGE = Page
    except (ImportError, AttributeError):
        # Fallback to Any
        from typing import Any
        TYPE_PAGE = Any

    # For type checking purposes, we'll use TYPE_TABLE
    try:
        from pdfplumber.table import Table
        TYPE_TABLE = Table
    except (ImportError, AttributeError):
        # Fallback to Any
        from typing import Any
        TYPE_TABLE = Any
else:
    TYPE_PAGE = object
    TYPE_TABLE = object

# Export for use in other modules
__all__ = ["TYPE_PAGE", "TYPE_TABLE"]