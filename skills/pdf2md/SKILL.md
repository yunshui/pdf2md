# pdf2md - PDF/Document to Markdown Converter

**Type**: CLI tool skill (portable, self-contained)
**Trigger**: When user needs to convert PDF, DOCX, DOC, or TXT files to Markdown
**Purpose**: Provide complete source code, tests, and usage guide for the pdf2md CLI tool — runnable anywhere without needing the original repo

---

## How to Use

Invoke this skill when:
- A user wants to convert a document to Markdown on a machine without this tool
- Working on or modifying the pdf2md codebase
- Debugging conversion failures
- Adding new features or tests to the project

---

## Quick Deploy

To set up pdf2md on a new machine, create these files in a directory:

1. `pdf2md.py` — the main script (source code below)
2. `requirements.txt` — runtime dependencies
3. `requirements-dev.txt` — dev dependencies (optional, for running tests)
4. `tests/test_pdf2md.py` — test suite (optional, for verification)

Then:

```bash
pip install -r requirements.txt
python pdf2md.py <file_or_directory_path>
```

---

## Complete Source Code

### pdf2md.py

```python
#!/usr/bin/env python3
"""pdf2md - Convert PDF and document files to Markdown via a remote conversion API.

This script accepts a PDF, DOCX, DOC, or TXT file or directory, sends them to a
remote conversion API, and saves the resulting Markdown output.
"""

import argparse
import base64
import datetime
import glob
import json
import logging
import os
import random
import string
import sys
import time

import requests


DEFAULT_CONFIG = {
    "api_url": "http://123.192.49.73:8000/convert2markdown",
    "client_id": "bf-mkd",
    "max_retries": 3,
    "retry_delay": 2,
    "timeout": 120,
    "output_dir": "output",
    "log_dir": "logs",
}

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}


def resolve_files(path, logger):
    """Resolve a path to a list of files with supported extensions.

    If path is a file with a supported extension, return it in a list.
    If path is a file with an unsupported extension, log a warning and
    return an empty list.
    If path is a directory, glob for supported extensions and return a
    sorted list of matching files.

    Args:
        path: A file or directory path string.
        logger: A logging.Logger instance.

    Returns:
        list: A list of resolved file paths (possibly empty).
    """
    if os.path.isfile(path):
        ext = os.path.splitext(path)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            return [path]
        logger.warning(
            "File has unsupported extension '%s': %s", ext, path
        )
        return []

    if os.path.isdir(path):
        patterns = [os.path.join(path, f"*{ext}") for ext in SUPPORTED_EXTENSIONS]
        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern))
        files = sorted(set(files))
        if not files:
            logger.warning("No supported files found in directory: %s", path)
        return files

    logger.warning("Path is neither a file nor a directory: %s", path)
    return []


def file_to_base64(file_path):
    """Read a file and return its base64-encoded content.

    Args:
        file_path: Path to the file to encode.

    Returns:
        str: The base64-encoded content of the file.

    Raises:
        OSError: If the file cannot be read.
    """
    with open(file_path, "rb") as f:
        content = f.read()
    return base64.b64encode(content).decode("ascii")


def call_api(config, logger, base64_content, file_name):
    """POST file to conversion API with retry. Returns response dict or None on failure."""
    url = config["api_url"]
    headers = {
        "client_id": config["client_id"],
        "Content-Type": "application/json",
    }
    body = {"files": [base64_content]}
    max_retries = config["max_retries"]
    timeout = config["timeout"]

    for attempt in range(1, max_retries + 1):
        logger.info("Calling API for %s (attempt %d/%d)", file_name, attempt, max_retries)
        start = time.time()
        try:
            resp = requests.post(url, json=body, headers=headers, timeout=timeout)
            elapsed = time.time() - start

            if resp.status_code != 200:
                logger.error("HTTP %d after %.1fs (attempt %d)", resp.status_code, elapsed, attempt)
                if attempt < max_retries:
                    time.sleep(config["retry_delay"])
                    continue
                return None

            data = resp.json()
            logger.info("API response in %.1fs, status=%s", elapsed, data.get("status"))
            return data

        except (requests.exceptions.JSONDecodeError, ValueError):
            elapsed = time.time() - start
            logger.error("Invalid JSON response after %.1fs (no retry)", elapsed)
            return None
        except requests.exceptions.RequestException as e:
            elapsed = time.time() - start
            logger.error("Request failed after %.1fs: %s (attempt %d)", elapsed, e, attempt)
            if attempt < max_retries:
                time.sleep(config["retry_delay"])
                continue
            return None

    return None


def extract_md_content(response_data):
    """Extract markdown content from API response. Returns list of (index, content) tuples."""
    results = response_data.get("results", {})
    items = []
    for key, val in results.items():
        if not isinstance(val, dict):
            continue
        content = val.get("md_content", "")
        items.append((key, content))
    return items


def get_unique_path(output_dir, base_name):
    """Return unique file path. If file exists, append _<5 random chars> and retry on collision."""
    path = os.path.join(output_dir, f"{base_name}.md")
    if not os.path.exists(path):
        return path
    chars = string.ascii_lowercase
    while os.path.exists(path):
        suffix = ''.join(random.choice(chars) for _ in range(5))
        path = os.path.join(output_dir, f"{base_name}_{suffix}.md")
    return path


def load_config(script_dir):
    """Load configuration from conf/setting.json relative to script location.

    If the config file is missing, create it with default values.
    If the config file contains invalid JSON or is missing required keys,
    print an error and exit.

    Args:
        script_dir: The directory where this script resides.

    Returns:
        dict: The loaded configuration.
    """
    config_dir = os.path.join(script_dir, "conf")
    config_path = os.path.join(config_dir, "setting.json")

    if not os.path.isfile(config_path):
        # Config file is missing; create it with defaults.
        os.makedirs(config_dir, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return dict(DEFAULT_CONFIG)

    # Config file exists; parse it.
    with open(config_path, "r", encoding="utf-8") as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse config file {config_path}: {e}", file=sys.stderr)
            sys.exit(1)

    # Validate required keys.
    missing_keys = [key for key in DEFAULT_CONFIG if key not in config]
    if missing_keys:
        print(
            f"Error: Config file {config_path} is missing required keys: "
            f"{', '.join(missing_keys)}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate value types.
    type_checks = {
        "api_url": str,
        "client_id": str,
        "max_retries": int,
        "retry_delay": (int, float),
        "timeout": (int, float),
        "output_dir": str,
        "log_dir": str,
    }
    bad_types = []
    for key, expected_type in type_checks.items():
        if not isinstance(config[key], expected_type):
            type_name = '/'.join(t.__name__ for t in expected_type) if isinstance(expected_type, tuple) else expected_type.__name__
            bad_types.append(f"{key} (expected {type_name}, got {type(config[key]).__name__})")
    if bad_types:
        print(
            f"Error: Config file {config_path} has invalid value types: "
            f"{', '.join(bad_types)}",
            file=sys.stderr,
        )
        sys.exit(1)

    return config


def setup_logging(log_dir):
    """Set up file and console logging.

    Creates the log directory if it does not exist.
    The log file is named pdf2md-YYYYMMDD.log.

    Args:
        log_dir: Directory where log files will be stored.

    Returns:
        logging.Logger: Configured logger instance.
    """
    os.makedirs(log_dir, exist_ok=True)

    today = datetime.datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(log_dir, f"pdf2md-{today}.log")

    logger = logging.getLogger("pdf2md")
    if logger.handlers:
        logger.handlers.clear()
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-5s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def main():
    """Entry point: parse arguments, load config, set up logging, and run."""
    parser = argparse.ArgumentParser(
        description="Convert PDF, DOCX, DOC, and TXT files to Markdown via a remote conversion API.",
    )
    parser.add_argument(
        "path",
        help="Path to a PDF/DOCX/DOC/TXT file or directory containing such files.",
    )
    args = parser.parse_args()

    # Validate that the provided path exists.
    if not os.path.exists(args.path):
        print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
        sys.exit(1)

    # Resolve the script directory (directory containing this file).
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Load configuration.
    config = load_config(script_dir)

    # Resolve relative paths (log_dir, output_dir) to script directory.
    for key in ("log_dir", "output_dir"):
        if not os.path.isabs(config[key]):
            config[key] = os.path.join(script_dir, config[key])

    # Set up logging.
    logger = setup_logging(config["log_dir"])

    logger.info("pdf2md started. Config loaded from conf/setting.json")
    logger.debug("Configuration: %s", json.dumps(config))

    # Resolve files and encode them in base64.
    logger.info("Processing path: %s", args.path)
    files = resolve_files(args.path, logger)
    logger.info("Found %d file(s) to process.", len(files))
    if not files:
        logger.error("No files to process. Exiting.")
        sys.exit(1)

    # Create output directory if needed.
    os.makedirs(config["output_dir"], exist_ok=True)

    success_count = 0
    failure_count = 0

    for file_path in files:
        file_ok = True
        try:
            file_size = os.path.getsize(file_path)
            encoded = file_to_base64(file_path)
            logger.info(
                "Encoded %s (%d bytes, base64 size: %d).",
                file_path,
                file_size,
                len(encoded),
            )
        except OSError as e:
            logger.error("Failed to read file %s: %s", file_path, e)
            failure_count += 1
            continue

        # Call the conversion API with retry logic.
        filename = os.path.basename(file_path)
        result = call_api(config, logger, encoded, filename)
        if result is not None:
            logger.info("API call succeeded for %s", filename)
            stem_name = os.path.splitext(filename)[0]
            md_items = extract_md_content(result)
            if not md_items:
                logger.warning("API returned no markdown content for %s", filename)
            output_dir = config["output_dir"]
            for index, md_content in md_items:
                try:
                    out_path = get_unique_path(output_dir, stem_name)
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(md_content)
                    out_size = os.path.getsize(out_path)
                    out_basename = os.path.basename(out_path)
                    logger.info(
                        "Wrote output %s (%d bytes) for %s (index %s)",
                        out_basename, out_size, filename, index,
                    )
                except OSError as e:
                    logger.error("Failed to write output for %s (index %s): %s", filename, index, e)
                    file_ok = False
        else:
            logger.error("API call failed for %s after all retries", filename)
            file_ok = False

        if file_ok:
            success_count += 1
        else:
            failure_count += 1

    # Log summary and exit with appropriate code.
    total = success_count + failure_count
    logger.info("Processed %d files: %d success, %d failed", total, success_count, failure_count)
    if failure_count > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
```

