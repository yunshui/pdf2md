"""PaddleOCR implementation of the OCR engine."""

from typing import List

import numpy as np
from PIL import Image

from pdf2md.ocr.base import OCREngine, OCRResult
from pdf2md.utils.logger import get_logger

logger = get_logger()


class PaddleOCREngine(OCREngine):
    """PaddleOCR-based text extraction engine.

    Supports Chinese (Simplified/Traditional) and English.
    """

    def __init__(
        self,
        use_angle_cls: bool = True,
        lang: str = "ch",
        min_chars: int = 100,
        min_ratio: float = 0.05,
        max_image_ratio: float = 0.80,
        show_log: bool = False,
    ) -> None:
        """Initialize the PaddleOCR engine.

        Args:
            use_angle_cls: Whether to use angle classification.
            lang: Language model to use ('ch' for Chinese, 'en' for English).
            min_chars: Minimum character count to trigger OCR.
            min_ratio: Minimum text ratio to trigger OCR.
            max_image_ratio: Maximum image ratio to trigger OCR.
            show_log: Whether to show PaddleOCR logs.
        """
        super().__init__(min_chars, min_ratio, max_image_ratio)

        self.use_angle_cls = use_angle_cls
        self.lang = lang
        self.show_log = show_log
        self._ocr_engine = None

    @property
    def ocr_engine(self):
        """Lazy load the PaddleOCR engine."""
        if self._ocr_engine is None:
            try:
                from paddleocr import PaddleOCR as PaddleOCRLib

                self._ocr_engine = PaddleOCRLib(
                    use_angle_cls=self.use_angle_cls,
                    lang=self.lang,
                    show_log=self.show_log,
                )
                logger.info("PaddleOCR engine initialized")
            except ImportError:
                logger.error(
                    "PaddleOCR not installed. Install with: pip install paddleocr"
                )
                raise ImportError(
                    "PaddleOCR is required. Install with: pip install paddleocr"
                )

        return self._ocr_engine

    def extract_text(self, image: Image.Image) -> OCRResult:
        """Extract text from an image using PaddleOCR.

        Args:
            image: PIL Image to process.

        Returns:
            OCRResult with extracted text and metadata.
        """
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image)

            # Convert PIL Image to numpy array
            image_array = np.array(processed_image)

            # Run OCR
            result = self.ocr_engine.ocr(image_array, cls=True)

            # Extract text from results
            text_parts = []
            boxes = []
            confidences = []

            if result and result[0]:
                for line in result[0]:
                    box, (text, confidence) = line
                    text_parts.append(text)
                    boxes.append(box)
                    confidences.append(confidence)

            full_text = "\n".join(text_parts)

            # Calculate average confidence
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            # Detect language
            detected_lang = self._detect_language(full_text)

            logger.debug(
                f"OCR extracted {len(full_text)} characters "
                f"with confidence {avg_confidence:.2f}"
            )

            return OCRResult(
                text=full_text,
                confidence=avg_confidence,
                language=detected_lang,
                boxes=boxes,
            )

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return OCRResult(text="", confidence=0.0, language="")

    def supported_languages(self) -> List[str]:
        """Get list of supported languages.

        Returns:
            List of language codes.
        """
        # PaddleOCR supports various languages based on the model
        return ["en", "zh", "zh-CN", "zh-TW", "japan", "korean"]

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results.

        Args:
            image: Input image.

        Returns:
            Preprocessed image.
        """
        # Convert to RGB if necessary
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Resize if too large (PaddleOCR has limits)
        max_dimension = 2000
        if max(image.size) > max_dimension:
            ratio = max_dimension / max(image.size)
            new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            logger.debug(f"Resized image to {new_size}")

        # Enhance contrast
        from PIL import ImageEnhance

        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)

        return image

    def _detect_language(self, text: str) -> str:
        """Detect the primary language of extracted text.

        Args:
            text: Extracted text.

        Returns:
            Language code.
        """
        if not text:
            return ""

        # Simple detection based on character types
        chinese_chars = sum(0x4E00 <= ord(c) <= 0x9FFF for c in text)
        english_chars = sum(c.isalpha() and ord(c) < 128 for c in text)
        total_chars = len(text)

        if total_chars == 0:
            return ""

        chinese_ratio = chinese_chars / total_chars
        english_ratio = english_chars / total_chars

        if chinese_ratio > 0.3:
            return "zh"
        elif english_ratio > 0.5:
            return "en"
        else:
            # Default to Chinese if ambiguous
            return "zh"