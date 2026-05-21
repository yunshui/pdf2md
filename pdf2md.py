#!/usr/bin/env python3
"""pdf2md - Convert PDF files to Markdown via a remote conversion API.

This script accepts a PDF file or directory of PDFs, sends them to a
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
        description="Convert PDF files to Markdown via a remote conversion API.",
    )
    parser.add_argument(
        "path",
        help="Path to a PDF file or directory containing PDF files.",
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

    # TODO: implement PDF-to-Markdown conversion workflow.
    logger.info("Processing path: %s", args.path)


if __name__ == "__main__":
    main()
