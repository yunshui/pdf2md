# PDF 转 Markdown 工具 - 使用示例

本文档提供 pdf2md 工具的详细使用示例和最佳实践。

---

## 目录

- [快速开始](#快速开始)
- [命令行使用](#命令行使用)
- [Python API 使用](#python-api-使用)
- [高级配置](#高级配置)
- [常见场景](#常见场景)
- [性能优化](#性能优化)
- [故障排除](#故障排除)

---

## 快速开始

### 安装

```bash
# 从源码安装
git clone https://github.com/yourusername/pdf2md.git
cd pdf2md
pip install -e .

# 或安装依赖
pip install pdfplumber pdf2image paddleocr Pillow click
```

### 基本使用

```bash
# 转换单个文件
pdf2md -input ./document.pdf

# 转换目录中的所有 PDF
pdf2md -input ./documents/

# 指定输出目录
pdf2md -input ./document.pdf -output ./output/
```

---

## 命令行使用

### 基本命令

```bash
# 最简单的用法
pdf2md -input report.pdf

# 指定输出目录
pdf2md -input report.pdf -output ./converted/

# 批量处理
pdf2md -input ./reports/
```

### OCR 配置

```bash
# 自动 OCR（默认）
pdf2md -input scanned.pdf --ocr-mode auto

# 始终使用 OCR
pdf2md -input scanned.pdf --ocr-mode always

# 禁用 OCR
pdf2md -input digital.pdf --ocr-mode never

# 自定义 OCR 触发阈值
pdf2md -input document.pdf \
    --ocr-min-chars 150 \
    --ocr-min-ratio 0.1 \
    --ocr-image-ratio 0.7
```

### 图像质量配置

```bash
# 高质量图像
pdf2md -input document.pdf \
    --image-quality 95 \
    --max-image-width 3840

# 中等质量（默认）
pdf2md -input document.pdf \
    --image-quality 85 \
    --max-image-width 1920

# 低质量（节省空间）
pdf2md -input document.pdf \
    --image-quality 70 \
    --max-image-width 1280
```

### 其他选项

```bash
# 详细输出（调试模式）
pdf2md -input document.pdf -v

# 启用内存监控
pdf2md -input large_document.pdf --memory-monitor

# 断点续传
pdf2md -input large_document.pdf --resume

# 查看版本信息
pdf2md --version

# 查看帮助
pdf2md --help
```

### 组合使用

```bash
# 完整示例：高质量转换，自定义 OCR，详细输出
pdf2md -input ./reports/annual_report.pdf \
    -output ./converted/ \
    --ocr-mode auto \
    --ocr-min-chars 100 \
    --image-quality 90 \
    --max-image-width 2560 \
    -v
```

---

## Python API 使用

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
result = pipeline.process_file("/path/to/document.pdf")

# 检查结果
if result.success:
    print(f"✓ 处理完成！")
    print(f"  总页数: {result.total_pages}")
    print(f"  已处理: {len(result.processed_pages)}")
    print(f"  输出目录: {result.output_dir}")
else:
    print(f"✗ 处理失败: {result.error_message}")

# 清理资源
pipeline.cleanup()
```

### 批量处理

```python
from pdf2md.core import Pipeline
from pdf2md.utils import FileManager

pipeline = Pipeline(
    file_manager=FileManager(output_dir="/output"),
    enable_ocr=True
)

# 处理目录中的所有 PDF
results = pipeline.process_directory("/input/pdfs/")

# 统计结果
success_count = 0
total_pages = 0

for result in results:
    if result.success:
        success_count += 1
        total_pages += len(result.processed_pages)
        print(f"✓ {result.file_path}: {len(result.processed_pages)} 页")
    else:
        print(f"✗ {result.file_path}: {result.error_message}")

print(f"\n总结: {success_count}/{len(results)} 文件成功，共 {total_pages} 页")

pipeline.cleanup()
```

### 自定义配置

```python
from pdf2md.core import Pipeline
from pdf2md.utils import FileManager

pipeline = Pipeline(
    file_manager=FileManager(output_dir="/custom/output"),
    enable_ocr=True,
    ocr_config={
        "min_chars": 150,           # OCR 最小字符数
        "min_ratio": 0.1,           # OCR 最小文本比例
        "max_image_ratio": 0.7      # OCR 最大图像比例
    },
    image_config={
        "max_width": 2560,          # 最大图像宽度
        "quality": 90               # 图像质量
    }
)

result = pipeline.process_file("/path/to/document.pdf")
pipeline.cleanup()
```

### 断点续传

```python
from pdf2md.core import Pipeline
from pdf2md.utils import FileManager

pipeline = Pipeline(file_manager=FileManager(), enable_ocr=True)

# 首次处理（可能会被中断）
result = pipeline.process_file("/path/to/large_document.pdf", resume=False)

# 从检查点恢复处理
result = pipeline.process_file("/path/to/large_document.pdf", resume=True)

pipeline.cleanup()
```

### 处理结果详情

```python
from pdf2md.core import Pipeline
from pdf2md.utils import FileManager

pipeline = Pipeline(file_manager=FileManager(), enable_ocr=False)
result = pipeline.process_file("/path/to/document.pdf")

if result.success:
    print("处理成功！")
    print(f"文件: {result.file_path}")
    print(f"总页数: {result.total_pages}")
    print(f"已处理: {len(result.processed_pages)}")
    print(f"失败页面: {result.failed_pages}")
    print(f"输出目录: {result.output_dir}")

    # 处理的页面列表
    print(f"页面列表: {result.processed_pages}")
else:
    print("处理失败！")
    print(f"错误信息: {result.error_message}")
    if result.failed_pages:
        print(f"失败页面: {result.failed_pages}")

pipeline.cleanup()
```

---

## 高级配置

### 使用自定义 OCR 引擎

```python
from pdf2md.ocr import OCREngine, OCRResult
from PIL import Image

class CustomOCREngine(OCREngine):
    def extract_text(self, image: Image.Image) -> OCRResult:
        # 实现自定义 OCR 逻辑
        text = "Custom extracted text"
        return OCRResult(
            text=text,
            confidence=0.8,
            language="en"
        )

    def supported_languages(self) -> list:
        return ["en"]

# 使用自定义引擎（需要修改 Pipeline 或直接使用组件）
```

### 禁用特定功能

```python
from pdf2md.core import Pipeline
from pdf2md.utils import FileManager

# 仅文本提取，无 OCR
pipeline = Pipeline(
    file_manager=FileManager(),
    enable_ocr=False
)

# 禁用摘要提取
# （在 Pipeline 中需要相应配置）
```

### 自定义输出格式

```python
from pdf2md.markdown import MarkdownGenerator, TableFormatter, Linker
from pathlib import Path

# 创建自定义生成器
formatter = TableFormatter(max_column_width=150)
linker = Linker(base_path=Path("/custom/output"))

generator = MarkdownGenerator(
    table_formatter=formatter,
    linker=linker
)

# 使用生成器（需要配合其他组件）
```

---

## 常见场景

### 场景 1: 处理扫描文档

```bash
pdf2md -input scanned_document.pdf \
    --ocr-mode always \
    -v
```

### 场景 2: 处理混合类型 PDF（文字 + 图像）

```bash
pdf2md -input mixed_document.pdf \
    --ocr-mode auto \
    --image-quality 90 \
    -output ./output/
```

### 场景 3: 处理大文件（断点续传）

```bash
# 首次处理
pdf2md -input large_document.pdf

# 如果中断，恢复处理
pdf2md -input large_document.pdf --resume
```

### 场景 4: 批量处理多个文件

```bash
# 处理整个目录
pdf2md -input ./reports/ -output ./converted/

# 使用脚本批量处理
for file in ./reports/*.pdf; do
    pdf2md -input "$file" -output ./converted/
done
```

### 场景 5: 提取文本表格（无图像）

```bash
pdf2md -input text_document.pdf \
    --ocr-mode never \
    --output ./text_only/
```

### 场景 6: 高质量图像保留

```bash
pdf2md -input image_heavy_document.pdf \
    --image-quality 95 \
    --max-image-width 3840 \
    -output ./high_quality/
```

### 场景 7: 快速处理（低质量）

```bash
pdf2md -input large_collection.pdf \
    --image-quality 70 \
    --max-image-width 1280 \
    --ocr-mode never \
    -output ./quick/
```

### 场景 8: 多语言文档

```bash
# PaddleOCR 自动检测语言
pdf2md -input multilingual.pdf \
    --ocr-mode auto \
    -v
```

---

## 性能优化

### 减少内存使用

```python
from pdf2md.core import Pipeline
from pdf2md.utils import FileManager

# 使用较低的图像质量
pipeline = Pipeline(
    file_manager=FileManager(),
    enable_ocr=False,  # 禁用 OCR 节省内存
    image_config={
        "max_width": 1280,
        "quality": 70
    }
)

# 处理单个文件而非批量
result = pipeline.process_file("/path/to/document.pdf")
```

### 提高处理速度

```bash
# 禁用 OCR
pdf2md -input document.pdf --ocr-mode never

# 使用较低的图像质量
pdf2md -input document.pdf --image-quality 70

# 不使用详细输出（减少 I/O）
pdf2md -input document.pdf  # 不使用 -v
```

### 并行处理

```bash
# 使用 GNU parallel 并行处理多个文件
find ./input/ -name "*.pdf" | parallel -j 4 pdf2md -input {} -output ./output/
```

---

## 故障排除

### 问题：OCR 识别不准确

**解决方案：**
1. 提高图像质量
   ```bash
   pdf2md -input document.pdf --image-quality 95 --max-image-width 3840
   ```
2. 使用 always 模式进行 OCR
   ```bash
   pdf2md -input document.pdf --ocr-mode always
   ```
3. 调整 OCR 参数
   ```bash
   pdf2md -input document.pdf --ocr-min-chars 50 --ocr-min-ratio 0.02
   ```

### 问题：内存不足

**解决方案：**
1. 降低图像质量
   ```bash
   pdf2md -input large_document.pdf --image-quality 70 --max-image-width 1280
   ```
2. 禁用 OCR
   ```bash
   pdf2md -input large_document.pdf --ocr-mode never
   ```
3. 使用断点续传分批处理
   ```bash
   pdf2md -input large_document.pdf --resume
   ```

### 问题：处理速度慢

**解决方案：**
1. 禁用 OCR（如果不需要）
   ```bash
   pdf2md -input document.pdf --ocr-mode never
   ```
2. 降低图像质量
   ```bash
   pdf2md -input document.pdf --image-quality 70
   ```
3. 减少输出文件大小

### 问题：表格格式不正确

**解决方案：**
1. 检查 PDF 表格结构是否复杂
2. 手动调整表格格式化参数
3. 使用图像方式保留复杂表格

### 问题：图像链接失效

**解决方案：**
1. 确保使用相对路径
2. 检查 assets 目录是否存在
3. 验证图像文件是否成功提取

### 问题：中文内容乱码

**解决方案：**
1. 确保使用支持中文的 OCR 引擎
   ```bash
   pdf2md -input chinese.pdf --ocr-mode auto
   ```
2. 检查输出文件编码（默认 UTF-8）
3. 验证字体支持

---

## 最佳实践

### 1. 文件组织

```
project/
├── input/              # 输入 PDF 文件
│   ├── reports/
│   ├── articles/
│   └── books/
├── output/             # 输出 Markdown 文件
│   ├── reports_md/
│   ├── articles_md/
│   └── books_md/
└── checkpoints/        # 检查点文件
```

### 2. 命名规范

```bash
# 使用描述性文件名
pdf2md -input 2024_annual_report.pdf -output ./output/annual_report/

# 批量处理时保持一致
pdf2md -input ./reports/*.pdf -output ./reports_md/
```

### 3. 日志和调试

```bash
# 开发时使用详细输出
pdf2md -input document.pdf -v

# 保存日志
pdf2md -input document.pdf -v > conversion.log 2>&1
```

### 4. 备份原始文件

```bash
# 在处理前备份
cp document.pdf document_backup.pdf
pdf2md -input document.pdf

# 或使用脚本自动备份
for file in *.pdf; do
    cp "$file" "backup_$(date +%Y%m%d)_$file"
    pdf2md -input "$file"
done
```

### 5. 验证输出

```python
# 处理后验证输出
import os

result = pipeline.process_file("/input/document.pdf")

if result.success:
    output_dir = result.output_dir
    md_file = os.path.join(output_dir, "document.md")

    if os.path.exists(md_file):
        print("✓ Markdown 文件已生成")
        print(f"  文件大小: {os.path.getsize(md_file)} bytes")
    else:
        print("✗ Markdown 文件未生成")
```

---

## 脚本示例

### 批量转换脚本

```python
#!/usr/bin/env python3
"""批量转换 PDF 文件为 Markdown"""

import os
import sys
from pathlib import Path
from pdf2md.core import Pipeline
from pdf2md.utils import FileManager

def convert_directory(input_dir: str, output_dir: str):
    """转换目录中的所有 PDF 文件"""
    pipeline = Pipeline(
        file_manager=FileManager(output_dir=output_dir),
        enable_ocr=True
    )

    results = pipeline.process_directory(input_dir)

    success_count = 0
    total_pages = 0

    for result in results:
        if result.success:
            success_count += 1
            total_pages += len(result.processed_pages)
            print(f"✓ {Path(result.file_path).name}: {len(result.processed_pages)} 页")
        else:
            print(f"✗ {Path(result.file_path).name}: {result.error_message}")

    print(f"\n总计: {success_count}/{len(results)} 文件成功，共 {total_pages} 页")
    pipeline.cleanup()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python batch_convert.py <input_dir> [output_dir]")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"

    convert_directory(input_dir, output_dir)
```

### 监控转换进度

```python
#!/usr/bin/env python3
"""监控 PDF 转换进度"""

import time
from pdf2md.core import Pipeline
from pdf2md.utils import FileManager
from pdf2md.utils import ProgressTracker

class ProgressMonitor:
    def __init__(self):
        self.tracker = ProgressTracker()
        self.pipeline = Pipeline(
            file_manager=FileManager(),
            enable_ocr=True
        )

    def process_with_progress(self, file_path: str):
        """带进度监控的处理"""
        self.tracker.start(file_path)

        try:
            result = self.pipeline.process_file(file_path, resume=False)

            if result.success:
                self.tracker.update(1.0, "完成")
                self.tracker.complete()
                print(f"✓ 处理完成: {result.processed_pages}/{result.total_pages} 页")
                return True
            else:
                print(f"✗ 处理失败: {result.error_message}")
                return False
        except KeyboardInterrupt:
            print("\n用户中断，保存检查点...")
            self.tracker.save_checkpoint(
                file_path,
                total_pages=0,
                processed_pages=[],
                failed_pages=[]
            )
            return False
        finally:
            self.pipeline.cleanup()

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python monitor.py <file_path>")
        sys.exit(1)

    monitor = ProgressMonitor()
    monitor.process_with_progress(sys.argv[1])
```

---

## 相关资源

- [API 文档](./API.md) - 完整的 API 参考
- [故障排除指南](./TROUBLESHOOTING.md) - 常见问题解决
- [贡献指南](../CONTRIBUTING.md) - 如何贡献代码
- [GitHub 仓库](https://github.com/yourusername/pdf2md) - 源代码和问题追踪