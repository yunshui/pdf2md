# pdf2md

Convert PDF, DOCX, DOC, and TXT files to Markdown via a remote paginated API with LLM summarization.

## Quick Start

```bash
pip install -r requirements.txt
python pdf2md.py <file_or_directory>
```

## Features

- **Multiple formats**: PDF, DOCX, DOC, TXT
- **Batch processing**: Pass a directory to convert all supported files at once
- **Paginated processing**: API called per page range, each chunk saved independently
- **LLM summarization**: Auto-generated summary with links to chunk files (configurable OpenAI-compatible API)
- **Directory-level output**: Each input file gets its own `{name}_md/` directory with chunks + summary
- **Retry logic**: Configurable retries for network/API failures
- **Detailed logging**: Daily log files with timing, attempt counts, and error details

## Configuration

Edit `conf/setting.json`:

| Field | Default | Description |
|-------|---------|-------------|
| `api_url` | `http://123.192.49.73:8000/file_parse` | Paginated parse API endpoint |
| `client_id` | `bf-mkd` | API client identifier |
| `max_retries` | `3` | Max retry attempts |
| `retry_delay` | `2` | Seconds between retries |
| `timeout` | `120` | Request timeout (seconds) |
| `output_dir` | `output` | Output directory for `.md` files |
| `log_dir` | `logs` | Log directory |
| `page_num` | `5` | Pages per API request |
| `summarize_api_url` | `http://123.192.49.9:8086/v1/chat/completions` | LLM summary API endpoint |
| `summarize_api_key` | `"123"` | LLM API key (optional) |
| `summarize_model` | `qwen3.5` | LLM model name |
| `summarize_prompt` | *(built-in)* | LLM summary prompt template |

## Output

Each input file gets its own output directory `{stem_name}_md/`:

```
output/
└── report_md/
    ├── report.md              # Summary file (with chunk links)
    ├── report_0-4.md          # Pages 0-4 content
    ├── report_5-9.md          # Pages 5-9 content
    └── ...
```

**Summary file format**:

```markdown
# report Summary

> AI-generated summary

{LLM summary text}

## Page Chunks

- [report_0-4.md](report_0-4.md)
- [report_5-9.md](report_5-9.md)
```

## Logs

Logs are stored in `logs/pdf2md-YYYYMMDD.log` with daily rotation. Each entry includes:
- Input file name and size
- API call attempt number and page range
- Elapsed time per request
- Chunk and summary file names and sizes
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

## Documentation

| Document | Description |
|----------|-------------|
| [PRD](docs/spec/PRD.md) | Product requirements, user stories, feature specifications |
| [APP_FLOW](docs/spec/APP_FLOW.md) | Application flow, retry logic, error handling matrix |
| [TECH](docs/spec/TECH.md) | Technical architecture, module descriptions, design decisions |
| [FRONTEND](docs/spec/FRONTEND.md) | CLI interface specification, output examples, exit codes |
| [BACKEND](docs/spec/BACKEND.md) | External API contract, local processing logic, logging system |
| [IMPLEMENTATION_PLAN](docs/spec/IMPLEMENTATION_PLAN.md) | Implementation phases, change log, test strategy |
| [PROGRESS](docs/spec/PROGRESS.md) | Project timeline, task completion status, metrics |
| [LESSON](docs/spec/LESSON.md) | Lessons learned, reusable patterns, improvement suggestions |
