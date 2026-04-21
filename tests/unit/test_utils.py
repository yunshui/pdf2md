"""Unit tests for Utils module."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from pdf2md.utils.file_manager import FileManager
from pdf2md.utils.progress import ProgressTracker
from pdf2md.utils.logger import get_logger


class TestLogger:
    """Test cases for Logger class."""

    def test_get_logger_singleton(self):
        """Test that get_logger returns singleton instance."""
        logger1 = get_logger()
        logger2 = get_logger()
        assert logger1 is logger2

    def test_logger_info(self, caplog):
        """Test info logging."""
        logger = get_logger()
        logger.info("Test message")
        assert "Test message" in caplog.text

    def test_logger_warning(self, caplog):
        """Test warning logging."""
        logger = get_logger()
        logger.warning("Warning message")
        assert "Warning message" in caplog.text

    def test_logger_error(self, caplog):
        """Test error logging."""
        logger = get_logger()
        logger.error("Error message")
        assert "Error message" in caplog.text

    def test_set_level(self):
        """Test setting log level."""
        logger = get_logger()
        logger.set_level("DEBUG")
        # Should not raise exception
        logger.set_level("INFO")


class TestFileManager:
    """Test cases for FileManager class."""

    def test_init_default(self):
        """Test FileManager initialization with default output_dir."""
        fm = FileManager()
        assert fm.output_dir is None

    def test_init_with_output_dir(self):
        """Test FileManager initialization with output_dir."""
        fm = FileManager(output_dir="/tmp/output")
        assert fm.output_dir == Path("/tmp/output")

    def test_scan_directory_nonexistent(self):
        """Test scanning non-existent directory."""
        fm = FileManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = fm.scan_directory(f"{tmpdir}/nonexistent")
            assert result == []

    def test_scan_directory_empty(self):
        """Test scanning empty directory."""
        fm = FileManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = fm.scan_directory(tmpdir)
            assert result == []

    def test_scan_directory_with_pdfs(self):
        """Test scanning directory with PDF files."""
        fm = FileManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test PDF files
            (Path(tmpdir) / "test1.pdf").touch()
            (Path(tmpdir) / "test2.pdf").touch()
            (Path(tmpdir) / "not_pdf.txt").touch()

            result = fm.scan_directory(tmpdir)
            assert len(result) == 2
            assert all(f.endswith(".pdf") for f in result)

    def test_create_output_structure(self):
        """Test creating output directory structure."""
        fm = FileManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = fm.create_output_structure(f"{tmpdir}/output", create_dir=True)
            assert output_path.exists()
            assert (output_path / "docs").exists()
            assert (output_path / "assets").exists()

    def test_create_output_structure_no_create(self):
        """Test getting output path without creating directory."""
        fm = FileManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = fm.create_output_structure(f"{tmpdir}/output", create_dir=False)
            assert not output_path.exists()

    def test_get_output_path_with_output_dir(self):
        """Test getting output path with specified output_dir."""
        fm = FileManager(output_dir="/tmp/output")
        result = fm.get_output_path("/input/test.pdf")
        # When output_dir is specified, use it directly without appending _md
        assert result == Path("/tmp/output")

    def test_get_output_path_without_output_dir(self):
        """Test getting output path without specified output_dir."""
        fm = FileManager()
        result = fm.get_output_path("/input/test.pdf")
        assert result == Path("/input/test_md")

    def test_get_single_file_output_path(self):
        """Test getting single file output path."""
        fm = FileManager(output_dir="/tmp/output")
        result = fm.get_single_file_output_path("/input/test.pdf")
        assert result == Path("/tmp/output/test.md")

    def test_handle_overwrite_nonexistent(self):
        """Test handle_overwrite with non-existent path."""
        fm = FileManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nonexistent.txt"
            assert fm.handle_overwrite(path, overwrite=False)

    def test_handle_overwrite_with_overwrite(self):
        """Test handle_overwrite with overwrite=True."""
        fm = FileManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.txt"
            path.write_text("test")
            assert fm.handle_overwrite(path, overwrite=True)
            assert not path.exists()

    def test_handle_overwrite_without_overwrite(self):
        """Test handle_overwrite with overwrite=False."""
        fm = FileManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.txt"
            path.write_text("test")
            assert not fm.handle_overwrite(path, overwrite=False)
            assert path.exists()

    def test_check_disk_space(self):
        """Test checking disk space."""
        fm = FileManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test"
            # Should pass on normal systems
            assert fm.check_disk_space(path, required_mb=1)

    def test_get_file_hash(self):
        """Test calculating file hash."""
        fm = FileManager()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content")
            temp_path = f.name

        try:
            hash1 = fm.get_file_hash(temp_path)
            hash2 = fm.get_file_hash(temp_path)
            assert hash1 == hash2
            assert len(hash1) == 64  # SHA256 produces 64 hex chars
        finally:
            os.unlink(temp_path)

    def test_validate_pdf_valid(self):
        """Test validating a valid PDF file."""
        fm = FileManager()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".pdf") as f:
            f.write("fake pdf content")
            temp_path = f.name

        try:
            # File exists, has .pdf extension, is small, readable
            assert fm.validate_pdf(temp_path, max_size_mb=200)
        finally:
            os.unlink(temp_path)

    def test_validate_pdf_nonexistent(self):
        """Test validating non-existent file."""
        fm = FileManager()
        assert not fm.validate_pdf("/nonexistent/file.pdf")

    def test_validate_pdf_wrong_extension(self):
        """Test validating file with wrong extension."""
        fm = FileManager()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test")
            temp_path = f.name

        try:
            assert not fm.validate_pdf(temp_path)
        finally:
            os.unlink(temp_path)

    def test_validate_pdf_too_large(self):
        """Test validating file that's too large."""
        fm = FileManager()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".pdf") as f:
            # Write 1MB of data
            f.write("x" * (1024 * 1024))
            temp_path = f.name

        try:
            # File is 1MB but max is 0.5MB
            assert not fm.validate_pdf(temp_path, max_size_mb=0.5)
        finally:
            os.unlink(temp_path)


