"""Pipeline orchestration for PDF processing."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pdfplumber

from pdf2md.core.page_processor import PageData, PageProcessor
from pdf2md.core.resource_manager import get_resource_manager
from pdf2md.deduplicator import ChapterDetector, EdgeTextHandler, HeaderFooterDeduplicator
from pdf2md.markdown import MarkdownGenerator
from pdf2md.utils import FileManager, ProgressTracker, get_logger

logger = get_logger()


@dataclass
class ProcessingResult:
    """Result of processing a PDF file."""

    file_path: str
    total_pages: int
    processed_pages: List[int]
    failed_pages: List[int]
    pages_data: List[PageData]
    output_dir: str
    success: bool
    error_message: Optional[str]

    def get_success_rate(self) -> float:
        """Get the success rate of page processing.

        Returns:
            Success rate (0.0 to 1.0).
        """
        if self.total_pages == 0:
            return 0.0
        return len(self.processed_pages) / self.total_pages


class Pipeline:
    """Orchestrates the PDF to Markdown conversion pipeline."""

    def __init__(
        self,
        file_manager: Optional[FileManager] = None,
        progress_tracker: Optional[ProgressTracker] = None,
        enable_ocr: bool = True,
        ocr_config: Optional[dict] = None,
        image_config: Optional[dict] = None,
    ) -> None:
        """Initialize the pipeline.

        Args:
            file_manager: File manager instance.
            progress_tracker: Progress tracker instance.
            enable_ocr: Whether to enable OCR.
            ocr_config: OCR configuration options.
            image_config: Image extraction configuration.
        """
        self.file_manager = file_manager or FileManager()
        self.progress_tracker = progress_tracker or ProgressTracker()
        self.enable_ocr = enable_ocr

        # Configuration
        self.ocr_config = ocr_config or {}
        self.image_config = image_config or {
            "max_width": 1920,
            "quality": 85,
        }

        # Resource manager
        self.resource_manager = get_resource_manager()

        # Page processor (initialized when needed)
        self.page_processor: Optional[PageProcessor] = None

    def process_file(
        self,
        file_path: str,
        output_dir: Optional[str] = None,
        resume: bool = False,
    ) -> ProcessingResult:
        """Process a single PDF file.

        Args:
            file_path: Path to PDF file.
            output_dir: Output directory path.
            resume: Whether to resume from checkpoint.

        Returns:
            ProcessingResult with processing details.
        """
        logger.info(f"Starting processing: {file_path}")

        # Validate file
        if not self.file_manager.validate_pdf(file_path):
            return ProcessingResult(
                file_path=file_path,
                total_pages=0,
                processed_pages=[],
                failed_pages=[],
                pages_data=[],
                output_dir="",
                success=False,
                error_message="File validation failed",
            )

        # Get output directory
        if output_dir:
            self.file_manager.output_dir = Path(output_dir)
        output_path = self.file_manager.get_output_path(file_path)

        # Check disk space
        if not self.file_manager.check_disk_space(output_path):
            return ProcessingResult(
                file_path=file_path,
                total_pages=0,
                processed_pages=[],
                failed_pages=[],
                pages_data=[],
                output_dir=str(output_path),
                success=False,
                error_message="Insufficient disk space",
            )

        # Create output structure
        self.file_manager.create_output_structure(str(output_path))

        # Start tracking
        self.progress_tracker.checkpoint_dir = Path(output_path)
        self.progress_tracker.start(file_path)

        try:
            # Open PDF and process
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                logger.info(f"PDF has {total_pages} page(s)")

                # Get pages to skip if resuming
                skip_pages = []
                if resume:
                    skip_pages = self.progress_tracker.get_processed_pages(file_path)

                # Initialize page processor
                self.page_processor = PageProcessor(
                    enable_ocr=self.enable_ocr,
                    **self.image_config,
                )

                # Process each page
                pages_data = []
                processed_pages = []
                failed_pages = []

                for page_num, page in enumerate(pdf.pages, start=1):
                    try:
                        # Skip if already processed
                        if page_num in skip_pages:
                            logger.info(f"Skipping page {page_num} (already processed)")
                            continue

                        # Update progress
                        self.progress_tracker.update(
                            page_num / total_pages, f"Processing page {page_num}"
                        )

                        # Process page
                        page_data = self.page_processor.process_page(
                            page, page_num, str(output_path)
                        )
                        pages_data.append(page_data)
                        processed_pages.append(page_num)

                        # Save checkpoint periodically
                        if len(processed_pages) % 5 == 0:
                            self.progress_tracker.save_checkpoint(
                                file_path,
                                total_pages,
                                processed_pages,
                                failed_pages,
                            )

                    except Exception as e:
                        logger.error(f"Failed to process page {page_num}: {e}")
                        failed_pages.append(page_num)

                # Final checkpoint
                self.progress_tracker.save_checkpoint(
                    file_path, total_pages, processed_pages, failed_pages
                )

                # Generate output
                self._generate_output(pages_data, output_path, file_path)

                # Remove checkpoint on success
                self.progress_tracker.remove_checkpoint(file_path)

                result = ProcessingResult(
                    file_path=file_path,
                    total_pages=total_pages,
                    processed_pages=processed_pages,
                    failed_pages=failed_pages,
                    pages_data=pages_data,
                    output_dir=str(output_path),
                    success=len(failed_pages) == 0,
                    error_message=None,
                )

                logger.info(
                    f"Processing complete: {len(processed_pages)}/{total_pages} pages "
                    f"successfully processed"
                )

                return result

        except Exception as e:
            logger.error(f"Error processing file: {e}")
            return ProcessingResult(
                file_path=file_path,
                total_pages=0,
                processed_pages=[],
                failed_pages=[],
                pages_data=[],
                output_dir=str(output_path),
                success=False,
                error_message=str(e),
            )
        finally:
            self.progress_tracker.complete()

    def process_directory(self, directory: str) -> List[ProcessingResult]:
        """Process all PDF files in a directory.

        Args:
            directory: Directory path.

        Returns:
            List of ProcessingResult objects.
        """
        logger.info(f"Processing directory: {directory}")

        results = []
        pdf_files = self.file_manager.scan_directory(directory)

        for pdf_file in pdf_files:
            try:
                result = self.process_file(pdf_file)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {pdf_file}: {e}")
                results.append(
                    ProcessingResult(
                        file_path=pdf_file,
                        total_pages=0,
                        processed_pages=[],
                        failed_pages=[],
                        pages_data=[],
                        output_dir="",
                        success=False,
                        error_message=str(e),
                    )
                )

        # Summary
        success_count = sum(1 for r in results if r.success)
        logger.info(
            f"Directory processing complete: {success_count}/{len(results)} files "
            f"successfully processed"
        )

        return results

    def _generate_output(
        self, pages_data: List[PageData], output_dir: Path, source_path: str
    ) -> None:
        """Generate output files from processed page data.

        Args:
            pages_data: List of page data.
            output_dir: Output directory.
            source_path: Source file path.
        """
        logger.info("Generating output files...")

        # Detect chapters
        chapter_detector = ChapterDetector()
        chapter_boundaries = chapter_detector.detect_chapters(pages_data)

        logger.info(f"Detected {len(chapter_boundaries)} chapter boundaries")

        # Deduplicate headers/footers
        deduplicator = HeaderFooterDeduplicator()
        deduplicated_headers = deduplicator.deduplicate(
            pages_data, chapter_boundaries
        )

        # Handle edge text
        edge_handler = EdgeTextHandler()
        edge_texts = edge_handler.extract_edge_text(pages_data)

        # Generate Markdown output
        markdown_generator = MarkdownGenerator(
            base_output_dir=output_dir,
            include_images=True,
            include_tables=True,
            include_ocr_text=True,
        )

        # Determine output format
        output_format = markdown_generator.determine_output_format(pages_data)
        logger.info(f"Output format: {output_format}")

        if output_format == "multi":
            # Generate main file
            markdown_generator.generate_main_file(pages_data, source_path, output_dir)

            # Generate detail files
            markdown_generator.generate_detail_files(pages_data, output_dir, chapter_boundaries)
        else:
            # Generate single file
            markdown_generator.generate_single_file(pages_data, source_path, output_dir)

        logger.info("Output generation complete")

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.page_processor:
            self.page_processor.cleanup()
        self.resource_manager.cleanup()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()