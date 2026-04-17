# PDF to Markdown Converter Design Document

**Date:** 2026-04-17
**Status:** Approved
**Approach:** Modular Pipeline Architecture

## Overview

A Python-based tool for converting PDF files to Markdown format with support for:
- Mixed PDF types (digitally created and scanned documents)
- Multilingual OCR (Chinese/English)
- High-fidelity formatting preservation
- Key summary extraction for indexing
- Efficient processing of large files (1MB-200MB)

## Requirements

### Functional Requirements

1. **Content Extraction**
   - Extract text, images, and tables from PDF pages
   - OCR text from images in scanned documents
   - Preserve images with link references
   - Convert tables to Markdown format

2. **Summary Extraction**
   - Extract key information for indexing
   - Generate summaries with links to detailed sections
   - Hybrid approach: rule-based extraction with optional AI

3. **Formatting Preservation**
   - High-fidelity preservation (fonts, colors, complex layouts)
   - Use HTML in Markdown where needed
   - Preserve headers, footers, and edge text

4. **Deduplication**
   - Identify repeated headers/footers across pages
   - Deduplicate within chapters
   - Place unique headers/footers at chapter level
   - Place edge text at page end

5. **Output Organization**
   - Single file: `./input/xx.md`
   - Multiple files: `./input/xx_md/` directory
   - Structure: `xx.md` (main), `docs/` (details), `assets/` (images)
   - Overwrite existing files

6. **CLI Interface**
   - Command: `python pdf2md.py -input ./input/xx.pdf`
   - Support batch processing with directory input
   - Clear error messages and progress reporting

### Non-Functional Requirements

- **Resource Efficiency**: Minimize memory usage for large files
- **Performance**: Page-by-page streaming to handle 200MB+ files
- **Reliability**: Graceful error handling and recovery
- **Maintainability**: Modular, testable architecture

## Architecture

### High-Level Design

Streaming pipeline architecture with modular stages:

```
Input PDF → Page Splitter → Content Extractor → OCR Engine →
Summarizer → Markdown Generator → Output Files
```

### Key Principles

1. **Streaming**: Process one page at a time to minimize memory usage
2. **Lazy OCR**: Only invoke OCR on pages that appear to contain scanned images
3. **Modular stages**: Each component has a single responsibility
4. **Resource pooling**: Reuse OCR engines and formatters across pages

### Component Breakdown

```
pdf2md/
├── core/              # PDF processing engine
│   ├── pipeline.py
│   ├── page_processor.py
│   └── resource_manager.py
├── ocr/               # OCR engine (pluggable)
│   ├── base.py
│   ├── paddleocr.py
│   └── tesseract.py
├── markdown/          # Markdown generator
│   ├── formatter.py
│   ├── table_formatter.py
│   ├── image_linker.py
│   └── layout_analyzer.py
├── summary/           # Summary extraction
│   ├── extractor.py
│   ├── rule_based.py
│   └── ai_extractor.py
├── utils/             # Shared utilities
│   ├── deduplicator.py
│   ├── image_processor.py
│   ├── file_manager.py
│   └── progress_tracker.py
├── cli/               # Command-line interface
│   └── main.py
└── pdf2md.py          # Entry point
```

## Component Details

### Core Module

**Purpose**: Pipeline orchestration and page management

**Key Classes:**

- `Pipeline`: Main orchestrator that stages the processing workflow
  - `process_file(file_path)`: Process a single PDF file
  - `process_directory(dir_path)`: Process multiple PDFs in batch
  - `cleanup()`: Release resources after processing

- `PageProcessor`: Handles individual page processing
  - `process_page(page)`: Process a single page through the pipeline
  - `get_page_metadata(page)`: Extract page information
  - `handle_errors(page, error)`: Error recovery for failed pages

- `ResourceManager`: Manages shared resources
  - `get_ocr_engine()`: Get or create OCR engine instance
  - `get_formatter()`: Get Markdown formatter instance
  - `cleanup()`: Release all resources

### OCR Module

**Purpose**: Multilingual text extraction from images

**Key Classes:**

- `OCREngine` (Abstract Base):
  - `needs_ocr(page)`: Detect if OCR is required
  - `extract_text(image)`: Extract text from image
  - `supported_languages`: Return supported language codes

