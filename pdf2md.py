#!/usr/bin/env python3
"""pdf2md - Convert PDF and document files to Markdown via a remote conversion API.

This script accepts a PDF, DOCX, DOC, or TXT file or directory, sends them to
a remote conversion API, and saves the resulting Markdown output.
"""

import argparse
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


def get_pdf_page_count(file_path, logger):
    """Get total page count from a PDF file using PyMuPDF. Returns int or None on failure."""
    try:
        import fitz
        doc = fitz.open(file_path)
        page_count = doc.page_count
        doc.close()
        logger.info("PDF page count for %s: %d", os.path.basename(file_path), page_count)
        return page_count
    except ImportError:
        logger.warning("PyMuPDF not installed, cannot determine PDF page count")
        return None
    except Exception as e:
        logger.warning("Failed to read PDF page count: %s", e)
        return None


DEFAULT_CONFIG = {
    "api_url": "http://123.192.49.73:8000/file_parse",
    "client_id": "bf-mkd",
    "max_retries": 3,
    "retry_delay": 2,
    "timeout": 120,
    "output_dir": "output",
    "log_dir": "logs",
    "page_num": 10,
    "summarize_api_url": "http://123.192.49.9:8086/v1/chat/completions",
    "summarize_api_key": "123",
    "summarize_model": "qwen3.5",
    "summarize_timeout": 200,
    "summarize_prompt": (
        "You are a document summarization assistant. Given the following markdown "
        "content, create a concise summary (within 500 words). Include key points "
        "and important details.\n\n{content}\n\nSummary:"
    ),
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


def call_file_parse_api(config, logger, file_path, start_page, end_page, file_name):
    """POST file to file_parse API with page range. Returns response dict or None on failure."""
    url = config["api_url"]
    headers = {"client_id": config["client_id"]}
    max_retries = config["max_retries"]
    timeout = config["timeout"]

    for attempt in range(1, max_retries + 1):
        logger.info(
            "Calling API for %s pages %d-%d (attempt %d/%d)",
            file_name, start_page, end_page, attempt, max_retries,
        )
        start = time.time()
        try:
            with open(file_path, "rb") as f:
                files = {"files": (file_name, f, "application/octet-stream")}
                data = {
                    "start_page_id": str(start_page),
                    "end_page_id": str(end_page),
                }
                resp = requests.post(
                    url, files=files, data=data, headers=headers, timeout=timeout,
                )
            elapsed = time.time() - start

            if resp.status_code != 200:
                logger.error("HTTP %d after %.1fs (attempt %d)", resp.status_code, elapsed, attempt)
                if attempt < max_retries:
                    time.sleep(config["retry_delay"])
                    continue
                return None

            resp_data = resp.json()
            logger.info("API response in %.1fs, status=%s", elapsed, resp_data.get("status"))
            return resp_data

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


def call_summarize_api(config, logger, content):
    """Call LLM summarization API for a single chunk. Returns summary text or empty string on failure."""
    url = config["summarize_api_url"]
    api_key = config["summarize_api_key"]
    model = config["summarize_model"]
    prompt_template = config["summarize_prompt"]
    max_retries = config["max_retries"]
    timeout = config["timeout"]
    summarize_timeout = config.get("summarize_timeout", 200)

    prompt = prompt_template.format(content=content)
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    for attempt in range(1, max_retries + 1):
        logger.info("Calling summarize API (attempt %d/%d)", attempt, max_retries)
        try:
            resp = requests.post(url, json=body, headers=headers, timeout=summarize_timeout)
            if resp.status_code != 200:
                logger.error("Summarize API HTTP %d (attempt %d)", resp.status_code, attempt)
                if attempt < max_retries:
                    time.sleep(config["retry_delay"])
                    continue
                return ""

            data = resp.json()
            # OpenAI-compatible: choices[0].message.content
            choices = data.get("choices", [])
            if choices:
                summary = choices[0].get("message", {}).get("content", "")
                logger.info("Summarize API returned %d chars", len(summary))
                return summary
            logger.error("Summarize API returned no choices")
            return ""

        except (requests.exceptions.JSONDecodeError, ValueError):
            logger.error("Invalid JSON from summarize API (no retry)")
            return ""
        except requests.exceptions.RequestException as e:
            logger.error("Summarize API request failed: %s (attempt %d)", e, attempt)
            if attempt < max_retries:
                time.sleep(config["retry_delay"])
                continue
            return ""

    return ""


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


def get_unique_dir(parent_dir, stem_name):
    """Return unique directory path. If exists, append _<5 random chars> and retry on collision."""
    dir_path = os.path.join(parent_dir, f"{stem_name}_md")
    if not os.path.exists(dir_path):
        return dir_path
    chars = string.ascii_lowercase
    while os.path.exists(dir_path):
        suffix = ''.join(random.choice(chars) for _ in range(5))
        dir_path = os.path.join(parent_dir, f"{stem_name}_md_{suffix}")
    return dir_path


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
        "page_num": int,
        "summarize_api_url": str,
        "summarize_api_key": str,
        "summarize_model": str,
        "summarize_timeout": (int, float),
        "summarize_prompt": str,
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

    # Resolve files.
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
        filename = os.path.basename(file_path)
        stem_name = os.path.splitext(filename)[0]
        page_num = config["page_num"]

        try:
            file_size = os.path.getsize(file_path)
            logger.info("Processing %s (%d bytes)", file_path, file_size)
        except OSError as e:
            logger.error("Failed to read file %s: %s", file_path, e)
            failure_count += 1
            continue

        # Create per-file output directory: {output_dir}/{stem_name}_md/
        file_output_dir = get_unique_dir(config["output_dir"], stem_name)
        os.makedirs(file_output_dir, exist_ok=True)
        logger.info("Output directory: %s", file_output_dir)

        # Paginated API calls
        chunk_ranges = []  # List of (start, end, chunk_file, summary)
        start_page = 0

        # For PDF files, get total page count to determine when to stop
        total_pages = None
        if os.path.splitext(filename)[1].lower() == ".pdf":
            total_pages = get_pdf_page_count(file_path, logger)

        while True:
            # If we know total pages, clamp end_page and check termination
            if total_pages is not None and start_page >= total_pages:
                logger.info("Reached end of PDF (%d pages) for %s", total_pages, filename)
                break

            end_page = start_page + page_num - 1
            if total_pages is not None and end_page >= total_pages:
                end_page = total_pages - 1

            result = call_file_parse_api(
                config, logger, file_path, start_page, end_page, filename,
            )
            if result is None:
                logger.error("API call failed for %s pages %d-%d", filename, start_page, end_page)
                file_ok = False
                break

            md_items = extract_md_content(result)
            if not md_items:
                logger.info(
                    "No more content from API for %s at pages %d-%d; stopping pagination.",
                    filename, start_page, end_page,
                )
                break

            # Write chunk file: {stem_name}_{start}-{end}.md
            chunk_basename = f"{stem_name}_{start_page}-{end_page}"
            out_path = os.path.join(file_output_dir, f"{chunk_basename}.md")
            chunk_md = md_items[0][1] if md_items else ""
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(chunk_md)
                out_size = os.path.getsize(out_path)
                logger.info(
                    "Wrote output %s (%d bytes) for %s",
                    os.path.basename(out_path), out_size, filename,
                )
            except OSError as e:
                logger.error("Failed to write output for %s: %s", filename, e)
                file_ok = False
                break

            chunk_file = f"{chunk_basename}.md"

            # Summarize this chunk separately
            summary_text = call_summarize_api(config, logger, chunk_md)

            chunk_ranges.append((start_page, end_page, chunk_file, summary_text))
            start_page = end_page + 1

        if not file_ok:
            failure_count += 1
            continue

        # Write summary file: {stem_name}.md with per-chunk summaries and links
        summary_path = os.path.join(file_output_dir, f"{stem_name}.md")
        try:
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(f"# {stem_name} Summary\n\n")
                f.write("> AI-generated summary per page range\n\n")
                f.write("## Page Chunks\n\n")
                for s, e, cfile, _ in chunk_ranges:
                    f.write(f"- [{cfile}]({cfile})\n")
                f.write("\n## Summaries\n\n")
                for s, e, cfile, summary in chunk_ranges:
                    f.write(f"### Pages {s}-{e}\n\n")
                    if summary:
                        f.write(f"{summary}\n\n")
                    else:
                        f.write("> No summary generated for this section.\n\n")
                    f.write(f"[View full content]({cfile})\n\n")
            logger.info("Wrote summary file %s", summary_path)
        except OSError as e:
            logger.error("Failed to write summary file for %s: %s", filename, e)
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
