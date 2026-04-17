# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Related Documentation**:
- [README.md](./README.md) - Project overview (English)
- [README.zh.md](./README.zh.md) - Project overview (Chinese)
- [docs/PROGRESS.md](./docs/PROGRESS.md) - Project progress and milestones
- [docs/LESSONS.md](./docs/LESSONS.md) - Lessons learned and best practices
- [docs/superpowers/specs/](./docs/superpowers/specs/) - Detailed design specifications

---

## Project Overview

**pdf2md** - A Python-based tool for converting PDF files to Markdown format with multilingual OCR support (Chinese/English), high-fidelity formatting preservation, and key summary extraction.

The project uses a modular streaming pipeline architecture to handle large PDF files (up to 200MB) efficiently by processing pages one at a time.

## Architecture

### High-Level Pipeline

```
Input PDF → Page Splitter → Content Extractor → OCR Engine →
Summarizer → Markdown Generator → Output Files
```

### Key Design Principles

1. **Streaming**: Process pages sequentially to minimize memory usage for large files
2. **Lazy OCR**: Only invoke OCR on pages with scanned images or minimal extracted text
3. **Modular stages**: Each component has single responsibility
4. **Resource pooling**: Reuse OCR engines and formatters across pages

### Module Structure

```
pdf2md/
├── core/              # PDF processing engine (pipeline, page_processor, resource_manager)
├── ocr/               # OCR engine (base.py, paddleocr.py, tesseract.py)
├── markdown/          # Markdown generator (formatter, table_formatter, image_linker, layout_analyzer)
├── summary/           # Summary extraction (extractor, rule_based, ai_extractor)
├── utils/             # Shared utilities (deduplicator, image_processor, file_manager, progress_tracker)
├── cli/               # Command-line interface
└── pdf2md.py          # Entry point
```

### OCR Detection Logic

OCR is invoked when:
1. Text extraction fails completely (empty or None)
2. Extracted text is < 100 characters OR < 5% of typical page volume
3. Page contains primarily images with minimal selectable text
4. Image elements occupy > 80% of page area

OCR caching is in-memory, per-file, keyed by image pixel data hash.

### Chapter Boundary Detection

Used for header/footer deduplication at chapter level and organizing output structure. Detected by:
1. H1-level headings (font size > 16pt, centered/top-positioned)
2. Page breaks following section headers with numeric patterns (e.g., "Chapter 1", "第一章")
3. Major headings at page beginning with large font size
4. PDF outline/bookmarks if available

### Output Structure

Single file: `./input/filename.md`

Multiple files: `./input/filename_md/`
```
filename_md/
├── filename.md              # Main file with summaries + anchors
├── docs/
│   ├── section1.md        # Detailed content sections
│   └── ...
└── assets/
    ├── page5_image1.png   # Extracted images
    └── ...
```

## Development Commands

### Run the CLI
```bash
# Single file processing
python pdf2md.py -input ./input/report.pdf

# Batch directory processing
python pdf2md.py -input ./input/
```

### Run Tests
```bash
# Run all tests
python -m pytest tests/

# Run unit tests only
python -m pytest tests/unit/

# Run integration tests only
python -m pytest tests/integration/

# Run specific test file
python -m pytest tests/unit/test_ocr.py

# Run with coverage
python -m pytest tests/ --cov=pdf2md --cov-report=html
```

### Install Dependencies
```bash
# Install core dependencies
pip install pdfplumber pdf2image paddleocr Pillow click

# Install optional dependencies
pip install tesseract openai
```

## Key External Dependencies

- **pdfplumber** - PDF text and table extraction
- **pdf2image** - Convert PDF pages to images for OCR
- **paddleocr** - Multilingual OCR (Chinese/English)
- **Pillow** - Image processing
- **click** - CLI argument parsing
- **System**: Python 3.8+, Poppler (for pdf2image)

## Checkpoint System

Checkpoint files enable resume capability: `filename.pdf.checkpoint.json`

Format:
```json
{
  "file_hash": "sha256_hash_of_source_file",
  "total_pages": 42,
  "processed_pages": [1, 2, 3, 5, 6],
  "failed_pages": [4],
  "timestamp": "2026-04-17T10:30:00Z",
  "version": "1.0"
}
```

Resume logic compares file hash and skips processed pages.