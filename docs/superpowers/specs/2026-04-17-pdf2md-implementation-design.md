# PDF 转 Markdown 工具设计文档

**日期**: 2026-04-17
**状态**: 已批准
**方案**: 模块化流水线架构

## 概述

基于 Python 的 PDF 转 Markdown 工具，支持：
- 混合 PDF 类型（数字化创建和扫描文档）
- 多语言 OCR（中/英）
- 高保真格式保留
- 关键摘要提取便于索引
- 高效处理大文件（1MB-200MB）

## 需求

### 功能需求

1. **内容提取**
   - 提取页面中的文本、图片、表格
   - OCR 提取图片中的文字
   - 保留图片并建立链接引用关系

2. **摘要提取**
   - 提取关键信息用于索引
   - 生成带链接的摘要到详细章节
   - 财务报表等文档提取标题、附注、标注

3. **格式保留**
   - 高保真保留格式（字体、颜色、复杂布局）
   - 表格转换为 Markdown 格式
   - 保留页眉、页脚、边缘文字

4. **去重处理**
   - 识别跨页章节中重复的页眉、页脚
   - 去重后放到该章节级别
   - 边缘文字单独放到页末

5. **输出组织**
   - 统一输出到 `./input/xx_md/` 目录结构
   - 结构: `xx.md` (主), `docs/` (详情), `assets/` (图片)
   - 覆盖已存在的文件
   - 小文档（<5页）可配置为输出单文件

6. **CLI 接口**
   - 命令: `python pdf2md.py -input ./input/xx.pdf`
   - 支持目录批量处理
   - 清晰的错误消息和进度报告

### 非功能需求

- **资源效率**: 最小化大文件的内存使用
- **性能**: 逐页流式处理处理 200MB+ 文件
- **可靠性**: 优雅的错误处理和恢复
- **可维护性**: 模块化、可测试的架构

## 架构

### 高层设计

流式流水线架构，包含模块化阶段：

```
输入 PDF → 页面分割器 → 内容提取器 → OCR 引擎 →
去重器 → 摘要提取器 → Markdown 生成器 → 输出文件
```

### 核心原则

1. **流式**: 逐页处理以最小化内存使用
2. **两遍处理**: 第一遍流式提取基础内容，第二遍处理跨页面分析（去重、章节检测）
3. **按需 OCR**: 仅对包含扫描图像的页面调用 OCR
4. **模块化阶段**: 每个组件职责单一
5. **资源池化**: 跨页面重用 OCR 引擎和格式化器

### 组件分解

```
pdf2md/
├── core/              # PDF 处理引擎
│   ├── pipeline.py
│   ├── page_processor.py
│   └── resource_manager.py
├── ocr/               # OCR 引擎（可插拔）
│   ├── base.py
│   └── paddleocr.py
├── extractor/         # 内容提取
│   ├── text_extractor.py
│   ├── image_extractor.py
│   ├── table_extractor.py
│   └── layout_analyzer.py
├── deduplicator/      # 去重
│   ├── chapter_detector.py
│   ├── header_footer.py
│   └── edge_text.py
├── summary/           # 摘要提取
│   ├── extractor.py
│   ├── rule_based.py
│   └── ai_assistant.py
├── markdown/          # Markdown 生成
│   ├── generator.py
│   ├── table_formatter.py
│   └── linker.py
├── utils/             # 共享工具
│   ├── logger.py
│   ├── file_manager.py
│   └── progress.py
├── cli/               # 命令行接口
│   └── main.py
└── pdf2md.py          # 入口点
```

## 组件详情

### Core 模块

**目的**: 流水线编排和页面管理

**关键类**:

- `Pipeline`: 主编排器，编排处理工作流
  - `process_file(file_path)`: 处理单个 PDF 文件
  - `process_directory(dir_path)`: 批量处理多个 PDF
  - `get_stage_results()`: 获取各阶段处理结果
  - `cleanup()`: 处理完成后释放资源

