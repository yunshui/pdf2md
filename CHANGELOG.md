# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- pypdf>=3.0.0 dependency for improved image extraction
- body_text property to PageData for edge text filtering
- Filter methods to PageText for region-based text filtering
- TableFormatter: Automatic column alignment detection (left/center/right)
- TableFormatter: HTML table formatting as alternative to Markdown
- TableFormatter: Cell grid building with rowspan/colspan support
- Table class: is_empty(), get_header_cells(), has_header(), get_dimensions() methods
- ChapterDetector: Additional chapter patterns (Appendix, Index, References, etc.)
- ChapterDetector: Structure-based chapter detection (layout changes, density changes)
- ChapterDetector: Page top position detection (top 20% of page)
- ChapterDetector: Font size comparison (1.3x median) for visual hierarchy

### Changed
- Image extraction now supports pypdf (no poppler required) as primary method
- Improved relative path calculation for image links in multi-file output
- Summary extractors now use body_text instead of raw_text to exclude edge text
- Edge text section now has single header (fixed duplication)
- Table formatting with spaces in separator rows for better readability
- MockTableCell tests use rowspan/colspan naming (consistent with production code)
- MockLayout tests now include text_density and body_regions attributes
- MockPageData tests now include proper PageData structure
- Chapter detection now scores and selects best heading on each page

### Fixed
- Edge text pollution in main content - page headers now properly filtered
- Checkpoint file path duplication (double directory names)
- Image link paths in docs/ directory now correctly use ../assets/
- Duplicate "## Edge Text" header in markdown output
- TableFormatter test compatibility with MockTableCell attribute naming
- test_summary.py mock dataclass mutable default values (edge_regions, images)

## [0.1.0] - 2026-04-20

### Added

#### Core Features
- Complete PDF to Markdown conversion pipeline
- Streaming page-by-page processing for memory efficiency
- Support for mixed PDF types (digital and scanned)
- Checkpoint/resume support for interrupted processing
- Batch directory processing

#### OCR Support
- PaddleOCR integration for multilingual OCR (Chinese/English)
- Configurable OCR triggering based on content analysis
- Lazy OCR invocation (only when needed)
- Image preprocessing for better OCR accuracy
- Language auto-detection

#### Content Extraction
- Text extraction with formatting preservation (font size, bold, italic)
- Image extraction with optimization (PNG/JPEG/WebP)
- Table extraction with merged cell support
- Layout analysis (header, footer, body, edge regions)
- Page statistics generation

#### Deduplication
- Chapter boundary detection (pattern, font, outline-based)
- Header/footer deduplication with chapter-level organization
- Edge text detection and deduplication
- Content similarity grouping

#### Summary Extraction
- Automatic summary generation
- Rule-based heading, footnote, and annotation extraction
- Table of contents generation
- Key point extraction
- Optional AI-assisted summarization (extensible)

#### Markdown Generation
- Single-file and multi-file output formats
- Smart output format detection
- Table formatting with alignment support
- Image link management
- Resource organization (docs/, assets/)
- Anchor-based section linking

#### Command-Line Interface
- Click-based CLI with comprehensive options
- OCR mode selection (auto/always/never)
- Configurable OCR thresholds
- Image quality and size controls
- Verbose and resume modes
- Progress tracking

#### Utilities
- Singleton logger with configurable levels
- File manager with validation and disk space checks
- Progress tracker with checkpoint support
- File hash calculation for resume validation

#### Documentation
- Comprehensive API documentation
- Usage examples and best practices guide
- Troubleshooting guide
- Contributing guidelines
- Bilingual project documentation (English/Chinese)

#### Testing
- Unit tests for all major modules
- Integration tests for pipeline and CLI
- 54 tests passing (base modules)
- Mock-based testing for external dependencies

### Performance
- Memory-efficient streaming architecture
- Lazy resource initialization
- Configurable image quality for memory/quality trade-off
- Two-pass processing strategy

### Dependencies
- pdfplumber >= 0.10.0
- pdf2image >= 1.16.0
- paddleocr >= 2.7.0
- Pillow >= 10.0.0
- click >= 8.1.0

### Python Support
- Python 3.8+
- Python 3.9
- Python 3.10
- Python 3.11

### Configuration
- pyproject.toml for modern Python packaging
- requirements.txt for dependency management
- pytest configuration with coverage support
- Code quality tools (black, isort, mypy)

### Known Limitations
- OCR requires additional system dependencies (Poppler)
- Large files (>200MB) require compression
- AI summarization requires additional configuration
- Complex PDF layouts may require manual adjustment

### Future Plans
- GPU-accelerated OCR support
- Additional OCR engine support (Tesseract)
- Advanced table formatting
- PDF outline integration
- Web UI
- Plugin system for custom extractors

[Unreleased]: https://github.com/yourusername/pdf2md/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/pdf2md/releases/tag/v0.1.0