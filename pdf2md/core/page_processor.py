"""Page processor for individual PDF page processing."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pdfplumber

from pdf2md.core.resource_manager import get_resource_manager
from pdf2md.extractor import (
    ImageExtractor,
    ImageInfo,
    LayoutAnalyzer,
    LayoutInfo,
    PageText,
    TableExtractor,
    Table,
    TextExtractor,
)
from pdf2md.ocr import OCRResult, OCREngine
from pdf2md.utils.logger import get_logger

logger = get_logger()


@dataclass
class PageData:
    """Complete data extracted from a single page."""

    page_number: int
    text: PageText
    text_statistics: dict
    images: List[ImageInfo]
    tables: List[Table]
    layout: LayoutInfo
    ocr_result: Optional[OCRResult]
    raw_page: pdfplumber.Page

    def has_content(self) -> bool:
        """Check if page has any content.

        Returns:
            True if page has text, images, or tables.
        """
        return (
            bool(self.text.raw_text)
            or self.images
            or self.tables
            or (self.ocr_result and self.ocr_result.text)
        )

    def get_all_text(self) -> str:
        """Get all text from the page.

        Returns:
            Combined text from all sources.
        """
        texts = []

        # Extracted text
        if self.text.raw_text:
            texts.append(self.text.raw_text)

        # OCR text
        if self.ocr_result and self.ocr_result.text:
            texts.append(f"[OCR]\n{self.ocr_result.text}")

        return "\n\n".join(texts)


class PageProcessor:
    """Processes individual PDF pages."""

    def __init__(
        self,
        ocr_engine: Optional[OCREngine] = None,
        enable_ocr: bool = True,
        image_max_width: int = 1920,
        image_quality: int = 85,
    ) -> None:
        """Initialize the page processor.

        Args:
            ocr_engine: OCR engine to use. If None, will get from resource manager.
            enable_ocr: Whether to enable OCR.
            image_max_width: Maximum image width.
            image_quality: Image quality.
        """
        self.ocr_engine = ocr_engine
        self.enable_ocr = enable_ocr

        # Initialize extractors
        self.text_extractor = TextExtractor(preserve_formatting=True)
        self.image_extractor = ImageExtractor(
            max_width=image_max_width, quality=image_quality
        )
        self.table_extractor = TableExtractor()
        self.layout_analyzer = LayoutAnalyzer()

        # Get resource manager for lazy OCR engine initialization
        self.resource_manager = get_resource_manager()

    def process_page(
        self,
        page: pdfplumber.Page,
        page_number: int,
        output_dir: str,
    ) -> PageData:
        """Process a single PDF page.

        Args:
            page: pdfplumber Page object.
            page_number: Page number (1-indexed).
            output_dir: Output directory for extracted resources.

        Returns:
            PageData with all extracted information.
        """
        logger.info(f"Processing page {page_number}")

        try:
            # Extract text
            text = self.text_extractor.extract(page)
            text_stats = self.text_extractor.get_text_statistics(text)

            # Extract images
            images = self.image_extractor.extract(page, page_number, output_dir)

            # Extract tables
            tables = self.table_extractor.extract(page)

            # Analyze layout
            layout = self.layout_analyzer.analyze(page)

            # OCR if needed
            ocr_result = None
            if self.enable_ocr and self._needs_ocr(page, text, layout):
                ocr_result = self._perform_ocr(page, page_number)

            logger.debug(
                f"Page {page_number}: "
                f"{text_stats['word_count']} words, "
                f"{len(images)} images, "
                f"{len(tables)} tables"
            )

            return PageData(
                page_number=page_number,
                text=text,
                text_statistics=text_stats,
                images=images,
                tables=tables,
                layout=layout,
                ocr_result=ocr_result,
                raw_page=page,
            )

        except Exception as e:
            logger.error(f"Error processing page {page_number}: {e}")
            # Return minimal page data on error
            return PageData(
                page_number=page_number,
                text=PageText(elements=[], raw_text=""),
                text_statistics={},
                images=[],
                tables=[],
                layout=LayoutInfo(
                    width=page.width,
                    height=page.height,
                    header_region=None,
                    footer_region=None,
                    body_regions=[],
                    edge_regions=[],
                    sidebar_regions=[],
                    has_images=False,
                    has_tables=False,
                    text_density=0.0,
                ),
                ocr_result=None,
                raw_page=page,
            )

    def _needs_ocr(
        self,
        page: pdfplumber.Page,
        text: PageText,
        layout: LayoutInfo,
    ) -> bool:
        """Determine if OCR is needed for the page.

        Args:
            page: pdfplumber Page object.
            text: Extracted text.
            layout: Layout analysis.

        Returns:
            True if OCR should be performed.
        """
        if not self.enable_ocr:
            return False

        # Get OCR engine
        ocr_engine = self.ocr_engine or self.resource_manager.get_ocr_engine()

        # Get image area ratio
        image_area_ratio = 0.0
        if layout.has_images:
            from pdf2md.extractor.image_extractor import ImageExtractor

            img_extractor = ImageExtractor()
            image_area_ratio = img_extractor.get_image_area_ratio(page)

        # Use OCR engine's decision logic
        return ocr_engine.needs_ocr(
            page_text=text.raw_text,
            has_images=layout.has_images,
            image_area_ratio=image_area_ratio,
            typical_page_length=text.text_statistics.get("word_count", 0),
        )

    def _perform_ocr(self, page: pdfplumber.Page, page_number: int) -> Optional[OCRResult]:
        """Perform OCR on a page.

        Args:
            page: pdfplumber Page object.
            page_number: Page number.

        Returns:
            OCRResult or None if OCR failed.
        """
        try:
            # Get OCR engine
            ocr_engine = self.ocr_engine or self.resource_manager.get_ocr_engine()

            # Convert page to image
            from pdf2image import convert_from_path

            images = convert_from_path(
                page.pdf.stream,
                first_page=page_number,
                last_page=page_number,
                dpi=150,
            )

            if not images:
                logger.warning(f"Could not convert page {page_number} to image")
                return None

            # Perform OCR
            logger.info(f"Performing OCR on page {page_number}")
            result = ocr_engine.extract_text(images[0])

            if result.is_empty():
                logger.warning(f"OCR produced no text on page {page_number}")
            else:
                logger.info(
                    f"OCR extracted {len(result.text)} characters from page {page_number}"
                )

            return result

        except ImportError:
            logger.error(
                "pdf2image not installed. Install with: pip install pdf2image"
            )
            return None
        except Exception as e:
            logger.error(f"OCR failed on page {page_number}: {e}")
            return None

    def cleanup(self) -> None:
        """Clean up resources."""
        # Extractors don't need cleanup
        pass