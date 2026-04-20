# PDF 转 Markdown 工具

[![版本](https://img.shields.io/badge/版本-0.1.0-blue)](https://github.com/yourusername/pdf2md/releases)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![许可证](https://img.shields.io/badge/许可证-MIT-green)](https://github.com/yourusername/pdf2md/blob/main/LICENSE)
[![构建](https://img.shields.io/badge/构建-通过-brightgreen)](https://github.com/yourusername/pdf2md)

一个基于 Python 的 PDF 转 Markdown 工具，支持多语言 OCR（中/英）、高保真格式保留和关键信息摘要提取。

## 功能特性

- **多语言 OCR**：支持中文（简体/繁体）和英文文本提取
- **混合 PDF 类型**：同时处理数字化创建的文档和扫描文档
- **高保真格式**：保留字体、颜色、复杂布局，在 Markdown 中嵌入 HTML
- **摘要提取**：提取关键信息用于索引，并链接到详细章节
- **高效处理**：流式架构处理大文件（1MB-200MB），内存占用低
- **批量处理**：转换单个文件或整个目录
- **断点续传**：检查点系统支持中断后继续处理
- **智能去重**：自动去除重复的页眉/页脚，合理放置边缘文本

## 安装

### 系统要求

- Python 3.8+
- Poppler（用于 pdf2image）

### 安装依赖

```bash
# 核心依赖
pip install pdfplumber pdf2image paddleocr Pillow click

# 可选依赖
pip install tesseract openai
```

### 安装 Poppler

**macOS:**
```bash
brew install poppler
```

**Ubuntu/Debian:**
```bash
sudo apt-get install poppler-utils
```

**Windows:**
从 [Poppler Windows builds](https://github.com/oschwartz10612/poppler-windows/releases/) 下载

## 使用方法

### 命令行接口

```bash
# 转换单个 PDF 文件
python pdf2md.py -input ./input/report.pdf

# 转换目录中的所有 PDF
python pdf2md.py -input ./input/
```

### 输出结构

**单个文件输出：**
```
./input/report.md
```

**多个文件输出：**
```
./input/report_md/
├── report.md              # 主文件，包含摘要和锚点链接
├── docs/
│   ├── section1.md        # 详细内容章节
│   ├── section2.md
│   └── ...
└── assets/
    ├── page5_image1.png   # 提取的图片
    ├── page12_chart.png
    └── ...
```

## 架构设计

工具采用模块化流式流水线：

```
输入 PDF → 页面分割器 → 内容提取器 → OCR 引擎 →
摘要器 → Markdown 生成器 → 输出文件
```

### 核心组件

- **Core 模块**：流水线编排和逐页处理
- **OCR 模块**：多语言文本提取，支持按需调用
- **Markdown 模块**：高保真 Markdown 生成
- **Summary 模块**：关键信息提取和索引
- **Utils 模块**：去重、图片处理和进度跟踪

## 开发

### 运行测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行单元测试
python -m pytest tests/unit/

# 运行集成测试
python -m pytest tests/integration/

# 运行测试并生成覆盖率报告
python -m pytest tests/ --cov=pdf2md --cov-report=html
```

### 项目结构

```
pdf2md/
├── core/              # PDF 处理引擎
├── ocr/               # OCR 引擎（可插拔）
├── markdown/          # Markdown 生成器
├── summary/           # 摘要提取
├── utils/             # 共享工具
├── cli/               # 命令行接口
└── pdf2md.py          # 入口文件
```

## 许可证

[请指定您的许可证]

## 文档

- [CLAUDE.md](./CLAUDE.md) - 项目开发指南
- [docs/PROGRESS.md](./docs/PROGRESS.md) - 项目进度跟踪和里程碑
- [docs/LESSONS.md](./docs/LESSONS.md) - 经验教训和最佳实践
- [docs/superpowers/specs/](./docs/superpowers/specs/) - 详细设计规范