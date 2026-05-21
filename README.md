# pdf2md

Convert PDF, DOCX, DOC, and TXT files to Markdown via a remote conversion API.

## Quick Start

```bash
pip install -r requirements.txt
python pdf2md.py <file_or_directory>
```

## Features

- **Multiple formats**: PDF, DOCX, DOC, TXT
- **Batch processing**: Pass a directory to convert all supported files at once
- **Retry logic**: Configurable retries for network/API failures
- **Collision handling**: Automatically renames output files if duplicates exist
- **Detailed logging**: Daily log files with timing, attempt counts, and error details

## Configuration

Edit `conf/setting.json`:

| Field | Default | Description |
|-------|---------|-------------|
| `api_url` | `http://123.192.49.73:8000/convert2markdown` | API endpoint |
| `client_id` | `bf-mkd` | API client identifier |
| `max_retries` | `3` | Max retry attempts |
| `retry_delay` | `2` | Seconds between retries |
| `timeout` | `120` | Request timeout (seconds) |
| `output_dir` | `output` | Output directory for `.md` files |
| `log_dir` | `logs` | Log directory |

## Output

- Markdown files are written to the `output/` directory
- If a file with the same name exists, a random 5-character suffix is appended (e.g., `report_abcde.md`)

## Logs

Logs are stored in `logs/pdf2md-YYYYMMDD.log` with daily rotation. Each entry includes:
- Input file name and base64 size
- API call attempt number and response status
- Elapsed time per request
- Output file name and size
- Error details on failure

## Exit Codes

- `0`: All files converted successfully
- `1`: One or more files failed to convert

## File Structure

```
pdf2md/
├── pdf2md.py              # Main script
├── conf/setting.json      # Configuration
├── requirements.txt       # Python dependencies
├── output/                # Generated markdown files (runtime)
└── logs/                  # Log files (runtime)
```
