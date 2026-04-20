"""Command-line interface for pdf2md."""

import sys
from typing import Optional

import click

from pdf2md.core import Pipeline
from pdf2md.utils import FileManager, get_logger

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

    # Determine if OCR is enabled
    enable_ocr = ocr_mode != "never"

    # Initialize pipeline
    pipeline = Pipeline(
        file_manager=FileManager(output_path),
        enable_ocr=enable_ocr,
        ocr_config={
            "min_chars": ocr_min_chars,
            "min_ratio": ocr_min_ratio,
            "max_image_ratio": ocr_image_ratio,
        },
        image_config={
            "image_max_width": max_image_width,
            "image_quality": image_quality,
        },
    )

    try:
        # Check if input is a directory or file
        from pathlib import Path

        input_file = Path(input_path)

        if input_file.is_dir():
            # Batch processing
            process_directory(input_path, pipeline)
        elif input_file.is_file() and input_file.suffix.lower() == ".pdf":
            # Single file processing
            process_file(input_path, pipeline, resume)
        else:
            logger.error(f"Invalid input: {input_path} (must be a PDF file or directory)")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\nProcessing interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        pipeline.cleanup()


def process_directory(directory: str, pipeline: Pipeline) -> None:
    """Process all PDF files in a directory.

    Args:
        directory: Directory path.
        pipeline: Pipeline instance.
    """
    logger.info(f"Scanning directory: {directory}")

    results = pipeline.process_directory(directory)

    # Print summary
    success_count = sum(1 for r in results if r.success)
    logger.info(
        f"\n{'='*60}\n"
        f"Processing Summary\n"
        f"{'='*60}\n"
        f"Total files: {len(results)}\n"
        f"Successful: {success_count}\n"
        f"Failed: {len(results) - success_count}\n"
    )

    # Show results for each file
    for result in results:
        status = "✓" if result.success else "✗"
        logger.info(
            f"{status} {Path(result.file_path).name}: "
            f"{result.processed_pages}/{result.total_pages} pages processed"
        )


def process_file(file_path: str, pipeline: Pipeline, resume: bool) -> None:
    """Process a single PDF file.

    Args:
        file_path: Path to PDF file.
        pipeline: Pipeline instance.
        resume: Whether to resume from checkpoint.
    """
    logger.info(f"Processing file: {file_path}")

    result = pipeline.process_file(file_path, resume=resume)

    if result.success:
        logger.info(f"\n{'='*60}")
        logger.info(f"✓ Processing completed successfully")
        logger.info(f"{'='*60}")
        logger.info(f"Pages processed: {len(result.processed_pages)}/{result.total_pages}")
        logger.info(f"Output directory: {result.output_dir}")
    else:
        logger.error(f"\n{'='*60}")
        logger.error(f"✗ Processing failed")
        logger.error(f"{'='*60}")
        logger.error(f"Error: {result.error_message}")
        sys.exit(1)


if __name__ == "__main__":
    main()