- `PaddleOCREngine`: PaddleOCR implementation
  - Supports Chinese (Simplified/Traditional) and English
  - Automatic language detection
  - Image preprocessing (rotation, contrast)

- `TesseractEngine` (Optional fallback):
  - Alternative OCR backend
  - Configurable language models

**Features:**
- Lazy invocation based on page analysis
- Image preprocessing for better accuracy
- Result caching for repeated patterns

### Markdown Module

**Purpose**: High-fidelity Markdown generation

**Key Classes:**

- `MarkdownFormatter`: Main formatter
  - `format_page(page_data)`: Convert page to Markdown
  - `format_text(text, style)`: Format text with styles
  - `format_html(html)`: Preserve complex HTML when needed

- `TableFormatter`: Table conversion
  - `format_table(table_data)`: Convert table to Markdown
  - `handle_merged_cells()`: Handle complex table structures
  - `apply_alignment()`: Preserve column alignment

- `ImageLinker`: Image management
  - `extract_image(image)`: Extract image from page
  - `create_link(path)`: Generate relative markdown link
  - `optimize_image(image)`: Optimize image size/quality

- `LayoutAnalyzer`: Layout preservation
  - `analyze_layout(elements)`: Analyze page layout
  - `generate_html(layout)`: Generate HTML for complex layouts
  - `preserve_spacing()`: Maintain original spacing

### Summary Module

**Purpose**: Extract key information for indexing

**Key Classes:**

- `SummaryExtractor`: Main coordinator
  - `extract_summaries(pages)`: Extract summaries from all pages
  - `generate_toc()`: Create table of contents with anchors
  - `create_index()`: Create searchable index

- `RuleBasedExtractor`: Pattern-based extraction
  - `extract_headings(page)`: Identify headings and subheadings
  - `extract_annotations(page)`: Find footnotes and annotations
  - `detect_chapters(pages)`: Identify chapter boundaries

- `AIExtractor` (Optional): AI-powered summarization
  - Placeholder for AI integration
  - Can use OpenAI API or local models

**Output Structure:**
- Main file contains summaries with anchor links
- Detailed sections split into separate files in `docs/`
- Table of contents at the top of main file

### Utils Module

**Purpose**: Shared utilities and helpers

**Key Components:**

- `Deduplicator`: Header/footer/edge text deduplication
  - `identify_patterns(pages)`: Find repeated elements
  - `deduplicate_headers()`: Remove duplicate headers
  - `deduplicate_footers()`: Remove duplicate footers
  - `place_edge_text()`: Position edge text at page end

- `ImageProcessor`: Image extraction and optimization
  - `extract_images(page)`: Extract images from page
  - `optimize(image)`: Compress and optimize
  - `save_image(image, path)`: Save to output directory

- `FileManager`: Batch file handling
  - `scan_directory(path)`: Find all PDF files
  - `create_output_structure(base_path)`: Create output directories
  - `handle_overwrites()`: Manage file overwriting

- `ProgressTracker`: Progress tracking
  - `start(file)`: Start tracking file processing
  - `update(progress)`: Update progress
  - `save_checkpoint()`: Save progress for recovery
  - `resume(checkpoint)`: Resume from checkpoint

## Data Flow

### Single File Processing

```
Input: ./input/report.pdf

1. Input Validation
   - Check file exists
   - Verify size < 200MB
   - Validate PDF format

2. PDF Streaming
   - Load pages one at a time
   - Extract page metadata

3. For each page:
   a. Page Splitter
      - Extract page content
      - Detect page type (text/image)

   b. Content Extractor
      - Extract text elements
      - Extract tables
      - Extract images
      - Analyze layout

   c. OCR Check
      - If scanned or minimal text → invoke OCR
      - Else use extracted text

   d. Deduplication
      - Compare headers/footers with previous pages
      - Track edge text

   e. Summary Extraction
      - Identify key sections
      - Extract headings
      - Find annotations

   f. Markdown Generation
      - Format content
      - Link images
      - Create anchors

4. Output Generation
   - Write report.md
   - Create assets/ directory
   - Save images

Output: ./input/report.md
```