- `PageProcessor`: 处理单个页面
  - `process_page(page, page_num)`: 通过流水线处理单页
  - 返回结构化页面数据：文本、图片、表格、布局

- `ResourceManager`: 管理共享资源
  - `get_ocr_engine()`: 获取或创建 OCR 引擎实例
  - `cleanup()`: 释放所有资源

### Extractor 模块

**目的**: 从 PDF 页面提取内容

**关键类**:

- `TextExtractor`: 提取文本内容
  - `extract_text(page)`: 提取文本元素
  - 保留字体、颜色、位置信息

- `ImageExtractor`: 提取和处理图片
  - `extract_image(page, output_dir)`: 提取并保存图片
  - 优化图片大小/质量
  - 默认配置: PNG 格式，最大宽度 1920px，质量 85%
  - 可通过 CLI 参数配置

- `TableExtractor`: 提取表格数据
  - `extract_tables(page)`: 提取表格
  - 处理合并单元格
  - 回退策略: 解析失败时提取为纯文本块，保留表格结构标记

- `LayoutAnalyzer`: 分析页面布局
  - `analyze_layout(page)`: 识别页眉、页脚、边缘文本位置

### OCR 模块

**目的**: 从图像提取多语言文本

**关键类**:

- `OCREngine` (抽象基类):
  - `needs_ocr(page, extracted_text)`: 检测是否需要 OCR
  - `extract_text(image)`: 从图像提取文本
  - `supported_languages`: 返回支持的语言代码

- `PaddleOCREngine`: PaddleOCR 实现
  - 支持中文（简体/繁体）和英文
  - 自动语言检测
  - 图像预处理（旋转、对比度）

**OCR 触发条件**（可配置）:

默认阈值（基于经验）:
- 文本提取完全失败（返回空或 None）
- 提取文本少于 100 字符或少于典型页面文本量的 5%
- 页面主要包含图片，可选择性文本极少
- 图像元素占据超过 80% 的页面区域

配置选项:
- `--ocr-min-chars`: 最小字符数阈值（默认: 100）
- `--ocr-min-ratio`: 最小文本占比（默认: 0.05）
- `--ocr-image-ratio`: 最大图像占比触发 OCR（默认: 0.80）
- `--ocr-mode`: OCR 模式（auto/always/never，默认: auto）

这些阈值基于以下原则确定:
- 100 字符: 典型英文段落的一半，过滤掉只有标题/页码的页面
- 5% 比例: 空白页面或大量图片页面的典型特征
- 80% 图像占比: 扫描文档的常见特征

### Deduplicator 模块

**目的**: 处理页眉/页脚和边缘文本的去重

**关键类**:

- `ChapterDetector`: 章节边界检测
  - `detect_chapters(pages)`: 识别章节边界
  - 综合检测：
    - H1 级标题（字体 > 16pt，居中/顶部位置）
    - 匹配章节号模式（Chapter 1, 第一章等）
    - 使用 PDF 大纲信息（如果有）

- `HeaderFooterDeduplicator`: 页眉/页脚去重
  - `deduplicate(pages, chapters)`: 去重页眉/页脚
  - 识别跨页重复内容
  - 去重后放到章节级别

- `EdgeTextHandler`: 边缘文本处理
  - `handle_edge_text(pages)`: 处理边缘文本
  - 去重后放到页末

### Summary 模块

**目的**: 提取关键信息用于索引

**关键类**:

- `SummaryExtractor`: 主协调器
  - `extract_summaries(pages)`: 提取所有页面的摘要
  - `generate_toc()`: 创建带锚点的目录
  - `create_index()`: 创建可搜索索引

- `RuleBasedExtractor`: 基于规则的提取
  - `extract_headings(page)`: 识别标题和副标题
  - `extract_annotations(page)`: 查找页脚和标注
  - `detect_chapters(pages)`: 识别章节边界

