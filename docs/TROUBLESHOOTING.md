# 故障排除指南

本文档提供 pdf2md 工具的常见问题和解决方案。

---

## 目录

- [安装问题](#安装问题)
- [运行时错误](#运行时错误)
- [OCR 问题](#ocr-问题)
- [性能问题](#性能问题)
- [输出问题](#输出问题)
- [兼容性问题](#兼容性问题)
- [获取帮助](#获取帮助)

---

## 安装问题

### 问题：ModuleNotFoundError: No module named 'pdfplumber'

**症状**：
```
ModuleNotFoundError: No module named 'pdfplumber'
```

**原因**：未安装必要的依赖包

**解决方案**：
```bash
# 安装所有依赖
pip install pdfplumber pdf2image paddleocr Pillow click

# 或从 requirements.txt 安装
pip install -r requirements.txt

# 或使用开发模式安装
pip install -e ".[dev]"
```

---

### 问题：poppler not installed

**症状**：
```
FileNotFoundError: [Errno 2] No such file or directory: 'pdftoppm'
```

**原因**：pdf2image 需要 Poppler

**解决方案**：

**macOS**:
```bash
brew install poppler
```

**Ubuntu/Debian**:
```bash
sudo apt-get install poppler-utils
```

**Fedora/CentOS**:
```bash
sudo yum install poppler-utils
```

**Windows**:
1. 下载 Poppler for Windows: http://blog.alivate.com.au/poppler-windows/
2. 解压并将 bin 目录添加到系统 PATH

---

### 问题：PaddleOCR 依赖冲突

**症状**：
```
ERROR: pip's dependency resolver does not currently take into account...
```

**原因**：PaddleOCR 的某些依赖可能与现有包冲突

**解决方案**：
```bash
# 创建新的虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 然后安装依赖
pip install pdfplumber pdf2image paddleocr Pillow click
```

---

## 运行时错误

### 问题：File not found or not accessible

**症状**：
```
FileNotFoundError: [Errno 2] No such file or directory: '/path/to/file.pdf'
```

**原因**：文件路径错误或文件不存在

**解决方案**：
```bash
# 检查文件是否存在
ls -la /path/to/file.pdf

# 使用相对路径
pdf2md -input ./documents/file.pdf

# 使用绝对路径
pdf2md -input /home/user/documents/file.pdf

# 检查文件权限
chmod 644 /path/to/file.pdf
```

---

### 问题：Permission denied when creating output

**症状**：
```
PermissionError: [Errno 13] Permission denied: '/output/directory'
```

**原因**：没有写入输出目录的权限

**解决方案**：
```bash
# 使用有权限的输出目录
pdf2md -input file.pdf -output ~/output/

# 修改目录权限
chmod 755 /output/directory

# 使用 sudo（不推荐）
sudo pdf2md -input file.pdf -output /system/output/
```

---

### 问题：Invalid PDF file

**症状**：
```
ValueError: Invalid PDF file or file is corrupted
```

**原因**：PDF 文件损坏或格式不正确

**解决方案**：
```bash
# 验证 PDF 文件
file input.pdf

# 尝试修复 PDF（使用 qpdf）
qpdf --linearize input.pdf repaired.pdf
pdf2md -input repaired.pdf

# 使用在线 PDF 验证工具
```

---

### 问题：File too large

**症状**：
```
ValueError: File too large: 250.00MB (max 200MB): large_file.pdf
```

**原因**：文件大小超过了 200MB 限制

**解决方案**：
```bash
# 压缩 PDF（使用 Ghostscript）
gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook \
   -dNOPAUSE -dQUIET -dBATCH -sOutputFile=compressed.pdf input.pdf

# 然后处理压缩后的文件
pdf2md -input compressed.pdf
```

---

## OCR 问题

### 问题：OCR results are poor

**症状**：OCR 识别的文本不准确或为空

**原因**：
1. 图像质量差
2. OCR 配置不当
3. 语言不匹配

**解决方案**：

**提高图像质量**：
```bash
pdf2md -input document.pdf \
    --image-quality 95 \
    --max-image-width 3840 \
    -v
```

**调整 OCR 参数**：
```bash
pdf2md -input document.pdf \
    --ocr-mode always \
    --ocr-min-chars 50 \
    --ocr-min-ratio 0.02 \
    -v
```

**验证语言支持**：
```python
from pdf2md.ocr import PaddleOCR

ocr = PaddleOCR(lang="ch")  # 中文
# 或
ocr = PaddleOCR(lang="en")  # 英文
```

---

### 问题：OCR is very slow

**症状**：OCR 处理耗时很长

**原因**：
1. 使用 CPU 处理
2. 图像分辨率过高
3. 处理大量页面

**解决方案**：

**降低图像质量**：
```bash
pdf2md -input document.pdf \
    --image-quality 70 \
    --max-image-width 1280
```

**禁用 OCR（如果不需要）**：
```bash
pdf2md -input document.pdf --ocr-mode never
```

**使用 GPU 加速**（如果可用）：
```python
from pdf2md.ocr import PaddleOCR

ocr = PaddleOCR(use_gpu=True)
```

---

### 问题：OCR not triggered when expected

**症状**：应该进行 OCR 的页面没有被处理

**原因**：OCR 触发阈值设置过高

**解决方案**：
```bash
# 降低触发阈值
pdf2md -input document.pdf \
    --ocr-min-chars 50 \
    --ocr-min-ratio 0.02 \
    --ocr-image-ratio 0.5
```

```python
# 或在代码中设置
pipeline = Pipeline(
    ocr_config={
        "min_chars": 50,
        "min_ratio": 0.02,
        "max_image_ratio": 0.5
    }
)
```

---

## 性能问题

### 问题：Out of memory

**症状**：
```
MemoryError: Unable to allocate array
```

**原因**：处理大文件时内存不足

**解决方案**：

**降低图像质量**：
```bash
pdf2md -input large_file.pdf \
    --image-quality 70 \
    --max-image-width 1280
```

**禁用 OCR**：
```bash
pdf2md -input large_file.pdf --ocr-mode never
```

**使用断点续传**：
```bash
# 首次处理
pdf2md -input large_file.pdf

# 如果中断，恢复处理
pdf2md -input large_file.pdf --resume
```

**分批处理**：
```bash
# 只处理部分页面（需要修改代码）
```

---

### 问题：Processing is very slow

**症状**：处理单个 PDF 文件耗时很长

**原因**：
1. 启用了 OCR
2. 图像质量设置过高
3. PDF 页数很多

**解决方案**：

**禁用 OCR（如果不需要）**：
```bash
pdf2md -input document.pdf --ocr-mode never
```

**降低图像质量**：
```bash
pdf2md -input document.pdf \
    --image-quality 70 \
    --max-image-width 1280
```

**并行处理**：
```bash
# 使用 GNU parallel
find ./input/ -name "*.pdf" | parallel -j 4 pdf2md -input {} -output ./output/
```

---

## 输出问题

### 问题：Markdown formatting is incorrect

**症状**：输出的 Markdown 格式混乱或不符合预期

**原因**：
1. PDF 布局复杂
2. 表格提取不准确
3. 特殊字符未正确转义

**解决方案**：

**检查原始 PDF 布局**
- 简化 PDF 布局
- 使用 PDF 编辑工具优化格式

**手动调整表格**
```python
from pdf2md.markdown import TableFormatter

formatter = TableFormatter(max_column_width=200)
# 自定义表格格式化
```

**验证输出内容**
```bash
# 使用 Markdown 预览器查看输出
# GitHub, VS Code, 或其他 Markdown 编辑器
```

---

### 问题：Images are missing or broken

**症状**：输出的 Markdown 中图像链接失效

**原因**：
1. 图像未成功提取
2. 图像路径错误
3. assets 目录缺失

**解决方案**：

**检查输出目录结构**：
```bash
ls -la output/
ls -la output/assets/
```

**验证图像文件**：
```bash
find output/ -name "*.png" -o -name "*.jpg"
```

**手动提取图像**（如果自动提取失败）：
```python
from pdf2md.extractor import ImageExtractor

extractor = ImageExtractor(output_dir="/output/assets")
images = extractor.extract(page)
```

---

### 问题：Chinese characters display as garbled text

**症状**：中文字符显示为乱码

**原因**：
1. 字符编码问题
2. OCR 语言设置错误
3. Markdown 渲染器不支持中文

**解决方案**：

**确保使用正确的 OCR 语言**：
```bash
pdf2md -input chinese.pdf --ocr-mode auto
```

```python
from pdf2md.ocr import PaddleOCR

ocr = PaddleOCR(lang="ch")  # 中文
```

**验证文件编码**：
```bash
file output.md
# 应显示: UTF-8 Unicode text
```

**使用支持中文的 Markdown 渲染器**：
- GitHub
- GitLab
- VS Code
- Typora

---

### 问题：Tables are not correctly formatted

**症状**：表格格式错误或内容丢失

**原因**：
1. PDF 表格结构复杂
2. 合并单元格处理不当
3. 表格检测失败

**解决方案**：

**检查原始表格结构**
- 确保表格格式简单清晰
- 避免复杂的嵌套表格

**调整表格格式化参数**：
```python
from pdf2md.markdown import TableFormatter

formatter = TableFormatter(
    max_column_width=200  # 增加列宽
)
```

**手动处理复杂表格**
- 将表格截图作为图像处理
- 手动编辑 Markdown 表格

---

## 兼容性问题

### 问题：Python version incompatibility

**症状**：
```
SyntaxError: invalid syntax
```

**原因**：Python 版本过低

**解决方案**：
```bash
# 检查 Python 版本
python --version

# 需要至少 Python 3.8
python3.8 --version

# 使用正确的 Python 版本
python3.8 pdf2md -input document.pdf
```

---

### 问题：Platform-specific issues

**症状**：代码在特定平台上失败

**解决方案**：

**Windows 路径问题**：
```python
# 使用 pathlib 处理跨平台路径
from pathlib import Path

path = Path("documents/file.pdf")  # 自动处理路径分隔符
```

**文件权限问题**（Linux/macOS）：
```bash
chmod +x pdf2md.py
```

---

## 调试技巧

### 启用详细日志

```bash
# 使用 verbose 模式
pdf2md -input document.pdf -v

# 或设置环境变量
export LOG_LEVEL=DEBUG
pdf2md -input document.pdf
```

### 检查中间文件

```bash
# 查看检查点文件
ls -la *.checkpoint.json

# 查看提取的图像
ls -la output/assets/

# 查看生成的 Markdown
cat output/document.md
```

### 使用 Python 调试器

```python
import pdb
from pdf2md.core import Pipeline

pipeline = Pipeline()

# 设置断点
pdb.set_trace()

result = pipeline.process_file("document.pdf")
```

### 验证组件

```python
# 单独测试 OCR
from pdf2md.ocr import PaddleOCR
from PIL import Image

ocr = PaddleOCR()
result = ocr.extract_text(image)
print(result.text)

# 单独测试文本提取
from pdf2md.extractor import TextExtractor
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    extractor = TextExtractor()
    text = extractor.extract(pdf.pages[0])
    print(text.raw_text)
```

---

## 获取帮助

如果以上解决方案无法解决您的问题：

### 1. 查看文档

- [API 文档](docs/API.md)
- [使用示例](docs/EXAMPLES.md)
- [贡献指南](CONTRIBUTING.md)

### 2. 搜索 Issues

访问 [GitHub Issues](https://github.com/yourusername/pdf2md/issues) 搜索类似问题

### 3. 创建新 Issue

如果未找到解决方案，请创建新的 Issue，包含：

- **环境信息**：
  - 操作系统
  - Python 版本
  - pdf2md 版本
- **复现步骤**
- **错误日志**（使用 `-v` 参数获取）
- **输入文件**（如果可能且不包含敏感信息）

### 4. 联系维护者

- 通过 GitHub Issues 联系
- 查看项目 README 中的联系方式

---

## 常见错误代码

| 错误代码 | 含义 | 解决方案 |
|---------|------|---------|
| `ModuleNotFoundError` | 缺少依赖 | 安装依赖包 |
| `FileNotFoundError` | 文件不存在 | 检查文件路径 |
| `PermissionError` | 权限不足 | 修改文件权限或使用其他目录 |
| `ValueError` | 无效参数 | 检查参数值 |
| `RuntimeError` | 运行时错误 | 查看详细错误信息 |
| `MemoryError` | 内存不足 | 降低图像质量或处理小文件 |
| `KeyError` | 键不存在 | 检查配置或数据结构 |

---

## 有用的工具

### PDF 工具

- **qpdf**: PDF 修复和优化
- **Ghostscript**: PDF 转换和压缩
- **Poppler**: PDF 渲染和处理
- **pdfinfo**: PDF 信息查看

### 图像工具

- **ImageMagick**: 图像处理和转换
- **Pillow**: Python 图像处理库

### Markdown 工具

- **VS Code**: 支持 Markdown 预览
- **Typora**: Markdown 编辑器
- **Pandoc**: 文档格式转换

---

## 性能基准

参考性能数据（仅供参考）：

| 文件大小 | 页数 | OCR | 预计时间 |
|---------|------|-----|---------|
| 1 MB | 5 | 否 | ~5 秒 |
| 1 MB | 5 | 是 | ~15 秒 |
| 10 MB | 50 | 否 | ~30 秒 |
| 10 MB | 50 | 是 | ~3 分钟 |
| 100 MB | 500 | 否 | ~5 分钟 |
| 100 MB | 500 | 是 | ~30 分钟 |

*注：实际时间取决于硬件配置和文件内容*

---

## 更新和升级

```bash
# 更新到最新版本
pip install --upgrade pdf2md

# 从 GitHub 安装最新开发版
pip install git+https://github.com/yourusername/pdf2md.git

# 检查当前版本
pip show pdf2md
```