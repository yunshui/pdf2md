"""OCR engine base class."""

from abc import ABC, abstractmethod
from typing import List, Optional

from PIL import Image

from pdf2md.utils.logger import get_logger

logger = get_logger()


class OCRResult:
    """Result of OCR processing."""

    def __init__(
        self,
        text: str,
        confidence: float = 0.0,
        language: str = "",
        boxes: Optional[List[List]] = None,
    ) -> None:
        """Initialize OCR result.

        Args:
            text: Extracted text.
            confidence: Confidence score (0.0 to 1.0).
            language: Detected language code.
            boxes: Bounding boxes for text regions.
        """
        self.text = text
        self.confidence = confidence
        self.language = language
        self.boxes = boxes or []

    def is_empty(self) -> bool:
        """Check if result is empty.

        Returns:
            True if text is empty or only whitespace.
        """
        return not self.text or not self.text.strip()


class OCREngine(ABC):
    """Abstract base class for OCR engines."""

    def __init__(
        self,
        min_chars: int = 100,
        min_ratio: float = 0.05,
        max_image_ratio: float = 0.80,
    ) -> None:
        """Initialize the OCR engine.

        Args:
            min_chars: Minimum character count to trigger OCR.
            min_ratio: Minimum text ratio to trigger OCR.
            max_image_ratio: Maximum image ratio to trigger OCR.
        """
        self.min_chars = min_chars
        self.min_ratio = min_ratio
        self.max_image_ratio = max_image_ratio

    @abstractmethod
    def extract_text(self, image: Image.Image) -> OCRResult:
        """Extract text from an image.

        Args:
            image: PIL Image to process.

        Returns:
            OCRResult with extracted text and metadata.
        """
        pass

    @abstractmethod
    def supported_languages(self) -> List[str]:
        """Get list of supported languages.

        Returns:
            List of language codes (e.g., ["en", "zh"]).
        """
        pass

    def needs_ocr(
        self,
        page_text: str,
        has_images: bool,
        image_area_ratio: float = 0.0,
        typical_page_length: int = 2000,
    ) -> bool:
        """Determine if OCR is needed for a page.

        Args:
            page_text: Text already extracted from the page.
            has_images: Whether the page contains images.
            image_area_ratio: Ratio of page area occupied by images.
            typical_page_length: Typical text length for a page.

        Returns:
            True if OCR should be performed.
        """
        # No text extracted
        if not page_text:
            logger.debug("No text extracted, OCR needed")
            return True

        text_length = len(page_text.strip())

        # Text below minimum character count
        if text_length < self.min_chars:
            logger.debug(
                f"Text length ({text_length}) below threshold ({self.min_chars}), "
                "OCR needed"
            )
            return True

        # Text ratio below threshold
        if typical_page_length > 0:
            text_ratio = text_length / typical_page_length
            if text_ratio < self.min_ratio:
                logger.debug(
                    f"Text ratio ({text_ratio:.2%}) below threshold "
                    f"({self.min_ratio:.2%}), OCR needed"
                )
                return True

        # High image content
        if has_images and image_area_ratio > self.max_image_ratio:
            logger.debug(
                f"Image ratio ({image_area_ratio:.2%}) above threshold "
                f"({self.max_image_ratio:.2%}), OCR needed"
            )
            return True

        logger.debug("Text extraction sufficient, OCR not needed")
        return False

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results.

        Args:
            image: Input image.

        Returns:
            Preprocessed image.
        """
        # Default implementation: return image as-is
        return image

    def _calculate_confidence(self, text: str) -> float:
        """Calculate confidence score based on text characteristics.

        Args:
            text: Extracted text.

        Returns:
            Confidence score (0.0 to 1.0).
        """
        if not text:
            return 0.0

        # Simple heuristics for confidence
        score = 0.5

        # Reward reasonable length
        if len(text) > 50:
            score += 0.2

        # Reward proper sentence structure
        sentences = text.count(". ") + text.count("！") + text.count("。")
        if sentences > 0:
            score += 0.2

        # Reward alphanumeric content
        alnum_ratio = sum(c.isalnum() for c in text) / len(text)
        score += alnum_ratio * 0.1

        return min(score, 1.0)