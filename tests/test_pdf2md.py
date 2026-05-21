"""Tests for pdf2md.py"""

import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

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
        "api_url": "http://example.com/convert2markdown",
        "client_id": "test-client",
        "max_retries": 2,
        "retry_delay": 0,
        "timeout": 5,
        "output_dir": "output",
        "log_dir": "logs",
    }


@pytest.fixture
def sample_api_response():
    """Provide a valid sample API response."""
    return {
        "task_id": "test-uuid",
        "status": "completed",
        "backend": "test-engine",
        "file_names": ["file_0"],
        "version": "1.0.0",
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
# file_to_base64 Tests
# ============================================================

class TestFileToBase64:
    """Tests for file_to_base64 function."""

    def test_encodes_file_correctly(self, tmp_dir):
        """Should return base64-encoded content of the file."""
        original = b"Hello, World!"
        file_path = os.path.join(tmp_dir, "test.txt")
        with open(file_path, "wb") as f:
            f.write(original)

        import base64
        expected = base64.b64encode(original).decode("ascii")
        result = pdf2md.file_to_base64(file_path)
        assert result == expected

    def test_raises_on_missing_file(self):
        """Should raise OSError when file does not exist."""
        with pytest.raises(OSError):
            pdf2md.file_to_base64("/nonexistent/file.pdf")

    def test_empty_file(self, tmp_dir):
        """Should handle empty files correctly."""
        file_path = os.path.join(tmp_dir, "empty.txt")
        with open(file_path, "wb") as f:
            pass

        result = pdf2md.file_to_base64(file_path)
        assert result == ""


# ============================================================
# call_api Tests
# ============================================================

class TestCallApi:
    """Tests for call_api function."""

    @patch("pdf2md.requests.post")
    def test_success_on_first_attempt(self, mock_post, sample_config):
        """Should return response dict on successful 200 response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "completed", "results": {}}
        mock_post.return_value = mock_response

        logger = MagicMock()
        result = pdf2md.call_api(
            sample_config, logger, "base64data", "test.pdf"
        )

        assert result is not None
        assert result["status"] == "completed"
        mock_post.assert_called_once()

    @patch("pdf2md.requests.post")
    def test_retries_on_non_200(self, mock_post, sample_config):
        """Should retry on non-200 status codes."""
        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"status": "completed", "results": {}}
        mock_post.side_effect = [mock_response_500, mock_response_200]

        logger = MagicMock()
        result = pdf2md.call_api(
            sample_config, logger, "base64data", "test.pdf"
        )

        assert result is not None
        assert mock_post.call_count == 2

    @patch("pdf2md.requests.post")
    def test_returns_none_after_max_retries(self, mock_post, sample_config):
        """Should return None after exhausting all retries."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        logger = MagicMock()
        result = pdf2md.call_api(
            sample_config, logger, "base64data", "test.pdf"
        )

        assert result is None
        assert mock_post.call_count == sample_config["max_retries"]

    @patch("pdf2md.requests.post")
    def test_no_retry_on_json_decode_error(self, mock_post, sample_config):
        """Should not retry on JSON decode errors."""
        from requests.exceptions import JSONDecodeError
        mock_post.side_effect = JSONDecodeError("Bad JSON", MagicMock(), 0)

        logger = MagicMock()
        result = pdf2md.call_api(
            sample_config, logger, "base64data", "test.pdf"
        )

        assert result is None
        assert mock_post.call_count == 1  # Only one attempt, no retry

    @patch("pdf2md.requests.post")
    def test_retries_on_connection_error(self, mock_post, sample_config):
        """Should retry on ConnectionError."""
        import requests.exceptions
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        logger = MagicMock()
        result = pdf2md.call_api(
            sample_config, logger, "base64data", "test.pdf"
        )

        assert result is None
        assert mock_post.call_count == sample_config["max_retries"]

    @patch("pdf2md.requests.post")
    def test_retries_on_timeout(self, mock_post, sample_config):
        """Should retry on Timeout."""
        import requests.exceptions
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        logger = MagicMock()
        result = pdf2md.call_api(
            sample_config, logger, "base64data", "test.pdf"
        )

        assert result is None
        assert mock_post.call_count == sample_config["max_retries"]

    @patch("pdf2md.requests.post")
    def test_logs_attempt_number(self, mock_post, sample_config):
        """Should log the attempt number."""
        import requests.exceptions
        mock_post.side_effect = requests.exceptions.ConnectionError("refused")

        logger = MagicMock()
        pdf2md.call_api(sample_config, logger, "data", "test.pdf")

        # Check that log calls include attempt numbers
        info_calls = [c[0][0] for c in logger.info.call_args_list]
        assert any("attempt" in msg for msg in info_calls)


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
# get_unique_path Tests
# ============================================================

class TestGetUniquePath:
    """Tests for get_unique_path function."""

    def test_returns_original_when_no_collision(self, tmp_dir):
        """Should return base_name.md when file does not exist."""
        result = pdf2md.get_unique_path(tmp_dir, "report")
        assert result == os.path.join(tmp_dir, "report.md")

    def test_generates_suffix_on_collision(self, tmp_dir):
        """Should generate a unique path with suffix when file exists."""
        existing = os.path.join(tmp_dir, "report.md")
        with open(existing, "w") as f:
            f.write("existing")

        result = pdf2md.get_unique_path(tmp_dir, "report")
        assert result != existing
        assert result.startswith(os.path.join(tmp_dir, "report_"))
        assert result.endswith(".md")
        assert not os.path.exists(result)

    def test_generates_different_suffixes(self, tmp_dir):
        """Should generate different suffixes for multiple collisions."""
        base = os.path.join(tmp_dir, "report.md")
        with open(base, "w") as f:
            f.write("base")

        path1 = pdf2md.get_unique_path(tmp_dir, "report")
        path2 = pdf2md.get_unique_path(tmp_dir, "report")

        assert path1 != path2

    def test_suffix_is_5_lowercase_chars(self, tmp_dir):
        """The random suffix should be exactly 5 lowercase letters."""
        base = os.path.join(tmp_dir, "report.md")
        with open(base, "w") as f:
            f.write("base")

        result = pdf2md.get_unique_path(tmp_dir, "report")
        basename = os.path.basename(result)
        # Format: report_XXXXX.md
        suffix = basename.replace("report_", "").replace(".md", "")
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
    def test_full_flow_with_api_success(self, mock_post, mock_load_config, tmp_dir, sample_api_response):
        """Should complete full workflow: file -> base64 -> API -> write output."""
        # Create a test file
        test_file = os.path.join(tmp_dir, "test.txt")
        with open(test_file, "wb") as f:
            f.write(b"# Test PDF Content")

        # Setup config to be returned by mocked load_config
        config = {
            "api_url": "http://example.com/convert",
            "client_id": "test",
            "max_retries": 1,
            "retry_delay": 0,
            "timeout": 5,
            "output_dir": os.path.join(tmp_dir, "output"),
            "log_dir": os.path.join(tmp_dir, "logs"),
        }
        mock_load_config.return_value = config

        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_api_response
        mock_post.return_value = mock_response

        # Run with mocked argv
        with patch("sys.argv", ["pdf2md.py", test_file]):
            with pytest.raises(SystemExit) as exc_info:
                pdf2md.main()
            assert exc_info.value.code == 0  # Success

        # Verify output file was created
        output_dir = config["output_dir"]
        output_file = os.path.join(output_dir, "test.md")
        assert os.path.isfile(output_file)

        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert "# Test Document" in content

    @patch("pdf2md.load_config")
    @patch("pdf2md.requests.post")
    def test_full_flow_with_api_failure(self, mock_post, mock_load_config, tmp_dir):
        """Should exit with code 1 when API call fails."""
        test_file = os.path.join(tmp_dir, "test.txt")
        with open(test_file, "wb") as f:
            f.write(b"test content")

        # Setup config to be returned by mocked load_config
        config = {
            "api_url": "http://example.com/convert",
            "client_id": "test",
            "max_retries": 1,
            "retry_delay": 0,
            "timeout": 5,
            "output_dir": os.path.join(tmp_dir, "output"),
            "log_dir": os.path.join(tmp_dir, "logs"),
        }
        mock_load_config.return_value = config

        # Mock API failure
        import requests.exceptions
        mock_post.side_effect = requests.exceptions.ConnectionError("refused")

        with patch("sys.argv", ["pdf2md.py", test_file]):
            with pytest.raises(SystemExit) as exc_info:
                pdf2md.main()
            assert exc_info.value.code == 1  # Failure

        # No markdown output files should be created
        output_dir = config["output_dir"]
        md_files = [f for f in os.listdir(output_dir) if f.endswith(".md")] if os.path.exists(output_dir) else []
        assert len(md_files) == 0
