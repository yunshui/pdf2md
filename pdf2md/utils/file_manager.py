"""File management utilities for pdf2md."""

import hashlib
import os
import shutil
from pathlib import Path
from typing import List, Optional

from pdf2md.utils.logger import get_logger

logger = get_logger()


class FileManager:
    """Manages file operations for PDF processing."""

    def __init__(self, output_dir: Optional[str] = None) -> None:
        """Initialize the file manager.

        Args:
            output_dir: Output directory path. If None, uses input file's directory.
        """
        self.output_dir = Path(output_dir) if output_dir else None

    def scan_directory(self, directory: str) -> List[str]:
        """Scan directory for PDF files.

        Args:
            directory: Directory path to scan.

        Returns:
            List of PDF file paths.
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.error(f"Directory does not exist: {directory}")
            return []

        pdf_files = []
        for file_path in dir_path.glob("*.pdf"):
            if file_path.is_file():
                pdf_files.append(str(file_path))

        logger.info(f"Found {len(pdf_files)} PDF files in {directory}")
        return sorted(pdf_files)

    def create_output_structure(self, base_path: str, create_dir: bool = True) -> Path:
        """Create the output directory structure.

        Args:
            base_path: Base path for output.
            create_dir: Whether to create the directory structure.

        Returns:
            Path to the main output directory.
        """
        output_path = Path(base_path)

        if create_dir:
            output_path.mkdir(parents=True, exist_ok=True)
            # Create subdirectories
            (output_path / "docs").mkdir(exist_ok=True)
            (output_path / "assets").mkdir(exist_ok=True)
            logger.info(f"Created output directory structure: {output_path}")

        return output_path

    def get_output_path(self, input_path: str) -> Path:
        """Get the output path for a given input file.

        Args:
            input_path: Path to input PDF file.

        Returns:
            Path to output directory or file.
        """
        input_file = Path(input_path)
        base_name = input_file.stem

        if self.output_dir:
            # Use specified output directory directly (don't append _md)
            return self.output_dir
        else:
            # Use input file's directory and append _md
            return input_file.parent / f"{base_name}_md"

    def get_single_file_output_path(self, input_path: str) -> Path:
        """Get the single file output path.

        Args:
            input_path: Path to input PDF file.

        Returns:
            Path to output markdown file.
        """
        input_file = Path(input_path)
        base_name = input_file.stem

        if self.output_dir:
            base_dir = self.output_dir
        else:
            base_dir = input_file.parent

        return base_dir / f"{base_name}.md"

    def handle_overwrite(self, path: Path, overwrite: bool = True) -> bool:
        """Handle file/directory overwrite logic.

        Args:
            path: Path to check.
            overwrite: Whether to overwrite existing files.

        Returns:
            True if should proceed, False otherwise.
        """
        if not path.exists():
            return True

        if overwrite:
            if path.is_dir():
                shutil.rmtree(path)
                logger.info(f"Removed existing directory: {path}")
            else:
                path.unlink()
                logger.info(f"Removed existing file: {path}")
            return True

        logger.warning(f"Path exists and overwrite is False: {path}")
        return False

    def check_disk_space(self, path: Path, required_mb: int = 1000) -> bool:
        """Check if there's enough disk space.

        Args:
            path: Path to check.
            required_mb: Required space in MB.

        Returns:
            True if enough space, False otherwise.
        """
        try:
            usage = shutil.disk_usage(path.parent)
            available_mb = usage.free / (1024 * 1024)

            if available_mb < required_mb:
                logger.error(
                    f"Insufficient disk space. Required: {required_mb}MB, "
                    f"Available: {available_mb:.2f}MB"
                )
                return False

            return True
        except OSError as e:
            logger.error(f"Failed to check disk space: {e}")
            return False

    def get_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file.

        Args:
            file_path: Path to file.

        Returns:
            Hexadecimal hash string.
        """
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)

        return sha256_hash.hexdigest()

    def validate_pdf(self, file_path: str, max_size_mb: int = 200) -> bool:
        """Validate a PDF file.

        Args:
            file_path: Path to PDF file.
            max_size_mb: Maximum allowed file size in MB.

        Returns:
            True if valid, False otherwise.
        """
        path = Path(file_path)

        # Check if file exists
        if not path.exists():
            logger.error(f"File does not exist: {file_path}")
            return False

        # Check file extension
        if path.suffix.lower() != ".pdf":
            logger.error(f"File is not a PDF: {file_path}")
            return False

        # Check file size
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > max_size_mb:
            logger.error(
                f"File too large: {size_mb:.2f}MB (max {max_size_mb}MB): {file_path}"
            )
            return False

        # Check if file is readable
        if not os.access(file_path, os.R_OK):
            logger.error(f"File is not readable: {file_path}")
            return False

        return True