- `AIAssistant`: AI 辅助摘要（可选）
  - `generate_summary(content)`: AI 生成摘要
  - 可使用 OpenAI API 或本地模型
  - 回退策略: AI 不可用或失败时，仅使用规则提取

**输出结构**:
- 主文件包含带锚点链接的摘要
- 详细章节拆分到 docs/ 中的独立文件
- 主文件顶部有目录

### Markdown 模块

**目的**: 高保真 Markdown 生成

**关键类**:

- `MarkdownGenerator`: 主生成器
  - `generate_page(page_data)`: 将页面转换为 Markdown
  - `format_text(text, style)`: 用样式格式化文本
  - `format_html(html)`: 在需要时保留复杂 HTML

- `TableFormatter`: 表格转换
  - `format_table(table_data)`: 将表格转换为 Markdown
  - `handle_merged_cells()`: 处理复杂表格结构
  - `apply_alignment()`: 保留列对齐

- `Linker`: 资源链接管理
  - `create_image_link(image_info)`: 生成相对 markdown 链接
  - `create_section_link(section)`: 创建章节锚点链接

### Utils 模块

**目的**: 共享工具和助手

**关键组件**:

- `Logger`: 日志工具
  - `info(msg)`: 信息日志
  - `warning(msg)`: 警告日志
  - `error(msg)`: 错误日志

- `FileManager`: 批量文件处理
  - `scan_directory(path)`: 查找所有 PDF 文件
  - `create_output_structure(base_path)`: 创建输出目录
  - `handle_overwrites()`: 管理文件覆盖

- `ProgressTracker`: 进度跟踪
  - `start(file)`: 开始跟踪文件处理
  - `update(progress)`: 更新进度
  - `complete()`: 标记完成

## 数据流

### 两遍处理策略

由于章节检测、页眉/页脚去重和边缘文本处理需要分析多个页面，采用两遍处理策略：

**第一遍 - 流式提取**:
- 逐页加载和释放内存
- 提取基础内容（文本、图片、表格）
- 执行 OCR（如需要）
- 保存轻量级元数据到缓冲区
- 内存占用稳定，适合大文件

**第二遍 - 批量分析**:
- 基于第一遍的元数据进行跨页面分析
- 章节边界检测
- 页眉/页脚去重
- 边缘文本处理
- 摘要提取和索引生成

内存占用分析:
- 第一遍: 单页数据量 × 1（当前页）
- 第二遍: 单页元数据量 × 总页数（元数据远小于原始数据）
- 总内存使用: < 500MB 用于 100MB PDF（5倍压缩比）

### 单文件处理

```
输入: ./input/report.pdf

1. 输入验证
   - 检查文件存在
   - 验证大小 < 200MB
   - 验证 PDF 格式

2. PDF 流式加载
   - 使用 pdfplumber 逐页迭代
   - 每次只处理一页
   - 及时释放内存

3. 对每页:
   a. ContentExtractor
      - 提取页面内容
      - 提取文本、图片、表格
      - 分析布局（页眉、页脚、边缘文本位置）

   b. OCR 检查
      - 如果扫描或文本极少 → 调用 OCR
      - OCR 超时: 30秒，重试1次
      - 否则使用提取的文本

   c. 保存轻量级元数据到缓冲区
      - 页面标题、文本片段
      - 页眉/页脚候选内容
      - 布局位置信息

=== 第二遍：批量分析和生成 ===

4. 章节边界检测
   - 基于元数据综合分析
   - H1 标题检测（字体 > 16pt，居中/顶部）
   - 章节号模式匹配
   - PDF 大纲信息（如果有）

5. 去重处理
   - 页眉/页脚去重
   - 边缘文本处理
   - 按章节组织内容

6. 摘要提取
   - 提取所有章节的关键信息
   - 生成目录和索引
   - 可选 AI 增强摘要（如不可用则仅使用规则）

7. Markdown 生成
   - 格式化所有内容
   - 链接图片到 assets/
   - 创建章节锚点

8. 输出生成
   - 写入 report.md（主文件）
   - 拆分详细内容到 docs/
   - 创建 assets/ 目录
   - 保存优化后的图片（PNG，最大1920px，质量85%）

输出: ./input/report_md/
```

