---
name: pdf2md
description: Convert PDF, DOCX, DOC, or TXT files to Markdown via a paginated API with LLM summarization
---

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
    ├── pdf2md.py             # Main CLI script (~500 lines)
    ├── requirements.txt      # Runtime dependencies
    ├── requirements-dev.txt  # Dev dependencies (pytest)
    └── tests/
        └── test_pdf2md.py    # Test suite (40 tests)
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

Main CLI script — single file, ~500 lines, Python 3.7+.

**Functions:**

| Function | Purpose |
|----------|---------|
| `get_pdf_page_count(file_path, logger)` | Read total page count from PDF file using PyMuPDF (PDF only) |
| `resolve_files(path, logger)` | Resolve path to list of supported files (.pdf, .docx, .doc, .txt) |
| `call_file_parse_api(config, logger, file_path, start_page, end_page, file_name)` | POST file to paginated parse API with multipart form-data + retry |
| `call_summarize_api(config, logger, chunks_info)` | Call LLM API to generate document summary |
| `extract_md_content(response_data)` | Extract markdown from API response, list of (index, content) |
| `get_unique_dir(parent_dir, stem_name)` | Return unique output directory path, suffix on collision |
| `load_config(script_dir)` | Load/create config from conf/setting.json |
| `setup_logging(log_dir)` | Set up file + console logging, daily rotation |
| `main()` | Entry point: paginate → call API → write chunks → summarize |

### scripts/requirements.txt

```
requests>=2.28.0
PyMuPDF==1.27.2.3
```

### scripts/requirements-dev.txt

```
pytest>=7.0.0
```

### scripts/tests/test_pdf2md.py

40 tests covering all functions and integration flows.

**Test classes:**
- `TestLoadConfig` (6) — config creation, loading, validation, new fields check
- `TestResolveFiles` (5) — single file, directory, unsupported extensions, case insensitive
- `TestGetPdfPageCount` (3) — valid PDF page count, import error, parse failure
- `TestCallFileParseApi` (5) — success, retries, non-200, JSON errors, connection errors
- `TestCallSummarizeApi` (6) — success, no choices, HTTP errors, auth headers, retries
- `TestExtractMdContent` (6) — single/multiple results, missing keys, invalid values
- `TestGetUniqueDir` (4) — directory uniqueness, suffix format
- `TestIntegration` (5) — full flow with paginated API + summarization (success + failure + pagination)

---

## Configuration

File: `conf/setting.json` (auto-created with defaults on first run, relative to script directory)

| Field | Default | Description |
|-------|---------|-------------|
| `api_url` | `http://123.192.49.73:8000/file_parse` | Paginated parse API endpoint |
| `client_id` | `bf-mkd` | API client identifier header |
| `max_retries` | `3` | Max retry attempts on failure |
| `retry_delay` | `2` | Seconds between retries |
| `timeout` | `120` | Request timeout in seconds |
| `output_dir` | `output` | Output directory for `.md` files |
| `log_dir` | `logs` | Log directory |
| `page_num` | `10` | Pages per API request |
| `summarize_api_url` | `http://123.192.49.9:8086/v1/chat/completions` | LLM summary API endpoint |
| `summarize_api_key` | `"123"` | LLM API key (optional) |
| `summarize_model` | `qwen3.5` | LLM model name |
| `summarize_timeout` | `200` | Summarize API timeout in seconds |
| `summarize_prompt` | *(see DEFAULT_CONFIG)* | LLM summary prompt template |

**Notes:**
- Relative `output_dir` and `log_dir` are resolved relative to the script directory
- Missing keys or invalid types cause exit with error message on stderr

---

## API Contract

### Paginated Parse API (`/file_parse`)

- **Request**: `POST {api_url}` with header `client_id: {client_id}`, multipart form-data:
  - `files`: binary file content
  - `start_page_id`: starting page number (0-based string)
  - `end_page_id`: ending page number (0-based string)
- **Response**: JSON with `status`, `results` dict containing `md_content` per item
- **Termination (PDF)**: When `start_page >= total_pages` (read from file via PyMuPDF)
- **Termination (non-PDF)**: Empty `results` (`{}`) means no more content

```json
{
  "status": "completed",
  "results": {
    "0": { "md_content": "# Markdown content here" }
  }
}
```

### LLM Summarize API (`/v1/chat/completions`)

- **Request**: `POST {summarize_api_url}` with `Authorization: Bearer {api_key}` (optional), OpenAI-compatible body
- **Response**: `choices[0].message.content` contains the summary text

---

## Output Structure

Each input file gets its own `{stem_name}_md/` directory:

```
output/
└── report_md/
    ├── report.md              # Summary (with links to chunks)
    ├── report_0-9.md          # Pages 0-9 content
    ├── report_10-19.md        # Pages 10-19 content
    └── ...
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
| Output directory collision | Append `_XXXXX` (5 random lowercase chars) |
| Output file collision | Append `_XXXXX` (5 random lowercase chars) |

---

## Verification

```bash
cd scripts
python3 -m pytest tests/test_pdf2md.py -v
```

Expected: **40 tests passed**