### requirements.txt

```
requests>=2.28.0
```

### requirements-dev.txt

```
pytest>=7.0.0
```

### tests/test_pdf2md.py

```python
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
```

---

## Configuration

File: `conf/setting.json` (created with defaults if missing)

| Field | Default | Description |
|-------|---------|-------------|
| `api_url` | `http://123.192.49.73:8000/convert2markdown` | API endpoint |
| `client_id` | `bf-mkd` | API client identifier header |
| `max_retries` | `3` | Max retry attempts on failure |
| `retry_delay` | `2` | Seconds between retries |
| `timeout` | `120` | Request timeout in seconds |
| `output_dir` | `output` | Output directory for `.md` files |
| `log_dir` | `logs` | Log directory |

**Notes:**
- Relative `output_dir` and `log_dir` are resolved relative to the script directory
- Missing keys or invalid types cause exit with error message on stderr

---

## API Contract

- **Request**: `POST {api_url}` with header `client_id: {client_id}`, body `{"files": [base64_string]}`
- **Response**: JSON with `status`, `results` dict containing `md_content` per item

### Response format

```json
{
  "task_id": "uuid",
  "status": "completed",
  "results": {
    "0": { "md_content": "# Markdown content here" }
  }
}
```

---

## Error Scenarios

| Scenario | Behavior |
|----------|----------|
| Path does not exist | Print error to stderr, exit 1 |
| Unsupported file extension | Log warning, skip file |
| Empty directory | Log warning, exit 1 |
| Config missing | Auto-create with defaults |
| Config invalid JSON | Print error, exit 1 |
| Config missing keys | Print error, exit 1 |
| Config wrong types | Print error, exit 1 |
| API non-200 | Retry up to `max_retries`, then skip file |
| API timeout | Retry up to `max_retries`, then skip file |
| API connection error | Retry up to `max_retries`, then skip file |
| API JSON error | No retry, skip file immediately |
| Output file collision | Append `_XXXXX` (5 random lowercase chars) |

---

## Verification

```bash
python3 -m pytest tests/test_pdf2md.py -v
```

Expected: **34 tests passed** covering load_config, resolve_files, file_to_base64, call_api, extract_md_content, get_unique_path, and integration flows.
