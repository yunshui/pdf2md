"""Unit tests for OCR module."""

import pytest
from PIL import Image

from pdf2md.ocr.base import OCRResult, OCREngine


class MockOCREngine(OCREngine):
    """Mock OCR engine for testing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mock_extracted_text = "Sample extracted text"

    def extract_text(self, image: Image.Image) -> OCRResult:
        """Mock text extraction."""
        return OCRResult(text=self.mock_extracted_text, confidence=0.85)

    def supported_languages(self) -> list:
        """Mock supported languages."""
        return ["en", "zh"]


class TestOCRResult:
    """Test cases for OCRResult class."""

    def test_init(self):
        """Test OCRResult initialization."""
        result = OCRResult(text="Sample text", confidence=0.8, language="en")
        assert result.text == "Sample text"
        assert result.confidence == 0.8
        assert result.language == "en"
        assert result.boxes == []

    def test_init_with_boxes(self):
        """Test OCRResult initialization with boxes."""
        boxes = [[0, 0, 100, 50], [0, 60, 100, 110]]
        result = OCRResult(text="Text", boxes=boxes)
        assert result.boxes == boxes

    def test_is_empty_with_text(self):
        """Test is_empty returns False for non-empty text."""
        result = OCRResult(text="Some text")
        assert not result.is_empty()

    def test_is_empty_empty_string(self):
        """Test is_empty returns True for empty string."""
        result = OCRResult(text="")
        assert result.is_empty()

    def test_is_empty_whitespace(self):
        """Test is_empty returns True for whitespace."""
        result = OCRResult(text="   \n\t  ")
        assert result.is_empty()


class TestOCREngine:
    """Test cases for OCREngine base class."""

    def test_init_default_params(self):
        """Test OCREngine initialization with default parameters."""
        engine = MockOCREngine()
        assert engine.min_chars == 100
        assert engine.min_ratio == 0.05
        assert engine.max_image_ratio == 0.80

    def test_init_custom_params(self):
        """Test OCREngine initialization with custom parameters."""
        engine = MockOCREngine(
            min_chars=50, min_ratio=0.1, max_image_ratio=0.6
        )
        assert engine.min_chars == 50
        assert engine.min_ratio == 0.1
        assert engine.max_image_ratio == 0.6

    def test_needs_ocr_no_text(self):
        """Test needs_ocr returns True when no text extracted."""
        engine = MockOCREngine()
        assert engine.needs_ocr("", has_images=False)

    def test_needs_ocr_below_min_chars(self):
        """Test needs_ocr returns True when text below minimum chars."""
        engine = MockOCREngine(min_chars=100)
        short_text = "Short text"
        assert len(short_text) < engine.min_chars
        assert engine.needs_ocr(short_text, has_images=False)

    def test_needs_ocr_below_min_ratio(self):
        """Test needs_ocr returns True when text ratio below threshold."""
        engine = MockOCREngine(min_ratio=0.05)
        short_text = "Short text"
        # Text ratio = 10/2000 = 0.005, which is < 0.05
        assert engine.needs_ocr(short_text, has_images=False, typical_page_length=2000)

    def test_needs_ocr_high_image_ratio(self):
        """Test needs_ocr returns True with high image ratio."""
        engine = MockOCREngine(max_image_ratio=0.8)
        long_text = "This is a long text that exceeds minimum characters."
        assert engine.needs_ocr(long_text, has_images=True, image_area_ratio=0.9)

    def test_needs_ocr_sufficient_text(self):
        """Test needs_ocr returns False for sufficient text."""
        engine = MockOCREngine()
        long_text = "A" * 200  # More than min_chars (100)
        # Text ratio = 200/2000 = 0.1, which is > min_ratio (0.05)
        assert not engine.needs_ocr(
            long_text,
            has_images=False,
            image_area_ratio=0.0,
            typical_page_length=2000
        )

    def test_preprocess_image_default(self):
        """Test preprocess_image returns input as-is by default."""
        engine = MockOCREngine()
        image = Image.new("RGB", (100, 100), color="white")
        result = engine.preprocess_image(image)
        assert result is image

    def test_calculate_confidence_empty_text(self):
        """Test _calculate_confidence returns 0 for empty text."""
        engine = MockOCREngine()
        assert engine._calculate_confidence("") == 0.0

    def test_calculate_confidence_short_text(self):
        """Test _calculate_confidence for short text."""
        engine = MockOCREngine()
        # Short text: base 0.5, no length bonus, no sentence bonus
        score = engine._calculate_confidence("Hi")
        assert 0.5 <= score < 0.7

    def test_calculate_confidence_long_text(self):
        """Test _calculate_confidence for long text with sentences."""
        engine = MockOCREngine()
        # Long text: base 0.5 + 0.2 length + 0.2 sentences + alnum bonus
        text = "This is a test. With multiple sentences. And some content."
        score = engine._calculate_confidence(text)
        assert 0.9 <= score <= 1.0

    def test_supported_languages(self):
        """Test supported_languages returns list of language codes."""
        engine = MockOCREngine()
        languages = engine.supported_languages()
        assert isinstance(languages, list)
        assert "en" in languages
        assert "zh" in languages