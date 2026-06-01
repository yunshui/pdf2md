"""Tests for pdf2md.py"""

import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pdf2md


@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a temporary directory for test file operations."""
    return str(tmp_path)


@pytest.fixture
def sample_config():
    """Provide a valid sample config."""
    return {
        "api_url": "http://example.com/file_parse",
        "client_id": "test-client",
        "max_retries": 2,
        "retry_delay": 0,
        "timeout": 5,
        "output_dir": "output",
        "log_dir": "logs",
        "page_num": 10,
        "summarize_api_url": "http://example.com/v1/chat/completions",
        "summarize_api_key": "test-key",
        "summarize_model": "gpt-4o",
        "summarize_timeout": 60,
        "summarize_prompt": "Summarize: {content}\n\nSummary:",
    }


@pytest.fixture
def sample_api_response():
    """Provide a valid sample API response."""
    return {
        "status": "completed",
        "results": {
            "0": {"md_content": "# Test Document\n\nThis is test content."},
        },
    }


# ============================================================
# load_config Tests
# ============================================================

class TestLoadConfig:
    """Tests for load_config function."""

    def test_creates_default_config_when_missing(self, tmp_dir):
        """When conf/setting.json is missing, it should be created with defaults."""
        config = pdf2md.load_config(tmp_dir)

        assert config == dict(pdf2md.DEFAULT_CONFIG)
        config_path = os.path.join(tmp_dir, "conf", "setting.json")
        assert os.path.isfile(config_path)

        # Verify the written config matches defaults
        with open(config_path, "r", encoding="utf-8") as f:
            written = json.load(f)
        assert written == pdf2md.DEFAULT_CONFIG

    def test_loads_existing_valid_config(self, tmp_dir):
        """Should load and return a valid config file."""
        os.makedirs(os.path.join(tmp_dir, "conf"), exist_ok=True)
        custom_config = dict(pdf2md.DEFAULT_CONFIG)
        custom_config["api_url"] = "http://custom.api.com"
        config_path = os.path.join(tmp_dir, "conf", "setting.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(custom_config, f)

        result = pdf2md.load_config(tmp_dir)
        assert result["api_url"] == "http://custom.api.com"

    def test_exits_on_invalid_json(self, tmp_dir, capsys):
        """Should exit with error message when config contains invalid JSON."""
        os.makedirs(os.path.join(tmp_dir, "conf"), exist_ok=True)
        config_path = os.path.join(tmp_dir, "conf", "setting.json")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json }")

        with pytest.raises(SystemExit) as exc_info:
            pdf2md.load_config(tmp_dir)
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error" in captured.err

    def test_exits_on_missing_keys(self, tmp_dir, capsys):
        """Should exit with error message when required keys are missing."""
        os.makedirs(os.path.join(tmp_dir, "conf"), exist_ok=True)
        config_path = os.path.join(tmp_dir, "conf", "setting.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"api_url": "http://test.com"}, f)

        with pytest.raises(SystemExit) as exc_info:
            pdf2md.load_config(tmp_dir)
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "missing required keys" in captured.err

    def test_exits_on_invalid_types(self, tmp_dir, capsys):
        """Should exit with error message when config values have wrong types."""
        os.makedirs(os.path.join(tmp_dir, "conf"), exist_ok=True)
        config_path = os.path.join(tmp_dir, "conf", "setting.json")
        config = dict(pdf2md.DEFAULT_CONFIG)
        config["max_retries"] = "three"  # Should be int
        config["timeout"] = None  # Should be int
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f)

        with pytest.raises(SystemExit) as exc_info:
            pdf2md.load_config(tmp_dir)
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "invalid value types" in captured.err

    def test_new_fields_in_default_config(self):
        """New config fields should be present in DEFAULT_CONFIG."""
        assert "page_num" in pdf2md.DEFAULT_CONFIG
        assert "summarize_api_url" in pdf2md.DEFAULT_CONFIG
        assert "summarize_api_key" in pdf2md.DEFAULT_CONFIG
        assert "summarize_model" in pdf2md.DEFAULT_CONFIG
        assert "summarize_timeout" in pdf2md.DEFAULT_CONFIG
        assert "summarize_prompt" in pdf2md.DEFAULT_CONFIG


# ============================================================
# resolve_files Tests
# ============================================================

class TestResolveFiles:
    """Tests for resolve_files function."""

    def test_single_supported_file(self, tmp_dir):
        """Should return a single-file list for a supported file."""
        file_path = os.path.join(tmp_dir, "test.pdf")
        with open(file_path, "wb") as f:
            f.write(b"test")

        logger = MagicMock()
        result = pdf2md.resolve_files(file_path, logger)
        assert result == [file_path]

    def test_unsupported_extension(self, tmp_dir):
        """Should return empty list and log warning for unsupported extensions."""
        file_path = os.path.join(tmp_dir, "test.json")
        with open(file_path, "wb") as f:
            f.write(b"test")

        logger = MagicMock()
        result = pdf2md.resolve_files(file_path, logger)
        assert result == []
        logger.warning.assert_called_once()

    def test_directory_with_multiple_files(self, tmp_dir):
        """Should find all supported files in a directory."""
        for name in ["a.pdf", "b.docx", "c.txt", "d.json"]:
            with open(os.path.join(tmp_dir, name), "wb") as f:
                f.write(b"test")

        logger = MagicMock()
        result = pdf2md.resolve_files(tmp_dir, logger)

        # Should find 3 files (not .json), sorted
        assert len(result) == 3
        assert result == sorted(result)

    def test_empty_directory(self, tmp_dir):
        """Should return empty list and log warning for empty directory."""
        logger = MagicMock()
        result = pdf2md.resolve_files(tmp_dir, logger)
        assert result == []
        logger.warning.assert_called_once()

    def test_case_insensitive_extension(self, tmp_dir):
        """Should handle uppercase extensions."""
        file_path = os.path.join(tmp_dir, "test.PDF")
        with open(file_path, "wb") as f:
            f.write(b"test")

        logger = MagicMock()
        result = pdf2md.resolve_files(file_path, logger)
        assert result == [file_path]


# ============================================================
# get_pdf_page_count Tests
# ============================================================

class TestGetPdfPageCount:
    """Tests for get_pdf_page_count function."""

    @patch("fitz.open")
    def test_returns_page_count(self, mock_open, tmp_dir):
        """Should return the number of pages from a valid PDF."""
        mock_doc = MagicMock()
        mock_doc.page_count = 10
        mock_open.return_value = mock_doc

        logger = MagicMock()
        result = pdf2md.get_pdf_page_count(os.path.join(tmp_dir, "test.pdf"), logger)
        assert result == 10
        mock_doc.close.assert_called_once()

    def test_returns_none_on_import_error(self, tmp_dir):
        """Should return None when PyMuPDF is not installed."""
        with patch.dict("sys.modules", {"fitz": None}):
            logger = MagicMock()
            result = pdf2md.get_pdf_page_count(os.path.join(tmp_dir, "test.pdf"), logger)
        assert result is None

    def test_returns_none_on_parse_failure(self, tmp_dir):
        """Should return None when PDF parsing fails."""
        with patch("fitz.open", side_effect=Exception("invalid PDF")):
            logger = MagicMock()
            result = pdf2md.get_pdf_page_count(os.path.join(tmp_dir, "test.pdf"), logger)
        assert result is None


# ============================================================
# call_file_parse_api Tests
# ============================================================

class TestCallFileParseApi:
    """Tests for call_file_parse_api function."""

    @patch("pdf2md.requests.post")
    def test_success_on_first_attempt(self, mock_post, sample_config, tmp_dir):
        """Should return response dict on successful 200 response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "completed", "results": {}}
        mock_post.return_value = mock_response

        # Create a test file
        test_file = os.path.join(tmp_dir, "test.pdf")
        with open(test_file, "wb") as f:
            f.write(b"test content")

        logger = MagicMock()
        result = pdf2md.call_file_parse_api(
            sample_config, logger, test_file, 0, 4, "test.pdf",
        )

        assert result is not None
        assert result["status"] == "completed"
        mock_post.assert_called_once()
        # Verify multipart form-data was used
        call_kwargs = mock_post.call_args[1]
        assert "files" in call_kwargs
        assert "data" in call_kwargs
        assert call_kwargs["data"]["start_page_id"] == "0"
        assert call_kwargs["data"]["end_page_id"] == "4"

    @patch("pdf2md.requests.post")
    def test_retries_on_non_200(self, mock_post, sample_config, tmp_dir):
        """Should retry on non-200 status codes."""
        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"status": "completed", "results": {}}
        mock_post.side_effect = [mock_response_500, mock_response_200]

        test_file = os.path.join(tmp_dir, "test.pdf")
        with open(test_file, "wb") as f:
            f.write(b"test")

        logger = MagicMock()
        result = pdf2md.call_file_parse_api(
            sample_config, logger, test_file, 0, 4, "test.pdf",
        )

        assert result is not None
        assert mock_post.call_count == 2

    @patch("pdf2md.requests.post")
    def test_returns_none_after_max_retries(self, mock_post, sample_config, tmp_dir):
        """Should return None after exhausting all retries."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        test_file = os.path.join(tmp_dir, "test.pdf")
        with open(test_file, "wb") as f:
            f.write(b"test")

        logger = MagicMock()
        result = pdf2md.call_file_parse_api(
            sample_config, logger, test_file, 0, 4, "test.pdf",
        )

        assert result is None
        assert mock_post.call_count == sample_config["max_retries"]

    @patch("pdf2md.requests.post")
    def test_no_retry_on_json_decode_error(self, mock_post, sample_config, tmp_dir):
        """Should not retry on JSON decode errors."""
        from requests.exceptions import JSONDecodeError
        mock_post.side_effect = JSONDecodeError("Bad JSON", MagicMock(), 0)

        test_file = os.path.join(tmp_dir, "test.pdf")
        with open(test_file, "wb") as f:
            f.write(b"test")

        logger = MagicMock()
        result = pdf2md.call_file_parse_api(
            sample_config, logger, test_file, 0, 4, "test.pdf",
        )

        assert result is None
        assert mock_post.call_count == 1

    @patch("pdf2md.requests.post")
    def test_retries_on_connection_error(self, mock_post, sample_config, tmp_dir):
        """Should retry on ConnectionError."""
        import requests.exceptions
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        test_file = os.path.join(tmp_dir, "test.pdf")
        with open(test_file, "wb") as f:
            f.write(b"test")

        logger = MagicMock()
        result = pdf2md.call_file_parse_api(
            sample_config, logger, test_file, 0, 4, "test.pdf",
        )

        assert result is None
        assert mock_post.call_count == sample_config["max_retries"]


# ============================================================
# call_summarize_api Tests
# ============================================================

class TestCallSummarizeApi:
    """Tests for call_summarize_api function."""

    @patch("pdf2md.requests.post")
    def test_success_returns_summary(self, mock_post, sample_config):
        """Should return summary text on successful response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "This is a summary."}}],
        }
        mock_post.return_value = mock_response

        logger = MagicMock()
        result = pdf2md.call_summarize_api(sample_config, logger, "chunk content")

        assert result == "This is a summary."
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["model"] == "gpt-4o"
        assert call_kwargs["json"]["messages"][0]["role"] == "user"

    @patch("pdf2md.requests.post")
    def test_empty_on_no_choices(self, mock_post, sample_config):
        """Should return empty string when response has no choices."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": []}
        mock_post.return_value = mock_response

        logger = MagicMock()
        result = pdf2md.call_summarize_api(sample_config, logger, "content")

        assert result == ""

    @patch("pdf2md.requests.post")
    def test_empty_on_http_error(self, mock_post, sample_config):
        """Should return empty string on HTTP error after retries."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        logger = MagicMock()
        result = pdf2md.call_summarize_api(sample_config, logger, "content")

        assert result == ""

    @patch("pdf2md.requests.post")
    def test_authorization_header_when_key_present(self, mock_post, sample_config):
        """Should include Authorization header when api_key is set."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "summary"}}],
        }
        mock_post.return_value = mock_response

        logger = MagicMock()
        pdf2md.call_summarize_api(sample_config, logger, "content")

        call_kwargs = mock_post.call_args[1]
        assert "Authorization" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Authorization"] == "Bearer test-key"

    @patch("pdf2md.requests.post")
    def test_no_authorization_header_when_key_empty(self, mock_post, sample_config):
        """Should not include Authorization header when api_key is empty."""
        sample_config["summarize_api_key"] = ""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "summary"}}],
        }
        mock_post.return_value = mock_response

        logger = MagicMock()
        pdf2md.call_summarize_api(sample_config, logger, "content")

        call_kwargs = mock_post.call_args[1]
        assert "Authorization" not in call_kwargs["headers"]

    @patch("pdf2md.requests.post")
    def test_retries_on_connection_error(self, mock_post, sample_config):
        """Should retry on connection errors."""
        import requests.exceptions
        mock_post.side_effect = requests.exceptions.ConnectionError("refused")

        logger = MagicMock()
        result = pdf2md.call_summarize_api(sample_config, logger, "content")

        assert result == ""
        assert mock_post.call_count == sample_config["max_retries"]


# ============================================================
# extract_md_content Tests
# ============================================================

class TestExtractMdContent:
    """Tests for extract_md_content function."""

    def test_extracts_single_result(self, sample_api_response):
        """Should extract markdown content from a single result."""
        result = pdf2md.extract_md_content(sample_api_response)
        assert len(result) == 1
        assert result[0] == ("0", "# Test Document\n\nThis is test content.")

    def test_extracts_multiple_results(self):
        """Should extract content from multiple results."""
        response = {
            "results": {
                "0": {"md_content": "# Page 1"},
                "1": {"md_content": "# Page 2"},
            }
        }
        result = pdf2md.extract_md_content(response)
        assert len(result) == 2

    def test_empty_results(self):
        """Should return empty list for empty results."""
        response = {"results": {}}
        result = pdf2md.extract_md_content(response)
        assert result == []

    def test_missing_results_key(self):
        """Should handle response without results key."""
        response = {"status": "completed"}
        result = pdf2md.extract_md_content(response)
        assert result == []

    def test_missing_md_content_key(self):
        """Should handle results missing md_content key."""
        response = {"results": {"0": {"other_field": "value"}}}
        result = pdf2md.extract_md_content(response)
        assert result == [("0", "")]

    def test_skips_non_dict_values(self):
        """Should skip result values that are not dicts."""
        response = {
            "results": {
                "0": {"md_content": "valid"},
                "1": "invalid_string",
                "2": None,
                "3": ["list"],
            }
        }
        result = pdf2md.extract_md_content(response)
        assert len(result) == 1
        assert result[0] == ("0", "valid")


# ============================================================
# get_unique_dir Tests
# ============================================================

class TestGetUniqueDir:
    """Tests for get_unique_dir function."""

    def test_returns_original_when_no_collision(self, tmp_dir):
        """Should return stem_name_md when directory does not exist."""
        result = pdf2md.get_unique_dir(tmp_dir, "report")
        assert result == os.path.join(tmp_dir, "report_md")

    def test_generates_suffix_on_collision(self, tmp_dir):
        """Should generate a unique path with suffix when directory exists."""
        existing = os.path.join(tmp_dir, "report_md")
        os.makedirs(existing)

        result = pdf2md.get_unique_dir(tmp_dir, "report")
        assert result != existing
        assert result.startswith(os.path.join(tmp_dir, "report_md_"))
        assert not os.path.exists(result)

    def test_generates_different_suffixes(self, tmp_dir):
        """Should generate different suffixes for multiple collisions."""
        base = os.path.join(tmp_dir, "report_md")
        os.makedirs(base)

        path1 = pdf2md.get_unique_dir(tmp_dir, "report")
        path2 = pdf2md.get_unique_dir(tmp_dir, "report")

        assert path1 != path2

    def test_suffix_is_5_lowercase_chars(self, tmp_dir):
        """The random suffix should be exactly 5 lowercase letters."""
        base = os.path.join(tmp_dir, "report_md")
        os.makedirs(base)

        result = pdf2md.get_unique_dir(tmp_dir, "report")
        basename = os.path.basename(result)
        suffix = basename.replace("report_md_", "")
        assert len(suffix) == 5
        assert suffix.islower()
        assert suffix.isalpha()


# ============================================================
# Integration Tests (main flow)
# ============================================================

class TestIntegration:
    """Integration tests for the full workflow."""

    @patch("pdf2md.requests.post")
    @patch("sys.argv", ["pdf2md.py"])
    def test_no_args_exits(self, mock_post):
        """Should show help and exit when no arguments provided."""
        with pytest.raises(SystemExit) as exc_info:
            pdf2md.main()
        # argparse exits with code 2 for missing required args
        assert exc_info.value.code == 2

    @patch("sys.argv", ["pdf2md.py", "/nonexistent/path"])
    def test_nonexistent_path_exits(self, capsys):
        """Should exit with code 1 for non-existent path."""
        with pytest.raises(SystemExit) as exc_info:
            pdf2md.main()
        assert exc_info.value.code == 1

    @patch("pdf2md.load_config")
    @patch("pdf2md.requests.post")
    def test_full_flow_with_api_success(self, mock_post, mock_load_config, tmp_dir):
        """Should complete full workflow: file -> parse API -> chunk files + summary."""
        # Create a test file
        test_file = os.path.join(tmp_dir, "test.txt")
        with open(test_file, "wb") as f:
            f.write(b"# Test PDF Content")

        # Setup config
        config = {
            "api_url": "http://example.com/file_parse",
            "client_id": "test",
            "max_retries": 1,
            "retry_delay": 0,
            "timeout": 5,
            "output_dir": os.path.join(tmp_dir, "output"),
            "log_dir": os.path.join(tmp_dir, "logs"),
            "page_num": 10,
            "summarize_api_url": "http://example.com/v1/chat/completions",
            "summarize_api_key": "test-key",
            "summarize_model": "gpt-4o",
            "summarize_timeout": 60,
            "summarize_prompt": "Summarize: {content}\n\nSummary:",
        }
        mock_load_config.return_value = config

        # Mock file_parse API response (first call returns content)
        parse_response_1 = MagicMock()
        parse_response_1.status_code = 200
        parse_response_1.json.return_value = {
            "status": "completed",
            "results": {"0": {"md_content": "# Test Document\n\nThis is test content."}},
        }

        # Second call returns empty results (end of document)
        parse_response_2 = MagicMock()
        parse_response_2.status_code = 200
        parse_response_2.json.return_value = {
            "status": "completed",
            "results": {},
        }

        # Mock summarize API response
        summarize_response = MagicMock()
        summarize_response.status_code = 200
        summarize_response.json.return_value = {
            "choices": [{"message": {"content": "This is a test summary."}}],
        }

        mock_post.side_effect = [parse_response_1, summarize_response, parse_response_2]

        # Run with mocked argv
        with patch("sys.argv", ["pdf2md.py", test_file]):
            with pytest.raises(SystemExit) as exc_info:
                pdf2md.main()
            assert exc_info.value.code == 0  # Success

        # Verify output directory structure
        output_dir = config["output_dir"]
        file_output_dir = os.path.join(output_dir, "test_md")
        assert os.path.isdir(file_output_dir)

        # Verify chunk file was created
        chunk_file = os.path.join(file_output_dir, "test_0-9.md")
        assert os.path.isfile(chunk_file)

        with open(chunk_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert "# Test Document" in content

        # Verify summary file was created
        summary_file = os.path.join(file_output_dir, "test.md")
        assert os.path.isfile(summary_file)

        with open(summary_file, "r", encoding="utf-8") as f:
            summary_content = f.read()
        assert "# test Summary" in summary_content
        assert "This is a test summary." in summary_content
        assert "test_0-9.md" in summary_content

    @patch("pdf2md.load_config")
    @patch("pdf2md.requests.post")
    def test_full_flow_with_api_failure(self, mock_post, mock_load_config, tmp_dir):
        """Should exit with code 1 when API call fails."""
        test_file = os.path.join(tmp_dir, "test.txt")
        with open(test_file, "wb") as f:
            f.write(b"test content")

        # Setup config
        config = {
            "api_url": "http://example.com/file_parse",
            "client_id": "test",
            "max_retries": 1,
            "retry_delay": 0,
            "timeout": 5,
            "output_dir": os.path.join(tmp_dir, "output"),
            "log_dir": os.path.join(tmp_dir, "logs"),
            "page_num": 10,
            "summarize_api_url": "http://example.com/v1/chat/completions",
            "summarize_api_key": "test-key",
            "summarize_model": "gpt-4o",
            "summarize_timeout": 60,
            "summarize_prompt": "Summarize: {content}\n\nSummary:",
        }
        mock_load_config.return_value = config

        # Mock API failure
        import requests.exceptions
        mock_post.side_effect = requests.exceptions.ConnectionError("refused")

        with patch("sys.argv", ["pdf2md.py", test_file]):
            with pytest.raises(SystemExit) as exc_info:
                pdf2md.main()
            assert exc_info.value.code == 1  # Failure

    @patch("pdf2md.load_config")
    @patch("pdf2md.requests.post")
    def test_pagination_creates_multiple_chunks(self, mock_post, mock_load_config, tmp_dir):
        """Should create multiple chunk files when document spans multiple page ranges."""
        test_file = os.path.join(tmp_dir, "report.txt")
        with open(test_file, "wb") as f:
            f.write(b"Page content")

        config = {
            "api_url": "http://example.com/file_parse",
            "client_id": "test",
            "max_retries": 1,
            "retry_delay": 0,
            "timeout": 5,
            "output_dir": os.path.join(tmp_dir, "output"),
            "log_dir": os.path.join(tmp_dir, "logs"),
            "page_num": 10,  # 10 pages per chunk
            "summarize_api_url": "http://example.com/v1/chat/completions",
            "summarize_api_key": "test-key",
            "summarize_model": "gpt-4o",
            "summarize_timeout": 60,
            "summarize_prompt": "Summarize: {content}\n\nSummary:",
        }
        mock_load_config.return_value = config

        # Simulate: first call returns content, second call returns empty results (end of doc)
        parse_response_1 = MagicMock()
        parse_response_1.status_code = 200
        parse_response_1.json.return_value = {
            "status": "completed",
            "results": {"0": {"md_content": "# Pages 0-9"}},
        }

        parse_response_2 = MagicMock()
        parse_response_2.status_code = 200
        parse_response_2.json.return_value = {
            "status": "completed",
            "results": {"0": {"md_content": "# Pages 10-19"}},
        }

        parse_response_3 = MagicMock()
        parse_response_3.status_code = 200
        parse_response_3.json.return_value = {
            "status": "completed",
            "results": {},  # Empty results = no more content
        }

        summarize_response_1 = MagicMock()
        summarize_response_1.status_code = 200
        summarize_response_1.json.return_value = {
            "choices": [{"message": {"content": "Summary of pages 0-9."}}],
        }

        summarize_response_2 = MagicMock()
        summarize_response_2.status_code = 200
        summarize_response_2.json.return_value = {
            "choices": [{"message": {"content": "Summary of pages 10-19."}}],
        }

        mock_post.side_effect = [
            parse_response_1, summarize_response_1,
            parse_response_2, summarize_response_2,
            parse_response_3,
        ]

        with patch("sys.argv", ["pdf2md.py", test_file]):
            with pytest.raises(SystemExit) as exc_info:
                pdf2md.main()
            assert exc_info.value.code == 0

        # Verify both chunk files exist
        output_dir = config["output_dir"]
        file_output_dir = os.path.join(output_dir, "report_md")

        chunk1 = os.path.join(file_output_dir, "report_0-9.md")
        chunk2 = os.path.join(file_output_dir, "report_10-19.md")
        assert os.path.isfile(chunk1)
        assert os.path.isfile(chunk2)

        # Verify summary references both chunks
        summary_file = os.path.join(file_output_dir, "report.md")
        with open(summary_file, "r", encoding="utf-8") as f:
            summary_content = f.read()
        assert "report_0-9.md" in summary_content
        assert "report_10-19.md" in summary_content
