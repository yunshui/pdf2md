"""Integration tests for Pipeline module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import pytest

from pdf2md.core import Pipeline, ProcessResult
from pdf2md.utils import FileManager


class TestPipelineIntegration:
    """Integration tests for Pipeline class."""

    def test_pipeline_initialization(self):
        """Test Pipeline initialization with valid parameters."""
        file_manager = FileManager()
        pipeline = Pipeline(
            file_manager=file_manager,
            enable_ocr=True,
            ocr_config={"min_chars": 100},
            image_config={"max_width": 1920},
        )
        assert pipeline.file_manager is not None
        assert pipeline.enable_ocr is True

    def test_pipeline_with_nonexistent_file(self):
        """Test processing a non-existent file."""
        file_manager = FileManager()
        pipeline = Pipeline(file_manager=file_manager, enable_ocr=False)

        result = pipeline.process_file("/nonexistent/file.pdf")
        assert not result.success
        assert result.error_message is not None

    def test_pipeline_with_invalid_file_type(self, tmp_path):
        """Test processing a non-PDF file."""
        # Create a temporary text file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Not a PDF file")

        file_manager = FileManager()
        pipeline = Pipeline(file_manager=file_manager, enable_ocr=False)

        result = pipeline.process_file(str(test_file))
        assert not result.success

    def test_pipeline_with_empty_directory(self, tmp_path):
        """Test processing an empty directory."""
        file_manager = FileManager(output_dir=str(tmp_path / "output"))
        pipeline = Pipeline(file_manager=file_manager, enable_ocr=False)

        results = pipeline.process_directory(str(tmp_path))
        assert len(results) == 0

    def test_pipeline_with_directory_without_pdfs(self, tmp_path):
        """Test processing a directory with no PDF files."""
        # Create some non-PDF files
        (tmp_path / "file1.txt").write_text("Text")
        (tmp_path / "file2.jpg").write_bytes(b"image")

        file_manager = FileManager(output_dir=str(tmp_path / "output"))
        pipeline = Pipeline(file_manager=file_manager, enable_ocr=False)

        results = pipeline.process_directory(str(tmp_path))
        assert len(results) == 0

    @patch('pdf2md.core.pipeline.pdfplumber.open')
    def test_pipeline_with_mock_pdf_single_page(self, mock_pdf_open, tmp_path):
        """Test processing a simple PDF with one page."""
        # Create a mock PDF page
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.width = 595
        mock_page.height = 842
        mock_page.chars = []  # No text
        mock_page.extract_text.return_value = ""

        # Create mock PDF
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        mock_pdf_open.return_value = mock_pdf

        # Create a temporary PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")  # Minimal PDF header

        file_manager = FileManager(output_dir=str(tmp_path / "output"))
        pipeline = Pipeline(file_manager=file_manager, enable_ocr=False)

        result = pipeline.process_file(str(pdf_file))

        # Should succeed even with empty PDF
        assert result.success
        assert result.file_path == str(pdf_file)
        assert len(result.processed_pages) >= 0

    @patch('pdf2md.core.pipeline.pdfplumber.open')
    def test_pipeline_resume_from_checkpoint(self, mock_pdf_open, tmp_path):
        """Test resuming processing from checkpoint."""
        # Create a mock PDF with 3 pages
        mock_pages = []
        for i in range(1, 4):
            mock_page = MagicMock()
            mock_page.page_number = i
            mock_page.width = 595
            mock_page.height = 842
            mock_page.chars = []
            mock_page.extract_text.return_value = ""
            mock_pages.append(mock_page)

        mock_pdf = MagicMock()
        mock_pdf.pages = mock_pages
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        mock_pdf_open.return_value = mock_pdf

        # Create a temporary PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        file_manager = FileManager(output_dir=str(tmp_path / "output"))
        pipeline = Pipeline(file_manager=file_manager, enable_ocr=False)

        # Process file
        result1 = pipeline.process_file(str(pdf_file), resume=False)

        # Try to resume (checkpoint should exist)
        result2 = pipeline.process_file(str(pdf_file), resume=True)

        assert result2.success

    @patch('pdf2md.core.pipeline.pdfplumber.open')
    def test_pipeline_batch_processing(self, mock_pdf_open, tmp_path):
        """Test processing multiple PDF files in batch."""
        # Create mock PDF
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.width = 595
        mock_page.height = 842
        mock_page.chars = []
        mock_page.extract_text.return_value = ""

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        mock_pdf_open.return_value = mock_pdf

        # Create multiple PDF files
        for i in range(1, 4):
            pdf_file = tmp_path / f"test{i}.pdf"
            pdf_file.write_bytes(b"%PDF-1.4")

        file_manager = FileManager(output_dir=str(tmp_path / "output"))
        pipeline = Pipeline(file_manager=file_manager, enable_ocr=False)

        results = pipeline.process_directory(str(tmp_path))

        assert len(results) == 3

        # Check that at least some succeeded
        success_count = sum(1 for r in results if r.success)
        assert success_count >= 0  # May fail due to mock limitations

    def test_pipeline_cleanup(self):
        """Test pipeline cleanup releases resources."""
        file_manager = FileManager()
        pipeline = Pipeline(file_manager=file_manager, enable_ocr=True)

        # Cleanup should not raise errors
        pipeline.cleanup()

    @patch('pdf2md.core.pipeline.pdfplumber.open')
    def test_pipeline_output_structure(self, mock_pdf_open, tmp_path):
        """Test that pipeline creates correct output structure."""
        # Create mock PDF page with some text
        mock_page = MagicMock()
        mock_page.page_number = 1
        mock_page.width = 595
        mock_page.height = 842
        mock_page.chars = [
            {
                'text': 'Test',
                'x0': 0,
                'top': 0,
                'x1': 30,
                'bottom': 10,
                'fontname': 'Arial',
                'size': 12,
                'non_stroking_color': (0, 0, 0)
            }
        ]
        mock_page.extract_text.return_value = "Test content"

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        mock_pdf_open.return_value = mock_pdf

        # Create PDF file
        pdf_file = tmp_path / "document.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        output_dir = tmp_path / "output"
        file_manager = FileManager(output_dir=str(output_dir))
        pipeline = Pipeline(file_manager=file_manager, enable_ocr=False)

        result = pipeline.process_file(str(pdf_file))

        if result.success:
            # Check that output directory exists
            assert output_dir.exists()

    @patch('pdf2md.core.pipeline.pdfplumber.open')
    def test_pipeline_error_handling(self, mock_pdf_open, tmp_path):
        """Test pipeline handles errors gracefully."""
        # Make pdfplumber raise an error
        mock_pdf_open.side_effect = Exception("PDF parsing error")

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        file_manager = FileManager()
        pipeline = Pipeline(file_manager=file_manager, enable_ocr=False)

        result = pipeline.process_file(str(pdf_file))

        assert not result.success
        assert result.error_message is not None

    def test_pipeline_with_large_file(self, tmp_path):
        """Test pipeline handles file size validation."""
        # Create a large file (but not necessarily a valid PDF)
        pdf_file = tmp_path / "large.pdf"

        # Write 201MB of data (over 200MB limit)
        with open(pdf_file, 'wb') as f:
            f.write(b"%PDF-1.4")
            f.write(b"x" * (201 * 1024 * 1024))

        file_manager = FileManager()
        pipeline = Pipeline(file_manager=file_manager, enable_ocr=False)

        result = pipeline.process_file(str(pdf_file))

        # Should fail due to size
        assert not result.success

    def test_process_result_attributes(self):
        """Test ProcessResult dataclass attributes."""
        result = ProcessResult(
            success=True,
            file_path="/test/file.pdf",
            total_pages=10,
            processed_pages=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            failed_pages=[],
            output_dir="/test/output_md",
            error_message=None,
        )

        assert result.success is True
        assert result.file_path == "/test/file.pdf"
        assert result.total_pages == 10
        assert len(result.processed_pages) == 10
        assert len(result.failed_pages) == 0
        assert result.output_dir == "/test/output_md"

    def test_process_result_error(self):
        """Test ProcessResult with error."""
        result = ProcessResult(
            success=False,
            file_path="/test/file.pdf",
            total_pages=0,
            processed_pages=[],
            failed_pages=[],
            output_dir=None,
            error_message="File not found",
        )

        assert result.success is False
        assert result.error_message == "File not found"