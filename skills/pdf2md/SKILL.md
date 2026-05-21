# pdf2md - PDF/Document to Markdown Converter

**Type**: CLI tool skill
**Trigger**: When user needs to convert PDF, DOCX, DOC, or TXT files to Markdown
**Purpose**: Guide usage, development, and troubleshooting of the pdf2md CLI tool

---

## How to Use

Invoke this skill when:
- A user wants to convert a document to Markdown
- Working on or modifying the pdf2md codebase
- Debugging conversion failures
- Adding new features or tests to the project

---

## Tool Overview

Single-file Python CLI tool that converts PDF/DOCX/DOC/TXT files to Markdown via a remote API.

**Key characteristics:**
- Python 3.7+, single script (`pdf2md.py`)
- One dependency: `requests`
- Config file: `conf/setting.json` (auto-created on first run)
- Output: `.md` files in `output/` directory
- Logs: `logs/pdf2md-YYYYMMDD.log` (daily rotation)

---

## Usage

```bash
pip install -r requirements.txt
python pdf2md.py <file_or_directory_path>
```

- Pass a single file → converts it
- Pass a directory → converts all supported files in it
- Exit code 0 = all success, 1 = any failure

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

## Function Inventory

| Function | Purpose |
|----------|---------|
| `resolve_files(path, logger)` | Resolve path to list of supported files |
| `file_to_base64(file_path)` | Read file, return base64-encoded content |
| `call_api(config, logger, base64, name)` | POST to API with retry, return response dict or None |
| `extract_md_content(response_data)` | Extract markdown from API response, list of (index, content) |
| `get_unique_path(output_dir, base_name)` | Return unique output path, suffix on collision |
| `load_config(script_dir)` | Load/create config from conf/setting.json |
| `setup_logging(log_dir)` | Set up file + console logging, daily rotation |
| `main()` | Entry point: parse args, load config, run conversion |

---

## Development

### Running tests

```bash
python3 -m pytest tests/test_pdf2md.py -v
```

34 tests total covering:
- `load_config` — creation, loading, validation errors
- `resolve_files` — single file, directory, unsupported extensions
- `file_to_base64` — encoding, empty files, missing files
- `call_api` — success, retries, non-200, JSON errors, connection errors, timeouts
- `extract_md_content` — single/multiple results, missing keys, invalid values
- `get_unique_path` — uniqueness, suffix format (5 lowercase chars)
- Integration — full flow with mocked API (success + failure)

### Test fixtures

- `tmp_dir` — temporary directory path (string)
- `sample_config` — valid config dict with `max_retries: 2`
- `sample_api_response` — valid API response with one result

### Mocking pattern for integration tests

```python
@patch("pdf2md.load_config")
@patch("pdf2md.requests.post")
def test_full_flow(self, mock_post, mock_load_config, tmp_dir):
    mock_load_config.return_value = { ... test config ... }
    mock_post.return_value = { ... mock response ... }
    with patch("sys.argv", ["pdf2md.py", test_file]):
        pdf2md.main()
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

## File Structure

```
pdf2md.py              # Main script (all logic)
conf/setting.json      # Configuration (auto-created)
requirements.txt       # Python dependencies
requirements-dev.txt   # Dev dependencies (pytest, etc.)
output/                # Generated markdown files (runtime)
logs/                  # Log files (runtime)
tests/test_pdf2md.py   # Test suite (34 tests)
docs/spec/             # Project specification documents
```