### 批量处理

```
输入: ./input/

1. 目录扫描
   - 查找所有 .pdf 文件
   - 验证每个文件

2. 批处理队列
   - 顺序处理文件（避免内存压力）
   - 跟踪进度
   - 每个文件独立处理，互不干扰

3. 对每个 PDF
   - 应用单文件流程
   - 创建每个文件的输出目录

4. 输出组织
   ./input/file1_md/
   ├── file1.md
   ├── docs/
   └── assets/

   ./input/file2_md/
   ├── file2.md
   ├── docs/
   └── assets/
```

### 输出文件结构

```
./input/report_md/
├── report.md              # 主文件：摘要 + 锚点
├── docs/
│   ├── section1.md        # 详细内容章节
│   ├── section2.md
│   └── ...
└── assets/
    ├── page_5_image_1.png # 提取的图片
    ├── page_12_chart.png
    └── ...
```

### 边缘情况处理

**小文档（1-2页）**:
- 不进行章节检测
- 所有内容放入主文件
- 可选单文件输出模式

**无章节检测**:
- 整个文档作为单个章节处理
- 页眉/页脚去重仍然生效
- 边缘文本仍放到文档末尾

**单页文档**:
- 跳过章节检测
- 跳过去重处理（无重复）
- 直接输出为单文件

**密码保护 PDF**:
- 尝试验证密码: 如果用户在命令行提供密码则使用
- 交互模式: 提示用户输入密码
- 失败回退: 记录错误，跳过该文件（批量模式）

**嵌入字体问题**:
- 尝试使用 pdfplumber 的字体渲染
- 失败时回退到基本文本提取
- 记录警告但不中断处理

**空页或空白页面**:
- 跳过空白页面（无文本、图片、表格）
- 在日志中记录
- 不影响页码连续性

## 错误处理

### 错误类别

**文件级错误**:
- 损坏的 PDF → 跳过，记录错误，继续批量处理
- 大小 > 200MB → 拒绝并显示清晰消息
- 权限被拒绝 → 记录错误，继续批量处理

**页面级错误**:
- OCR 超时 → 重试一次（30秒超时），然后用占位符跳过页面
- 图片提取失败 → 记录警告，继续
- 表格解析错误 → 回退到原始文本，记录警告
- 密码保护 → 提示输入密码或跳过文件

**输出级错误**:
- 目录创建失败 → 中止并显示清晰错误消息
- 磁盘空间 → 处理前检查，空间不足则中止
- 已存在的文件 → 按指定覆盖

### 日志策略

- **INFO**: 处理进度、已处理文件
- **WARNING**: 可恢复问题（OCR 重试、跳过页面）
- **ERROR**: 严重失败（损坏文件、I/O 错误）

### 进度跟踪

- 显示大文件的进度条
- 显示每个文件的处理状态
- 将警告和错误记录到控制台

### 内存使用目标

- 目标内存使用: < 500MB 用于处理 100MB PDF
- 监控模式: 可选 (--memory-monitor) 记录内存峰值
- 内存保护: 超过阈值时减少并发处理或优化缓冲区

### 性能目标

- 100MB PDF: 目标处理时间 < 60 秒
- 10 页简单文档: 目标处理时间 < 10 秒
- 扫描文档 OCR: 目标每页 < 5 秒

性能基准测试将验证这些目标，并根据实际硬件进行调整。

## 测试策略

### 测试组织

