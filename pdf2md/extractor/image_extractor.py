"""Image extraction from PDF pages."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pdfplumber
from PIL import Image

from pdf2md.extractor.pdfplumber_types import TYPE_PAGE
from pdf2md.utils.logger import get_logger

logger = get_logger()


@dataclass
class ImageInfo:
    """Information about an extracted image."""

    page_number: int
    image_index: int
    path: str
    x0: float
    y0: float
    x1: float
    y1: float
    width: float
    height: float
    format: str = "png"

    @property
    def filename(self) -> str:
        """Get the image filename."""
        return Path(self.path).name

    @property
    def relative_path(self) -> str:
        """Get relative path from output directory."""
        return f"assets/{self.filename}"


class ImageExtractor:
    """Extracts images from PDF pages."""

    def __init__(
        self,
        max_width: int = 1920,
        quality: int = 85,
        format: str = "png",
    ) -> None:
        """Initialize the image extractor.

        Args:
            max_width: Maximum image width in pixels.
            quality: Image quality (1-100) for JPEG.
            format: Output image format (png, jpeg, webp).
        """
        self.max_width = max_width
        self.quality = quality
        self.format = format.lower()

        if self.format not in ["png", "jpeg", "jpg", "webp"]:
            logger.warning(f"Unsupported format {format}, using png")
            self.format = "png"

        # Try to import pypdf for image extraction
        self.has_pypdf = False
        try:
            import pypdf
            self.has_pypdf = True
            logger.debug("pypdf available for image extraction")
        except ImportError:
            logger.debug("pypdf not available, will use pdfplumber fallback")

    def extract(
        self,
        page,
        page_number: int,
        output_dir: str,
    ) -> list[ImageInfo]:
        """Extract images from a PDF page.

        Args:
            page: pdfplumber Page object.
            page_number: Page number (1-indexed).
            output_dir: Output directory for images.

        Returns:
            List of ImageInfo objects.
        """
        images = []

        if not hasattr(page, "images") or not page.images:
            logger.debug(f"No images found on page {page_number}")
            return images

        logger.debug(f"Extracting {len(page.images)} images from page {page_number}")

        for idx, page_image in enumerate(page.images):
            try:
                image_info = self._extract_single_image(
                    page, page_image, page_number, idx, output_dir
                )
                if image_info:
                    images.append(image_info)

            except Exception as e:
                logger.error(
                    f"Error extracting image {idx} from page {page_number}: {e}"
                )
                continue

        logger.info(f"Extracted {len(images)} images from page {page_number}")
        return images

    def _extract_single_image(
        self,
        page: TYPE_PAGE,
        page_image: dict,
        page_number: int,
        image_index: int,
        output_dir: str,
    ) -> Optional[ImageInfo]:
        """Extract a single image from a page.

        Args:
            page: pdfplumber Page object.
            page_image: Image dictionary from pdfplumber.
            page_number: Page number (1-indexed).
            image_index: Image index on the page.
            output_dir: Output directory.

        Returns:
            ImageInfo object, or None if extraction failed.
        """
        # Get image position and dimensions
        x0 = page_image.get("x0", 0)
        y0 = page_image.get("top", 0)
        x1 = page_image.get("x1", 0)
        y1 = page_image.get("bottom", 0)
        width = x1 - x0
        height = y1 - y0

        # Generate filename
        filename = self._generate_filename(page_number, image_index, self.format)
        output_path = Path(output_dir) / "assets" / filename

        # Extract the image
        try:
            # Try pypdf first (doesn't require poppler)
            if self.has_pypdf:
                pil_image = self._extract_with_pypdf(page, page_number, page_image)

            if pil_image is None:
                # Fallback to pdfplumber direct extraction
                pil_image = self._extract_image_directly(page, page_image)

            if pil_image is None:
                # Last resort: convert page to image (requires poppler)
                pil_image = self._page_to_pil_image(page)
                if pil_image is not None:
                    # Crop to image area
                    pil_image = self._crop_image(
                        pil_image,
                        x0,
                        y0,
                        x1,
                        y1,
                        page.width,
                        page.height,
                    )

            if pil_image is None:
                logger.warning(f"Could not extract image {image_index} on page {page_number}")
                return None

            # Optimize and save
            self._optimize_and_save(pil_image, output_path)

            logger.debug(
                f"Saved image: {filename} ({pil_image.width}x{pil_image.height})"
            )

            return ImageInfo(
                page_number=page_number,
                image_index=image_index,
                path=str(output_path),
                x0=x0,
                y0=y0,
                x1=x1,
                y1=y1,
                width=width,
                height=height,
                format=self.format,
            )

        except Exception as e:
            logger.error(f"Error processing image {image_index} on page {page_number}: {e}")
            return None

    def _extract_with_pypdf(
        self, page: TYPE_PAGE, page_number: int, page_image: dict
    ) -> Optional[Image.Image]:
        """Extract image using pypdf (doesn't require poppler).

        Args:
            page: pdfplumber Page object.
            page_number: Page number.
            page_image: Image dictionary from pdfplumber.

        Returns:
            PIL Image, or None if extraction failed.
        """
        try:
            import pypdf

            # Get PDF file path
            pdf_path = getattr(page.pdf.stream, 'name', None)
            if not pdf_path:
                return None

            # Open PDF with pypdf
            reader = pypdf.PdfReader(pdf_path)

            # Get images for the page
            # Note: pypdf uses 0-indexed pages
            pypdf_page = reader.pages[page_number - 1]
            images = pypdf_page.images

            # Find matching image by position
            for img in images:
                img_x0 = img.indirect_reference.get_object().get('x0', 0)
                img_y0 = img.indirect_reference.get_object().get('y0', 0)
                img_x1 = img.indirect_reference.get_object().get('x1', 0)
                img_y1 = img.indirect_reference.get_object().get('y1', 0)

                # Check if this is the image we're looking for
                if (abs(img_x0 - page_image.get('x0', 0)) < 1 and
                    abs(img_y0 - page_image.get('y0', 0)) < 1):
                    return img.image

            # If no match, return first image
            if images:
                return images[0].image

            return None

        except Exception as e:
            logger.debug(f"pypdf extraction failed: {e}")
            return None

    def _extract_image_directly(
        self, page: TYPE_PAGE, page_image: dict
    ) -> Optional[Image.Image]:
        """Extract image directly from PDF stream without poppler.

        Args:
            page: pdfplumber Page object.
            page_image: Image dictionary from pdfplumber.

        Returns:
            PIL Image, or None if extraction failed.
        """
        try:
            # Get the image object from the PDF
            if 'stream' not in page_image:
                return None

            # Try to extract image data directly
            from io import BytesIO

            stream = page_image['stream']

            # Get raw image data from PDF stream
            try:
                # Try to get image data
                if hasattr(stream, 'get_data'):
                    data = stream.get_data()
                elif hasattr(stream, 'get_rawdata'):
                    data = stream.get_rawdata()
                else:
                    # Try accessing as bytes
                    data = stream
            except:
                return None

            if not data:
                return None

            # Try to open the image data
            image = Image.open(BytesIO(data))

            # Convert to RGB for better compatibility
            if image.mode == 'CMYK':
                image = image.convert('RGB')
            elif image.mode not in ('RGB', 'RGBA', 'L'):
                image = image.convert('RGB')

            return image

        except Exception as e:
            logger.debug(f"Could not extract image directly: {e}")
            return None

    def _page_to_pil_image(self, page: TYPE_PAGE) -> Optional[Image.Image]:
        """Convert a pdfplumber page to a PIL Image.

        Args:
            page: pdfplumber Page object.

        Returns:
            PIL Image, or None if conversion failed.
        """
        try:
            # This requires pdf2image, which converts PDF to image
            from pdf2image import convert_from_path

            # Get the file path from the PDF stream
            pdf_path = getattr(page.pdf.stream, 'name', None)
            if not pdf_path:
                logger.error("Could not determine PDF file path for image extraction")
                return None

            # Convert specific page to image
            images = convert_from_path(
                pdf_path,
                first_page=page.page_number,
                last_page=page.page_number,
                dpi=150,
            )

            return images[0] if images else None

        except ImportError:
            logger.error(
                "pdf2image not installed. Install with: pip install pdf2image"
            )
            return None
        except Exception as e:
            logger.error(f"Error converting page to image: {e}")
            return None

    def _extract_image_directly(
        self, page: TYPE_PAGE, page_image: dict
    ) -> Optional[Image.Image]:
        """Extract image directly from PDF stream without poppler.

        Args:
            page: pdfplumber Page object.
            page_image: Image dictionary from pdfplumber.

        Returns:
            PIL Image, or None if extraction failed.
        """
        try:
            # Get the image object from the PDF
            if 'stream' not in page_image:
                return None

            # Try to extract image data directly
            from io import BytesIO
            from PIL import Image

            stream = page_image['stream']

            # Get raw image data from PDF stream
            try:
                # Try to get image data
                if hasattr(stream, 'get_data'):
                    data = stream.get_data()
                elif hasattr(stream, 'get_rawdata'):
                    data = stream.get_rawdata()
                else:
                    # Try accessing as bytes
                    data = stream
            except:
                return None

            if not data:
                return None

            # Try to open the image data
            image = Image.open(BytesIO(data))

            # Convert to RGB for better compatibility
            if image.mode == 'CMYK':
                image = image.convert('RGB')
            elif image.mode not in ('RGB', 'RGBA', 'L'):
                image = image.convert('RGB')

            return image

        except Exception as e:
            logger.debug(f"Could not extract image directly: {e}")
            return None

    def _crop_image(
        self,
        image: Image.Image,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        page_width: float,
        page_height: float,
    ) -> Optional[Image.Image]:
        """Crop image to specified bounds.

        Args:
            image: PIL Image to crop.
            x0: Left coordinate (PDF coordinates).
            y0: Top coordinate (PDF coordinates).
            x1: Right coordinate (PDF coordinates).
            y1: Bottom coordinate (PDF coordinates).
            page_width: Page width (PDF coordinates).
            page_height: Page height (PDF coordinates).

        Returns:
            Cropped PIL Image, or None if cropping failed.
        """
        try:
            # Convert PDF coordinates to image coordinates
            img_width, img_height = image.size

            # Calculate scaling factors
            scale_x = img_width / page_width
            scale_y = img_height / page_height

            # Convert coordinates
            left = int(x0 * scale_x)
            top = int(y0 * scale_y)
            right = int(x1 * scale_x)
            bottom = int(y1 * scale_y)

            # Ensure bounds are within image
            left = max(0, left)
            top = max(0, top)
            right = min(img_width, right)
            bottom = min(img_height, bottom)

            if right <= left or bottom <= top:
                logger.warning("Invalid crop bounds")
                return None

            # Crop the image
            cropped = image.crop((left, top, right, bottom))

            return cropped

        except Exception as e:
            logger.error(f"Error cropping image: {e}")
            return None

    def _optimize_and_save(self, image: Image.Image, output_path: Path) -> None:
        """Optimize and save image.

        Args:
            image: PIL Image to save.
            output_path: Output path.
        """
        # Resize if too wide
        if image.width > self.max_width:
            ratio = self.max_width / image.width
            new_height = int(image.height * ratio)
            image = image.resize((self.max_width, new_height), Image.Resampling.LANCZOS)
            logger.debug(f"Resized image to {self.max_width}x{new_height}")

        # Convert to RGB if saving as JPEG
        if self.format in ["jpeg", "jpg"] and image.mode != "RGB":
            image = image.convert("RGB")

        # Save the image
        save_kwargs = {}
        if self.format in ["jpeg", "jpg"]:
            save_kwargs["quality"] = self.quality
            save_kwargs["optimize"] = True
        elif self.format == "webp":
            save_kwargs["quality"] = self.quality

        image.save(output_path, format=self.format.upper(), **save_kwargs)

    def _generate_filename(
        self,
        page_number: int,
        image_index: int,
        format: str,
    ) -> str:
        """Generate a unique filename for an extracted image.

        Args:
            page_number: Page number.
            image_index: Image index on the page.
            format: Image format.

        Returns:
            Generated filename.
        """
        ext = "jpg" if format in ["jpeg", "jpg"] else format
        return f"page_{page_number}_image_{image_index + 1}.{ext}"

    def get_image_area_ratio(
        self,
        page: TYPE_PAGE,
    ) -> float:
        """Calculate the ratio of page area occupied by images.

        Args:
            page: pdfplumber Page object.

        Returns:
            Ratio of page area (0.0 to 1.0).
        """
        if not hasattr(page, "images") or not page.images:
            return 0.0

        page_area = page.width * page.height
        if page_area == 0:
            return 0.0

        image_area = 0.0
        for page_image in page.images:
            x0 = page_image.get("x0", 0)
            y0 = page_image.get("top", 0)
            x1 = page_image.get("x1", 0)
            y1 = page_image.get("bottom", 0)

            width = max(0, x1 - x0)
            height = max(0, y1 - y0)
            image_area += width * height

        return image_area / page_area