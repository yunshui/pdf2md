"""Command-line interface for pdf2md."""

import sys
from typing import Optional

import click

from pdf2md.ocr import PaddleOCREngine
from pdf2md.utils import FileManager, ProgressTracker, get_logger

logger = get_logger()


@click.command()
@click.option(
    "-input",
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True),
    help="Input PDF file or directory path.",
)
@click.option(
    "-output",
    "--output",
    "output_path",
    type=click.Path(),
    default=None,
    help="Output directory path. Defaults to input file directory.",
)
@click.option(
    "--ocr-mode",
    type=click.Choice(["auto", "always", "never"], case_sensitive=False),
    default="auto",
    help="OCR mode: auto (detect when needed), always (always use OCR), never (never use OCR).",
)
@click.option(
    "--ocr-min-chars",
    type=int,
    default=100,
    show_default=True,
    help="Minimum character count to trigger OCR.",
)
@click.option(
    "--ocr-min-ratio",
    type=float,
    default=0.05,
    show_default=True,
    help="Minimum text ratio to trigger OCR.",
)
@click.option(
    "--ocr-image-ratio",
    type=float,
    default=0.80,
    show_default=True,
    help="Maximum image ratio to trigger OCR.",
)
@click.option(
    "--image-quality",
    type=int,
    default=85,
    show_default=True,
    help="Image quality (1-100).",
)
@click.option(
    "--max-image-width",
    type=int,
    default=1920,
    show_default=True,
    help="Maximum image width in pixels.",
)
@click.option(
    "--memory-monitor",
    is_flag=True,
    default=False,
    help="Enable memory monitoring.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose output.",
)
@click.option(
    "--resume",
    is_flag=True,
    default=False,
    help="Resume from checkpoint if available.",
)
@click.version_option(version="0.1.0", prog_name="pdf2md")
def main(
    input_path: str,
    output_path: Optional[str],
    ocr_mode: str,
    ocr_min_chars: int,
    ocr_min_ratio: float,
    ocr_image_ratio: float,
    image_quality: int,
    max_image_width: int,
    memory_monitor: bool,
    verbose: bool,
    resume: bool,
) -> None:
    """PDF to Markdown Converter.

    Convert PDF files to Markdown format with multilingual OCR support,
    high-fidelity formatting preservation, and key summary extraction.

    Example usage:
        pdf2md -input ./report.pdf
        pdf2md -input ./reports/ -output ./output/
        pdf2md -input ./report.pdf --ocr-mode always
    """
    # Set logging level
    if verbose:
        logger.set_level("DEBUG")

    logger.info("PDF to Markdown Converter v0.1.0")
    logger.info(f"Input: {input_path}")

    # Initialize file manager
    file_manager = FileManager(output_path)

    # Check if input is a directory or file
    from pathlib import Path

    input_file = Path(input_path)

    if input_file.is_dir():
        # Batch processing
        process_directory(input_path, file_manager)
    elif input_file.is_file() and input_file.suffix.lower() == ".pdf":
        # Single file processing
        process_file(
            input_path,
            file_manager,
            ocr_mode,
            ocr_min_chars,
            ocr_min_ratio,
            ocr_image_ratio,
            resume,
        )
    else:
        logger.error(f"Invalid input: {input_path} (must be a PDF file or directory)")
        sys.exit(1)


def process_directory(
    directory: str,
    file_manager: FileManager,
) -> None:
    """Process all PDF files in a directory.

    Args:
        directory: Directory path.
        file_manager: File manager instance.
    """
    logger.info(f"Scanning directory: {directory}")

    pdf_files = file_manager.scan_directory(directory)

    if not pdf_files:
        logger.warning("No PDF files found in directory")
        return

    logger.info(f"Found {len(pdf_files)} PDF file(s) to process")

    for pdf_file in pdf_files:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {pdf_file}")

        try:
            process_file(
                pdf_file,
                file_manager,
                ocr_mode="auto",
                ocr_min_chars=100,
                ocr_min_ratio=0.05,
                ocr_image_ratio=0.80,
                resume=False,
            )
        except Exception as e:
            logger.error(f"Failed to process {pdf_file}: {e}")
            continue


def process_file(
    file_path: str,
    file_manager: FileManager,
    ocr_mode: str,
    ocr_min_chars: int,
    ocr_min_ratio: float,
    ocr_image_ratio: float,
    resume: bool,
) -> None:
    """Process a single PDF file.

    Args:
        file_path: Path to PDF file.
        file_manager: File manager instance.
        ocr_mode: OCR mode.
        ocr_min_chars: Minimum character count for OCR.
        ocr_min_ratio: Minimum text ratio for OCR.
        ocr_image_ratio: Maximum image ratio for OCR.
        resume: Whether to resume from checkpoint.
    """
    # Validate file
    if not file_manager.validate_pdf(file_path):
        return

    logger.info(f"Processing file: {file_path}")

    # Check disk space
    output_dir = file_manager.get_output_path(file_path)
    if not file_manager.check_disk_space(output_dir, required_mb=1000):
        logger.error("Insufficient disk space")
        return

    # Initialize progress tracker
    progress = ProgressTracker(str(output_dir))
    progress.start(file_path)

    try:
        # Placeholder for actual PDF processing
        # This will be implemented with the Core module
        logger.info("PDF processing not yet implemented")
        logger.info("This is a placeholder for the complete implementation")

        # For now, just create the output directory structure
        file_manager.create_output_structure(str(output_dir))

        # Create a placeholder markdown file
        placeholder_md = output_dir / "README.md"
        with open(placeholder_md, "w", encoding="utf-8") as f:
            f.write(f"# {file_path}\n\n")
            f.write("This is a placeholder for the converted Markdown content.\n\n")
            f.write("Full implementation coming soon.\n")

        logger.info(f"Created placeholder output: {output_dir}")

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise
    finally:
        progress.complete()


if __name__ == "__main__":
    main()