### Batch Processing

```
Input: ./input/

1. Directory Scan
   - Find all .pdf files
   - Validate each file

2. Batch Queue
   - Process files sequentially
   - Track progress

3. For each PDF
   - Apply single file flow
   - Create per-file output directory

4. Output Organization
   ./input/file1_md/
   ├── file1.md
   ├── docs/
   └── assets/

   ./input/file2_md/
   ├── file2.md
   ├── docs/
   └── assets/
```

### Output File Structure

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

## Error Handling

### Error Categories

**File-level errors:**
- Corrupted PDF → Skip, log error, continue batch
- Size > 200MB → Reject with clear message
- Permission denied → Log error, continue batch

**Page-level errors:**
- OCR timeout → Retry once, then skip page with placeholder
- Image extraction failure → Log warning, continue
- Table parsing error → Fallback to raw text, log warning

**Output-level errors:**
- Directory creation failed → Abort with clear error message
- Disk space → Check before processing, abort if insufficient
- Existing files → Overwrite as specified

### Logging Strategy

- **INFO**: Processing progress, files processed
- **WARNING**: Recoverable issues (OCR retries, skipped pages)
- **ERROR**: Critical failures (corrupted files, I/O errors)

### Progress Tracking

- Save checkpoint file with processed pages
- Support resume from interruption
- Show progress bar for large files

## Testing Strategy

### Test Organization

```
tests/
├── unit/                 # Component-level tests
│   ├── test_ocr.py       # OCR engine tests
│   ├── test_markdown.py  # Markdown formatter tests
│   └── test_summary.py   # Extraction logic tests
├── integration/          # Pipeline integration tests
│   ├── test_pipeline.py  # End-to-end pipeline tests
│   └── test_cli.py       # CLI interface tests
└── fixtures/             # Sample PDFs for testing
    ├── small_text.pdf    # Simple text PDF
    ├── complex_tables.pdf # PDF with complex tables
    ├── scanned_doc.pdf   # Scanned document for OCR
    └── multilingual.pdf  # Chinese/English mixed
```

### Unit Testing Focus

- **OCR tests**: Mock OCR responses, test language detection, verify preprocessing
- **Markdown tests**: Verify table conversion, image linking, HTML formatting
- **Summary tests**: Test rule-based extraction patterns, heading detection
- **Deduplication tests**: Header/footer detection across pages

### Integration Testing

- **Pipeline tests**: Process complete PDFs, verify output structure
- **CLI tests**: Test command-line arguments, batch processing, error handling
- **Resource tests**: Verify memory usage with large files

### Test Coverage

- Target 80%+ code coverage for critical paths
- Test happy paths for each component
- Test error conditions and edge cases

## External Dependencies

### Required Libraries

- `pdfplumber` - PDF text and table extraction
- `pdf2image` - Convert PDF pages to images for OCR
- `paddleocr` - Multilingual OCR (Chinese/English)
- `Pillow` - Image processing
- `click` - CLI argument parsing

### Optional Dependencies

- `tesseract` - Alternative OCR engine
- `openai` - Optional AI summarization

### System Dependencies

- Python 3.8+
- Poppler (for pdf2image)

## CLI Interface

### Command Structure

```bash
# Single file processing
python pdf2md.py -input ./input/report.pdf

# Directory processing (batch)
python pdf2md.py -input ./input/
```

### Output Behavior

- Single file: Output to `./input/report.md`
- Multiple files: Create `./input/filename_md/` directory
- Overwrite existing files automatically

### Progress Reporting

- Show progress bar for large files
- Display processing status for each file
- Log warnings and errors to console

## Implementation Priorities

1. **Phase 1**: Core pipeline and basic PDF text extraction
2. **Phase 2**: OCR integration and image handling
3. **Phase 3**: Table extraction and Markdown formatting
4. **Phase 4**: Summary extraction and indexing
5. **Phase 5**: Deduplication and edge text handling
6. **Phase 6**: CLI interface and batch processing
7. **Phase 7**: Testing and optimization

## Future Enhancements

- Resume interrupted processing
- Parallel processing for multiple files
- Custom summary templates
- Additional OCR backends
- Cloud storage integration
- Web API interface