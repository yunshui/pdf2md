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

All runnable source files are in `scripts/` relative to this skill:

```
skills/pdf2md/
├── SKILL.md                 # This file
└── scripts/
    ├── pdf2md.py             # Main CLI script (375 lines)
    ├── requirements.txt      # Runtime dependencies
    ├── requirements-dev.txt  # Dev dependencies (pytest)
    └── tests/
        └── test_pdf2md.py    # Test suite (34 tests)
```

To deploy on a new machine, copy the entire `scripts/` directory and run:

```bash
cd scripts
pip install -r requirements.txt
python pdf2md.py <file_or_directory_path>
```

---

## Script Files

### scripts/pdf2md.py

Main CLI script — single file, ~375 lines, Python 3.7+.

**Functions:**

| Function | Purpose |
|----------|---------|
| `resolve_files(path, logger)` | Resolve path to list of supported files (.pdf, .docx, .doc, .txt) |
| `file_to_base64(file_path)` | Read file, return base64-encoded content |
| `call_api(config, logger, base64, name)` | POST to API with retry, return response dict or None |
| `extract_md_content(response_data)` | Extract markdown from API response, list of (index, content) |
| `get_unique_path(output_dir, base_name)` | Return unique output path, suffix on collision |
| `load_config(script_dir)` | Load/create config from conf/setting.json |
| `setup_logging(log_dir)` | Set up file + console logging, daily rotation |
| `main()` | Entry point: parse args, load config, run conversion |

### scripts/requirements.txt

```
requests>=2.28.0
```

### scripts/requirements-dev.txt

```
pytest>=7.0.0
```

### scripts/tests/test_pdf2md.py

34 tests covering all functions and integration flows.

**Test classes:**
- `TestLoadConfig` (5) — config creation, loading, validation errors
- `TestResolveFiles` (5) — single file, directory, unsupported extensions, case insensitive
- `TestFileToBase64` (3) — encoding, empty files, missing files
- `TestCallApi` (7) — success, retries, non-200, JSON errors, connection errors, timeouts
- `TestExtractMdContent` (6) — single/multiple results, missing keys, invalid values
- `TestGetUniquePath` (4) — uniqueness, suffix format (5 lowercase chars)
- `TestIntegration` (4) — full flow with mocked API (success + failure, no args, nonexistent path)

---

## Configuration

File: `conf/setting.json` (auto-created with defaults on first run, relative to script directory)

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
cd scripts
python3 -m pytest tests/test_pdf2md.py -v
```

Expected: **34 tests passed**
