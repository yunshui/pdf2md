# PDF to Markdown Converter

A Python-based tool for converting PDF files to Markdown format with multilingual OCR support (Chinese/English), high-fidelity formatting preservation, and key summary extraction.

## Features

- **Multilingual OCR**: Supports Chinese (Simplified/Traditional) and English text extraction
- **Mixed PDF Types**: Handles both digitally created and scanned documents
- **High-Fidelity Formatting**: Preserves fonts, colors, complex layouts using HTML in Markdown
- **Summary Extraction**: Extracts key information for indexing with links to detailed sections
- **Efficient Processing**: Streaming architecture handles large files (1MB-200MB) with minimal memory
- **Batch Processing**: Convert single files or entire directories
- **Resume Support**: Checkpoint system allows resuming interrupted processing
- **Smart Deduplication**: Removes repeated headers/footers, places edge text appropriately

## Installation

### Requirements

- Python 3.8+
- Poppler (for pdf2image)

### Install Dependencies

```bash
# Core dependencies
pip install pdfplumber pdf2image paddleocr Pillow click

# Optional dependencies
pip install tesseract openai
```

### Install Poppler

**macOS:**
```bash
brew install poppler
```

**Ubuntu/Debian:**
```bash
sudo apt-get install poppler-utils
```

**Windows:**
Download from [Poppler Windows builds](https://github.com/oschwartz10612/poppler-windows/releases/)

## Usage

### Command Line Interface

```bash
# Convert a single PDF file
python pdf2md.py -input ./input/report.pdf

# Convert all PDFs in a directory
python pdf2md.py -input ./input/
```

### Output Structure

**Single file output:**
```
./input/report.md
```

**Multiple files output:**
```
./input/report_md/
├── report.md              # Main file with summaries + anchors
├── docs/
│   ├── section1.md        # Detailed content sections
│   ├── section2.md
│   └── ...
└── assets/
    ├── page5_image1.png   # Extracted images
    ├── page12_chart.png
    └── ...
```

## Architecture

The tool uses a modular streaming pipeline:

```
Input PDF → Page Splitter → Content Extractor → OCR Engine →
Summarizer → Markdown Generator → Output Files
```

### Key Components

- **Core Module**: Pipeline orchestration and page-by-page processing
- **OCR Module**: Multilingual text extraction with lazy invocation
- **Markdown Module**: High-fidelity Markdown generation
- **Summary Module**: Key information extraction and indexing
- **Utils Module**: Deduplication, image processing, and progress tracking

## Development

### Run Tests

```bash
# Run all tests
python -m pytest tests/

# Run unit tests
python -m pytest tests/unit/

# Run integration tests
python -m pytest tests/integration/

# Run with coverage
python -m pytest tests/ --cov=pdf2md --cov-report=html
```

### Project Structure

```
pdf2md/
├── core/              # PDF processing engine
├── ocr/               # OCR engine (pluggable)
├── markdown/          # Markdown generator
├── summary/           # Summary extraction
├── utils/             # Shared utilities
├── cli/               # Command-line interface
└── pdf2md.py          # Entry point
```

## License

[Specify your license here]

## Documentation

- [CLAUDE.md](./CLAUDE.md) - Project guidance for Claude Code
- [docs/PROGRESS.md](./docs/PROGRESS.md) - Project progress tracking and milestones
- [docs/LESSONS.md](./docs/LESSONS.md) - Lessons learned and best practices
- [docs/superpowers/specs/](./docs/superpowers/specs/) - Detailed design specifications