```
tests/
├── unit/                 # 组件级测试
│   ├── test_ocr.py       # OCR 引擎测试
│   ├── test_extractor.py # 内容提取测试
│   ├── test_deduplicator.py # 去重逻辑测试
│   └── test_markdown.py  # Markdown 生成器测试
├── integration/          # 流水线集成测试
│   ├── test_pipeline.py  # 端到端流水线测试
│   └── test_cli.py       # CLI 接口测试
└── fixtures/             # 测试用示例 PDF
    ├── small_text.pdf    # 简单文本 PDF
    ├── with_tables.pdf   # 带复杂表格的 PDF
    ├── scanned_doc.pdf   # 用于 OCR 的扫描文档
    └── multilingual.pdf  # 中英混合
```

### 单元测试重点

- **OCR 测试**: 模拟 OCR 响应，测试语言检测，验证预处理
- **提取器测试**: 验证文本、图片、表格提取
- **去重测试**: 跨页页眉/页脚检测
- **Markdown 测试**: 验证表格转换、图片链接、HTML 格式化
- **摘要测试**: 测试规则提取模式、标题检测

### 集成测试

- **流水线测试**: 处理完整 PDF，验证输出结构
- **CLI 测试**: 测试命令行参数、批量处理、错误处理
- **资源测试**: 用大文件验证内存使用

### 测试覆盖率

- 关键路径目标 80%+ 代码覆盖率
- 测试每个组件的快乐路径
- 测试错误条件和边缘情况

## 外部依赖

### 必需库

- `pdfplumber` - PDF 文本和表格提取
- `pdf2image` - 将 PDF 页面转换为图像用于 OCR
- `paddleocr` - 多语言 OCR（中/英）
- `Pillow` - 图像处理
- `click` - CLI 参数解析

### 可选依赖

- `openai` - 可选 AI 摘要

### 系统依赖

- Python 3.8+
- Poppler（用于 pdf2image）

## CLI 接口

### 命令结构

```bash
# 基本用法
python pdf2md.py -input ./input/report.pdf

# 批量处理
python pdf2md.py -input ./input/

# 配置选项
python pdf2md.py -input ./input/report.pdf \
    --ocr-mode auto \
    --ocr-min-chars 100 \
    --ocr-min-ratio 0.05 \
    --output-format multi \
    --image-quality 85 \
    --memory-monitor
```

### 可用选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `-input` | 必需 | 输入文件或目录路径 |
| `--ocr-mode` | auto | OCR 模式: auto/always/never |
| `--ocr-min-chars` | 100 | OCR 触发的最小字符数 |
| `--ocr-min-ratio` | 0.05 | OCR 触发的最小文本占比 |
| `--ocr-image-ratio` | 0.80 | OCR 触发的最大图像占比 |
| `--output-format` | auto | 输出格式: auto/multi/single |
| `--image-quality` | 85 | 图片质量 (1-100) |
| `--max-image-width` | 1920 | 图片最大宽度 (像素) |
| `--memory-monitor` | false | 启用内存监控 |
| `--verbose` | false | 详细输出模式 |
| `--help` | - | 显示帮助信息 |

### 输出行为

- `--output-format auto`: 自动选择（<5页单文件，≥5页多文件）
- `--output-format multi`: 总是创建目录结构 `./input/filename_md/`
- `--output-format single`: 输出单文件 `./input/filename.md`（不包含图片）
- 自动覆盖已存在的文件

### 进度报告

- 显示大文件的进度条
- 显示每个文件的处理状态
- 将警告和错误记录到控制台

## 实现优先级

1. **阶段 1**: 核心流水线和基本 PDF 文本提取
2. **阶段 2**: OCR 集成和图片处理
3. **阶段 3**: 表格提取和 Markdown 格式化
4. **阶段 4**: 摘要提取和索引
5. **阶段 5**: 去重和边缘文本处理
6. **阶段 6**: CLI 接口和批量处理
7. **阶段 7**: 测试和优化

## 未来增强

- 多文件并行处理
- 自定义摘要模板
- 额外的 OCR 后端
- 云存储集成
- Web API 接口