class TestProgressTracker:
    """Test cases for ProgressTracker class."""

    def test_init_default(self):
        """Test ProgressTracker initialization with default checkpoint_dir."""
        pt = ProgressTracker()
        assert pt.checkpoint_dir is None
        assert pt.current_file is None
        assert pt.start_time is None

    def test_init_with_checkpoint_dir(self):
        """Test ProgressTracker initialization with checkpoint_dir."""
        pt = ProgressTracker(checkpoint_dir="/tmp/checkpoints")
        assert pt.checkpoint_dir == Path("/tmp/checkpoints")

    def test_start(self):
        """Test starting progress tracking."""
        pt = ProgressTracker()
        pt.start("/test/file.pdf")
        assert pt.current_file == "/test/file.pdf"
        assert pt.start_time is not None
        assert "file_path" in pt.checkpoint_data

    def test_complete(self):
        """Test completing progress tracking."""
        pt = ProgressTracker()
        pt.start("/test/file.pdf")
        pt.complete()
        assert pt.current_file is None
        assert pt.start_time is None
        assert pt.checkpoint_data == {}

    def test_update(self, caplog):
        """Test updating progress."""
        pt = ProgressTracker()
        pt.update(0.5, "Processing")
        assert "Progress: 50.0%" in caplog.text

    def test_save_and_load_checkpoint(self):
        """Test saving and loading checkpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = Path(tmpdir) / "test.pdf"
            test_file.write_text("test content")

            pt = ProgressTracker(checkpoint_dir=tmpdir)
            checkpoint_path = pt.save_checkpoint(
                file_path=str(test_file),
                total_pages=10,
                processed_pages=[1, 2, 3],
                failed_pages=[4],
            )
            assert checkpoint_path.exists()

            # Load the checkpoint
            loaded = pt.load_checkpoint(str(test_file))
            assert loaded is not None
            assert loaded["total_pages"] == 10
            assert loaded["processed_pages"] == [1, 2, 3]
            assert loaded["failed_pages"] == [4]

    def test_load_checkpoint_invalid_hash(self):
        """Test loading checkpoint with invalid file hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = Path(tmpdir) / "test.pdf"
            test_file.write_text("original content")

            pt = ProgressTracker(checkpoint_dir=tmpdir)
            pt.save_checkpoint(
                file_path=str(test_file),
                total_pages=10,
                processed_pages=[1, 2],
                failed_pages=[],
            )

            # Modify the file to change hash
            test_file.write_text("modified content")

            # Load should return None due to hash mismatch
            loaded = pt.load_checkpoint(str(test_file))
            assert loaded is None

    def test_load_checkpoint_nonexistent(self):
        """Test loading non-existent checkpoint."""
        pt = ProgressTracker()
        loaded = pt.load_checkpoint("/nonexistent/file.pdf")
        assert loaded is None

    def test_remove_checkpoint(self):
        """Test removing checkpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.pdf"
            test_file.write_text("test")

            pt = ProgressTracker(checkpoint_dir=tmpdir)
            pt.save_checkpoint(
                file_path=str(test_file),
                total_pages=5,
                processed_pages=[1, 2],
                failed_pages=[],
            )

            checkpoint_path = Path(tmpdir) / "test.pdf.checkpoint.json"
            assert checkpoint_path.exists()

            pt.remove_checkpoint(str(test_file))
            assert not checkpoint_path.exists()

    def test_get_processed_pages(self):
        """Test getting processed pages from checkpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.pdf"
            test_file.write_text("test")

            pt = ProgressTracker(checkpoint_dir=tmpdir)
            pt.save_checkpoint(
                file_path=str(test_file),
                total_pages=5,
                processed_pages=[1, 2, 3],
                failed_pages=[],
            )

            pages = pt.get_processed_pages(str(test_file))
            assert pages == [1, 2, 3]

    def test_get_failed_pages(self):
        """Test getting failed pages from checkpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.pdf"
            test_file.write_text("test")

            pt = ProgressTracker(checkpoint_dir=tmpdir)
            pt.save_checkpoint(
                file_path=str(test_file),
                total_pages=5,
                processed_pages=[1, 2],
                failed_pages=[3, 4],
            )

            pages = pt.get_failed_pages(str(test_file))
            assert pages == [3, 4]

    def test_should_process_page(self):
        """Test checking if page should be processed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.pdf"
            test_file.write_text("test")

            pt = ProgressTracker(checkpoint_dir=tmpdir)
            pt.save_checkpoint(
                file_path=str(test_file),
                total_pages=5,
                processed_pages=[1, 2, 3],
                failed_pages=[],
            )

            assert not pt.should_process_page(str(test_file), 1)  # Already processed
            assert not pt.should_process_page(str(test_file), 2)
            assert pt.should_process_page(str(test_file), 4)  # Not processed
            assert pt.should_process_page(str(test_file), 5)

    def test_is_page_failed(self):
        """Test checking if page failed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.pdf"
            test_file.write_text("test")

            pt = ProgressTracker(checkpoint_dir=tmpdir)
            pt.save_checkpoint(
                file_path=str(test_file),
                total_pages=5,
                processed_pages=[1, 2],
                failed_pages=[3, 4],
            )

            assert pt.is_page_failed(str(test_file), 3)
            assert pt.is_page_failed(str(test_file), 4)
            assert not pt.is_page_failed(str(test_file), 1)
            assert not pt.is_page_failed(str(test_file), 5)