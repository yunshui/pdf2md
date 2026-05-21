#!/usr/bin/env python3
"""pdf2md - Convert PDF and document files to Markdown via a remote conversion API.

This script accepts a PDF, DOCX, DOC, or TXT file or directory, sends them to a
remote conversion API, and saves the resulting Markdown output.
"""

import sys
import os
import json
import logging
import argparse
import base64
import time
import random
import string
import datetime
import glob
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
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
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
            bad_types.append(f"{key} (expected {expected_type.__name__}, got {type(config[key]).__name__})")
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

    for file_path in files:
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
            os.makedirs(output_dir, exist_ok=True)
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
        else:
            logger.error("API call failed for %s after all retries", filename)


if __name__ == "__main__":
    main()
