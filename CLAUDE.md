# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**pdf2md** — CLI tool for converting PDF/DOCX/DOC/TXT files to Markdown via a remote API.

## Tech Stack

- **Language**: Python 3.7+
- **Dependencies**: `requests` (see `requirements.txt`)
- **Single-file script**: `pdf2md.py` — all logic in one file

## Setup and Usage

```bash
pip install -r requirements.txt
python pdf2md.py <file_or_directory_path>
```

- Pass a single file (`.pdf`, `.docx`, `.doc`, `.txt`) to convert it
- Pass a directory to convert all supported files in it
- Exit code 0 if all conversions succeed, 1 if any fail

## Configuration

Config file: `conf/setting.json` (created with defaults on first run if missing)

| Field | Default | Description |
|-------|---------|-------------|
| `api_url` | `http://123.192.49.73:8000/convert2markdown` | API endpoint |
| `client_id` | `bf-mkd` | API client identifier header |
| `max_retries` | `3` | Max retry attempts on failure |
| `retry_delay` | `2` | Seconds between retries |
| `timeout` | `120` | Request timeout in seconds |
| `output_dir` | `output` | Output directory for `.md` files |
| `log_dir` | `logs` | Log directory |

## Output and Logs

- **Output**: `.md` files written to `output/` directory. If a file with the same name exists, a random 5-char suffix is appended (e.g., `report_abcde.md`).
- **Logs**: `logs/pdf2md-YYYYMMDD.log` — daily rotation, includes timing, attempt counts, errors.

## API Contract

- **Request**: `POST {api_url}` with header `client_id: {client_id}`, body `{"files": [base64_string]}`
- **Response**: JSON with `status`, `results` dict containing `md_content` per item

## File Structure

```
pdf2md.py              # Main script (all logic)
conf/setting.json      # Configuration
requirements.txt       # Python dependencies
output/                # Generated markdown files (runtime)
logs/                  # Log files (runtime)
data/                  # Example input/output files
```
