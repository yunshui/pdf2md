"""Resource manager for PDF processing."""

from typing import Optional

from pdf2md.ocr import OCREngine, PaddleOCREngine
from pdf2md.utils.logger import get_logger

logger = get_logger()


class ResourceManager:
    """Manages shared resources for PDF processing."""

    _instance: Optional["ResourceManager"] = None

    def __new__(cls) -> "ResourceManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the resource manager."""
        if not hasattr(self, "_initialized"):
            self._ocr_engine: Optional[OCREngine] = None
            self._initialized = True

    def get_ocr_engine(self, **kwargs) -> OCREngine:
        """Get or create the OCR engine.

        Args:
            **kwargs: Arguments to pass to OCR engine constructor.

        Returns:
            OCR engine instance.
        """
        if self._ocr_engine is None:
            logger.info("Initializing OCR engine...")
            self._ocr_engine = PaddleOCREngine(**kwargs)
            logger.info("OCR engine initialized")
        return self._ocr_engine

    def cleanup(self) -> None:
        """Clean up all resources."""
        if self._ocr_engine:
            logger.info("Cleaning up OCR engine...")
            self._ocr_engine = None
        logger.info("Resource cleanup complete")

    def get_instance(self) -> "ResourceManager":
        """Get the singleton instance.

        Returns:
            ResourceManager instance.
        """
        return self


# Global resource manager instance
resource_manager = ResourceManager()


def get_resource_manager() -> ResourceManager:
    """Get the global resource manager instance.

    Returns:
        The ResourceManager singleton instance.
    """
    return resource_manager