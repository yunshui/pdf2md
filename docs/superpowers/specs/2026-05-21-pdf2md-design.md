# pdf2md Design Spec

**Date**: 2026-05-21
**Type**: Single-file CLI tool for PDF/DOCX to Markdown conversion via remote API

## Architecture

Single-file Python script (`pdf2md.py`) with no external dependencies beyond stdlib + `requests`.

### File Structure

```
pdf2md.py              # Main script: CLI, API client, file I/O, logging
conf/setting.json      # Configuration
output/                # Generated markdown files
logs/                  # Log files (pdf2md-YYYYMMDD.log)
```

### Configuration (conf/setting.json)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| api_url | string | http://123.192.49.73:8000/convert2markdown | API endpoint |
| client_id | string | bf-mkd | API client identifier header |
| max_retries | int | 3 | Max retry attempts on failure |
| retry_delay | int | 2 | Seconds between retries |
| timeout | int | 120 | Request timeout in seconds |
| output_dir | string | output | Output directory for .md files |
| log_dir | string | logs | Log directory |

### CLI Usage

```
python pdf2md.py <path>
```

- `<path>`: Single file (pdf/docx) or directory (processes all supported files)
- Exits with code 0 if all succeed, 1 if any fail

### Directory Setup

- `output/` and `logs/` directories are created automatically if they do not exist.
- `conf/setting.json` is created with defaults on first run if missing.
- Malformed JSON or missing required fields in `setting.json`: fail fast with clear error message.

### Data Flow

1. Load `conf/setting.json` (create with defaults if missing)
2. Setup logging to `logs/pdf2md-YYYYMMDD.log`
3. Resolve input files from CLI argument
4. For each file:
   a. Read binary, encode to base64
   b. POST to API (one file per request, wrapped in single-element array `{"files": [base64_string]}`), with retry logic
   c. On success: write `md_content` from response to `output/<name>.md`
   d. On name collision: append `_` + 5 random lowercase chars
   e. Log timing, status, errors

### API Contract

**Request**: `POST {api_url}`
- Header: `client_id: {client_id}`, `Content-Type: application/json`
- Body: `{"files": [base64_string]}`

**Response**:
```json
{
  "task_id": "...",
  "status": "completed",
  "backend": "...",
  "file_names": ["file_0"],
  "version": "...",
  "results": {
    "0": {"md_content": "..."}
  }
}
```

### Error Handling

- Network errors: retry up to `max_retries` with `retry_delay` between attempts
- Non-200 HTTP: retry
- JSON parse error: fail immediately (no retry)
- Missing `md_content` in response: log error, skip file
- Unsupported file extension: log warning, skip

### Logging

Format: `[YYYY-MM-DD HH:MM:SS] {LEVEL}  {message}`

Key logged info: config loaded, input file name, base64 size, attempt number, response status, output file name, elapsed time, error details.
