# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**pdf2md** — CLI tool for converting PDF/DOCX/DOC/TXT files to Markdown via a remote paginated API with LLM summarization.

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
| `api_url` | `http://123.192.49.73:8000/file_parse` | Paginated parse API endpoint |
| `client_id` | `bf-mkd` | API client identifier header |
| `max_retries` | `3` | Max retry attempts on failure |
| `retry_delay` | `2` | Seconds between retries |
| `timeout` | `120` | Request timeout in seconds |
| `output_dir` | `output` | Output directory for `.md` files |
| `log_dir` | `logs` | Log directory |
| `page_num` | `5` | Pages per API request |
| `summarize_api_url` | `http://127.0.0.1:8000/v1/chat/completions` | LLM summary API endpoint |
| `summarize_api_key` | `""` | LLM API key (optional) |
| `summarize_model` | `gpt-4o` | LLM model name |
| `summarize_prompt` | *(built-in template)* | LLM summary prompt template |

## Output and Logs

- **Output**: Each file gets a `{stem_name}_md/` directory under `output/`, containing:
  - `{stem_name}.md` — LLM-generated summary with links to chunks
  - `{stem_name}_{start}-{end}.md` — per-page-range markdown files
- **Logs**: `logs/pdf2md-YYYYMMDD.log` — daily rotation, includes timing, attempt counts, errors.

## API Contract

### Paginated Parse API (`/file_parse`)
- **Request**: `POST {api_url}` with header `client_id: {client_id}`, multipart form-data: `files` (binary file), `start_page_id`, `end_page_id`
- **Response**: JSON with `status`, `results` dict containing `md_content` per item
- **Termination**: Empty `results` (`{}`) means no more content

### LLM Summarize API (`/v1/chat/completions`)
- **Request**: `POST {summarize_api_url}` with `Authorization: Bearer {api_key}`, body `{"model": model, "messages": [{"role": "user", "content": prompt}]}`
- **Response**: OpenAI-compatible format, summary from `choices[0].message.content`

## File Structure

```
pdf2md.py              # Main script (all logic)
conf/setting.json      # Configuration
requirements.txt       # Python dependencies
output/                # Generated markdown files (runtime)
logs/                  # Log files (runtime)
data/                  # Example input/output files
```

## Documentation

All project documentation is under `docs/spec/`:

| Document | Purpose |
|----------|---------|
| [PRD](docs/spec/PRD.md) | Product requirements, user stories, feature specs |
| [APP_FLOW](docs/spec/APP_FLOW.md) | Application flowcharts, retry logic, error matrix |
| [TECH](docs/spec/TECH.md) | Technical architecture, design decisions, security |
| [FRONTEND](docs/spec/FRONTEND.md) | CLI interface spec, output examples, exit codes |
| [BACKEND](docs/spec/BACKEND.md) | External API contract, local processing, logging |
| [IMPLEMENTATION_PLAN](docs/spec/IMPLEMENTATION_PLAN.md) | Implementation phases, test strategy, decisions log |
| [PROGRESS](docs/spec/PROGRESS.md) | Timeline, task status, metrics, open issues |
| [LESSON](docs/spec/LESSON.md) | Lessons learned, reusable patterns, suggestions |

Also see: `docs/superpowers/specs/` (design spec), `docs/superpowers/plans/` (implementation plan).

## Skills

| Skill | Purpose |
|-------|---------|
| [skills/pdf2md/SKILL.md](skills/pdf2md/SKILL.md) | pdf2md CLI usage guide, API contract, error scenarios, dev workflow |
| [skills/update-docs/SKILL.md](skills/update-docs/SKILL.md) | Auto-update project documentation after code changes |
