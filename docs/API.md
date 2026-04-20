# PDF 转 Markdown 工具 - API 文档

本文档提供 pdf2md 工具的完整 API 参考。

---

## 目录

- [Utils 模块](#utils-模块)
- [OCR 模块](#ocr-模块)
- [Extractor 模块](#extractor-模块)
- [Core 模块](#core-模块)
- [Deduplicator 模块](#deduplicator-模块)
- [Summary 模块](#summary-模块)
- [Markdown 模块](#markdown-模块)
- [CLI 模块](#cli-模块)

---

## Utils 模块

### Logger

日志记录工具，提供统一的日志接口。

```python
from pdf2md.utils import get_logger

logger = get_logger()
logger.info("Information message")
logger.warning("Warning message")
logger.error("Error message")
logger.debug("Debug message")
logger.set_level("DEBUG")
```

#### 方法

- `info(msg, *args, **kwargs)` - 记录信息日志
- `warning(msg, *args, **kwargs)` - 记录警告日志
- `error(msg, *args, **kwargs)` - 记录错误日志
- `debug(msg, *args, **kwargs)` - 记录调试日志
- `set_level(level)` - 设置日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### FileManager

文件管理工具，处理文件操作和目录管理。

```python
from pdf2md.utils import FileManager

fm = FileManager(output_dir="/output")
pdf_files = fm.scan_directory("/input")
fm.create_output_structure("/output")
```

#### 方法

- `scan_directory(directory)` - 扫描目录中的 PDF 文件
- `create_output_structure(base_path, create_dir=True)` - 创建输出目录结构
- `get_output_path(input_path)` - 获取输出路径
- `get_single_file_output_path(input_path)` - 获取单文件输出路径
- `handle_overwrite(path, overwrite=True)` - 处理文件覆盖
- `check_disk_space(path, required_mb=1000)` - 检查磁盘空间
- `get_file_hash(file_path)` - 计算文件 SHA256 哈希
- `validate_pdf(file_path, max_size_mb=200)` - 验证 PDF 文件

### ProgressTracker

进度跟踪工具，支持断点续传。

```python
from pdf2md.utils import ProgressTracker

tracker = ProgressTracker(checkpoint_dir="/checkpoints")
tracker.start("/path/to/file.pdf")
tracker.update(0.5, "Processing")
tracker.complete()
```

#### 方法

- `start(file_path)` - 开始跟踪文件处理
- `update(progress, message="")` - 更新进度
- `complete()` - 标记完成
- `save_checkpoint(file_path, total_pages, processed_pages, failed_pages)` - 保存检查点
- `load_checkpoint(file_path)` - 加载检查点
- `remove_checkpoint(file_path)` - 移除检查点
- `get_processed_pages(file_path)` - 获取已处理页面
- `get_failed_pages(file_path)` - 获取失败页面
- `should_process_page(file_path, page_num)` - 检查是否需要处理页面
- `is_page_failed(file_path, page_num)` - 检查页面是否失败

---

## OCR 模块

### OCRResult

OCR 处理结果数据类。

```python
from pdf2md.ocr import OCRResult

result = OCRResult(
    text="Extracted text",
    confidence=0.85,
    language="en",
    boxes=[[0, 0, 100, 50]]
)
```

#### 属性

- `text` - 提取的文本
- `confidence` - 置信度 (0.0 - 1.0)
- `language` - 检测的语言代码
- `boxes` - 文本区域边界框

#### 方法

- `is_empty()` - 检查结果是否为空

### OCREngine

OCR 引擎抽象基类。

```python
from pdf2md.ocr import OCREngine
from PIL import Image

class MyOCREngine(OCREngine):
    def extract_text(self, image: Image.Image) -> OCRResult:
        # 实现文本提取逻辑
        pass

    def supported_languages(self) -> List[str]:
        return ["en", "zh"]
```

#### 方法

- `extract_text(image)` - 提取图像中的文本 (抽象方法)
- `supported_languages()` - 获取支持的语言列表 (抽象方法)
- `needs_ocr(page_text, has_images, image_area_ratio, typical_page_length)` - 判断是否需要 OCR
- `preprocess_image(image)` - 预处理图像
- `_calculate_confidence(text)` - 计算置信度

### PaddleOCR

PaddleOCR 实现的 OCR 引擎。

```python
from pdf2md.ocr import PaddleOCR

ocr_engine = PaddleOCR(
    use_gpu=False,
    lang="ch"  # 'ch' for Chinese, 'en' for English
)
result = ocr_engine.extract_text(image)
```

---

## Extractor 模块

### TextElement

文本元素数据类。

```python
from pdf2md.extractor import TextElement

element = TextElement(
    text="Hello",
    x0=0.0,
    y0=0.0,
    x1=30.0,
    y1=10.0,
    font_name="Arial",
    font_size=12.0,
    is_bold=True
)
```

#### 属性

- `text` - 文本内容
- `x0, y0, x1, y1` - 边界框坐标
- `font_name` - 字体名称
- `font_size` - 字体大小
- `font_color` - 字体颜色
- `is_bold` - 是否加粗
- `is_italic` - 是否斜体

#### 方法

- `is_heading(min_font_size=14.0)` - 检查是否为标题
- `is_centered(page_width, tolerance=0.1)` - 检查是否居中
- `width` - 获取元素宽度
- `height` - 获取元素高度

### PageText

页面文本数据类。

```python
from pdf2md.extractor import PageText

page_text = PageText(
    elements=[element1, element2],
    raw_text="Extracted text"
)
```

#### 方法

- `get_text_by_position(x0, y0, x1, y1)` - 获取指定区域的文本
- `get_headings(min_font_size=14.0)` - 获取所有标题
- `get_large_font_elements(min_font_size=16.0)` - 获取大字体元素

### TextExtractor

文本提取器。

```python
from pdf2md.extractor import TextExtractor
import pdfplumber

extractor = TextExtractor(preserve_formatting=True)
page_text = extractor.extract(page)
```

#### 方法

- `extract(page)` - 从 PDF 页面提取文本
- `get_text_statistics(page_text)` - 获取文本统计信息

### ImageInfo

图像信息数据类。

```python
from pdf2md.extractor import ImageInfo

image_info = ImageInfo(
    path="/path/to/image.png",
    x0=0.0,
    y0=0.0,
    x1=100.0,
    y1=100.0,
    page_number=1
)
```

### ImageExtractor

图像提取器。

```python
from pdf2md.extractor import ImageExtractor

extractor = ImageExtractor(
    output_dir="/output",
    max_width=1920,
    quality=85
)
images = extractor.extract(page)
```

### Table

表格数据类。

```python
from pdf2md.extractor import Table

table = Table(
    cells=[cell1, cell2],
    num_rows=3,
    num_cols=2
)
```

#### 方法

- `get_cell(row, col)` - 获取指定单元格

### TableExtractor

表格提取器。

```python
from pdf2md.extractor import TableExtractor

extractor = TableExtractor()
tables = extractor.extract(page)
```

### TextRegion

文本区域数据类。

```python
from pdf2md.extractor import TextRegion, TextRegionType

region = TextRegion(
    region_type=TextRegionType.BODY,
    text="Body text",
    x0=0.0,
    y0=0.0,
    x1=500.0,
    y1=700.0
)
```

### LayoutAnalyzer

布局分析器。

```python
from pdf2md.extractor import LayoutAnalyzer

analyzer = LayoutAnalyzer()
layout = analyzer.analyze(page)
```

---

## Core 模块

### PageData

页面数据数据类。

```python
from pdf2md.core.page_processor import PageData

page_data = PageData(
    page_number=1,
    text=page_text,
    images=[],
    tables=[],
    layout=layout,
    text_statistics=stats
)
```

### PageProcessor

页面处理器。

```python
from pdf2md.core.page_processor import PageProcessor

processor = PageProcessor(
    text_extractor=text_extractor,
    image_extractor=image_extractor,
    table_extractor=table_extractor,
    layout_analyzer=layout_analyzer
)
page_data = processor.process(page, page_number=1)
```

### ResourceManager

资源管理器（单例）。

```python
from pdf2md.core.resource_manager import ResourceManager

manager = ResourceManager.instance()
ocr_engine = manager.get_ocr_engine()
```

#### 方法

- `instance()` - 获取单例实例
- `get_ocr_engine()` - 获取 OCR 引擎
- `get_table_formatter()` - 获取表格格式化器
- `cleanup()` - 清理资源

### ProcessResult

处理结果数据类。

```python
from pdf2md.core import ProcessResult

result = ProcessResult(
    success=True,
    file_path="/input/file.pdf",
    total_pages=10,
    processed_pages=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    failed_pages=[],
    output_dir="/output/file_md",
    error_message=None
)
```

### Pipeline

主流水线。

```python
from pdf2md.core import Pipeline
from pdf2md.utils import FileManager

pipeline = Pipeline(
    file_manager=FileManager(),
    enable_ocr=True,
    ocr_config={"min_chars": 100, "min_ratio": 0.05},
    image_config={"max_width": 1920, "quality": 85}
)

# 处理单个文件
result = pipeline.process_file("/input/file.pdf")

# 处理目录
results = pipeline.process_directory("/input/")

# 清理资源
pipeline.cleanup()
```

#### 方法

- `process_file(file_path, resume=False)` - 处理单个 PDF 文件
- `process_directory(directory)` - 处理目录中的所有 PDF 文件
- `cleanup()` - 清理资源

---

## Deduplicator 模块

### ChapterBoundary

章节边界数据类。

```python
from pdf2md.deduplicator import ChapterBoundary

boundary = ChapterBoundary(
    chapter_number=1,
    page_number=5,
    title="Introduction",
    heading_element=heading,
    is_detected_by="pattern"
)
```

### ChapterDetector

章节检测器。

```python
from pdf2md.deduplicator import ChapterDetector

detector = ChapterDetector(
    min_font_size=14.0,
    center_tolerance=0.1,
    use_outline=True
)
boundaries = detector.detect_chapters(pages_data, pdf_outline)
```

#### 方法

- `detect_chapters(pages_data, pdf_outline)` - 检测章节边界
- `get_chapter_pages(boundaries, total_pages)` - 获取章节页面范围
- `get_page_chapter(page_number, boundaries)` - 获取页面所属章节
- `has_chapters(pages_data)` - 检查文档是否有章节

### HeaderFooterContent

页眉页脚内容数据类。

```python
from pdf2md.deduplicator import HeaderFooterContent

content = HeaderFooterContent(
    content="Page 1",
    page_numbers=[1, 2, 3],
    frequency=3,
    is_header=True
)
```

#### 方法

- `is_candidate_for_deduplication(min_frequency=2)` - 检查是否需要去重

### HeaderFooterDeduplicator

页眉页脚去重器。

```python
from pdf2md.deduplicator import HeaderFooterDeduplicator

deduplicator = HeaderFooterDeduplicator(
    min_frequency=2,
    similarity_threshold=0.9,
    ignore_page_numbers=True
)
deduplicated = deduplicator.deduplicate(pages_data, chapter_boundaries)
```

#### 方法

- `deduplicate(pages_data, chapter_boundaries)` - 去重页眉页脚
- `get_unique_headers(pages_data)` - 获取唯一页眉
- `get_unique_footers(pages_data)` - 获取唯一页脚

### EdgeText

边缘文本数据类。

```python
from pdf2md.deduplicator import EdgeText

edge_text = EdgeText(
    text="Note",
    page_number=1,
    position="left",
    x0=10.0,
    y0=50.0,
    x1=50.0,
    y1=100.0
)
```

### EdgeTextHandler

边缘文本处理器。

```python
from pdf2md.deduplicator import EdgeTextHandler

handler = EdgeTextHandler(
    edge_margin=30.0,
    deduplicate_across_pages=True
)
edge_texts = handler.extract_edge_text(pages_data)
formatted = handler.format_edge_text(edge_texts, format="markdown")
```

#### 方法

- `extract_edge_text(pages_data)` - 提取边缘文本
- `format_edge_text(edge_texts, format="markdown")` - 格式化边缘文本
- `remove_edge_text_from_body(pages_data, edge_texts)` - 从正文中移除边缘文本

---

## Summary 模块

### Summary

文档摘要数据类。

```python
from pdf2md.summary import Summary

summary = Summary(
    title="Document Title",
    headings=["Chapter 1", "Chapter 2"],
    key_points=["Point 1", "Point 2"],
    page_count=10,
    word_count=5000,
    table_of_contents=[],
    footnotes=[],
    annotations=[]
)
```

#### 方法

- `to_markdown()` - 转换为 Markdown 格式

### SummaryItem

摘要项数据类。

```python
from pdf2md.summary import SummaryItem

item = SummaryItem(
    item_type="heading",
    text="Chapter 1",
    page_number=1,
    position="header",
    confidence=0.9,
    context="Font size: 16pt"
)
```

### SummaryExtractor

摘要提取器。

```python
from pdf2md.summary import SummaryExtractor

extractor = SummaryExtractor(enable_ai=False)
summary = extractor.extract_summary(
    pages_data,
    source_file="/input/file.pdf",
    summary_type="rule_based"
)
```

#### 方法

- `extract_summary(pages_data, source_file, summary_type)` - 提取摘要
- `generate_toc(summaries)` - 生成目录
- `get_summary_statistics(summary)` - 获取摘要统计

### RuleBasedExtractor

基于规则的提取器。

```python
from pdf2md.summary import RuleBasedExtractor

extractor = RuleBasedExtractor(min_heading_font_size=14.0)
summaries = extractor.extract_summaries(pages_data)
```

#### 方法

- `extract_summaries(pages_data)` - 提取摘要项
- `extract_headings_by_level(pages_data, max_level)` - 按级别提取标题
- `generate_index(summaries)` - 生成索引
- `filter_by_type(summaries, item_type)` - 按类型过滤
- `filter_by_page_range(summaries, start_page, end_page)` - 按页码范围过滤

---

## Markdown 模块

### TableFormatter

表格格式化器。

```python
from pdf2md.markdown import TableFormatter

formatter = TableFormatter(max_column_width=100)
markdown_table = formatter.format_table(table)
```

#### 方法

- `format_table(table)` - 格式化单个表格
- `format_table_list(tables)` - 格式化多个表格
- `format_with_alignment(table, alignments)` - 带对齐方式格式化表格
- `calculate_column_widths(table)` - 计算列宽

### Linker

链接管理器。

```python
from pdf2md.markdown import Linker
from pathlib import Path

linker = Linker(base_path=Path("/output"))
image_link = linker.create_image_link(image_info, Path("/output"))
section_link = linker.create_section_link("Section Title", "docs/section1.md")
```

#### 方法

- `create_image_link(image_info, output_dir)` - 创建图像链接
- `create_image_link_with_size(image_info, max_width, output_dir)` - 创建带大小的图像链接
- `create_section_link(section_title, section_file, anchor)` - 创建章节链接
- `create_toc_link(section_title, section_file, page_number)` - 创建目录链接
- `create_image_gallery(images, output_dir, columns)` - 创建图像画廊
- `update_image_links(markdown, image_mappings)` - 更新图像链接

### MarkdownGenerator

Markdown 生成器。

```python
from pdf2md.markdown import MarkdownGenerator

generator = MarkdownGenerator(
    table_formatter=formatter,
    linker=linker
)
generator.generate_main_file(
    pages_data,
    source_file="/input/file.pdf",
    output_dir=Path("/output"),
    document_summary=summary
)
```

#### 方法

- `generate_main_file(pages_data, source_file, output_dir, document_summary)` - 生成主文件
- `generate_single_file(pages_data, source_file, output_dir, document_summary)` - 生成单文件
- `generate_detail_files(pages_data, source_file, output_dir, chapters)` - 生成详细文件

---

## CLI 模块

### 命令行接口

```bash
# 基本用法
pdf2md -input ./input/file.pdf

# 指定输出目录
pdf2md -input ./input/file.pdf -output ./output/

# 批量处理目录
pdf2md -input ./input/

# OCR 模式
pdf2md -input ./input/file.pdf --ocr-mode always

# 自定义 OCR 阈值
pdf2md -input ./input/file.pdf --ocr-min-chars 150 --ocr-min-ratio 0.1

# 图像质量设置
pdf2md -input ./input/file.pdf --image-quality 90 --max-image-width 2560

# 详细输出
pdf2md -input ./input/file.pdf -v

# 断点续传
pdf2md -input ./input/file.pdf --resume
```

#### 选项

| 选项 | 描述 | 默认值 |
|------|------|--------|
| `-input` | 输入 PDF 文件或目录路径 | 必需 |
| `-output` | 输出目录路径 | 输入文件目录 |
| `--ocr-mode` | OCR 模式 (auto/always/never) | auto |
| `--ocr-min-chars` | OCR 最小字符数 | 100 |
| `--ocr-min-ratio` | OCR 最小文本比例 | 0.05 |
| `--ocr-image-ratio` | OCR 最大图像比例 | 0.80 |
| `--image-quality` | 图像质量 (1-100) | 85 |
| `--max-image-width` | 最大图像宽度（像素） | 1920 |
| `--memory-monitor` | 启用内存监控 | False |
| `--verbose, -v` | 详细输出 | False |
| `--resume` | 从检查点恢复 | False |

---

## 示例代码

### 基本使用

```python
from pdf2md.core import Pipeline
from pdf2md.utils import FileManager

# 创建流水线
pipeline = Pipeline(
    file_manager=FileManager(),
    enable_ocr=True
)

# 处理文件
result = pipeline.process_file("/path/to/file.pdf")

# 检查结果
if result.success:
    print(f"处理完成！输出目录: {result.output_dir}")
else:
    print(f"处理失败: {result.error_message}")

# 清理资源
pipeline.cleanup()
```

### 自定义 OCR 配置

```python
from pdf2md.core import Pipeline
from pdf2md.utils import FileManager

pipeline = Pipeline(
    file_manager=FileManager(output_dir="/custom/output"),
    enable_ocr=True,
    ocr_config={
        "min_chars": 150,
        "min_ratio": 0.1,
        "max_image_ratio": 0.7
    },
    image_config={
        "max_width": 2560,
        "quality": 90
    }
)
```

### 批量处理

```python
from pdf2md.core import Pipeline
from pdf2md.utils import FileManager

pipeline = Pipeline(file_manager=FileManager())

results = pipeline.process_directory("/path/to/pdfs/")

for result in results:
    if result.success:
        print(f"✓ {result.file_path}: {len(result.processed_pages)}/{result.total_pages}")
    else:
        print(f"✗ {result.file_path}: {result.error_message}")
```

---

## 错误处理

所有处理操作都返回 `ProcessResult` 对象，包含以下信息：

```python
if result.success:
    # 处理成功
    print(f"已处理 {len(result.processed_pages)} 页")
else:
    # 处理失败
    print(f"错误: {result.error_message}")
    print(f"失败页面: {result.failed_pages}")
```

常见错误类型：
- `FileNotFoundError` - 文件不存在
- `ValueError` - 无效的文件类型或参数
- `RuntimeError` - 处理过程中出现错误
- `MemoryError` - 内存不足