# 贡献指南

感谢您对 pdf2md 项目的关注！我们欢迎任何形式的贡献，包括但不限于：

- 🐛 报告 bug
- 💡 提出新功能建议
- 📝 改进文档
- 🔧 提交代码修复
- ✨ 开发新功能

---

## 如何贡献

### 报告 Bug

在报告 bug 之前，请先检查：

1. [Issues](https://github.com/yourusername/pdf2md/issues) 中是否已有类似问题
2. [故障排除指南](docs/TROUBLESHOOTING.md) 中是否有解决方案

如果确认是新问题，请创建一个新的 Issue，包含：

- **标题**: 简洁描述问题
- **描述**: 详细说明问题复现步骤
- **环境信息**:
  - 操作系统（Windows/Linux/macOS）
  - Python 版本
  - 依赖版本（`pip list` 输出）
- **复现步骤**:
  1. 使用命令: `...`
  2. 输入文件: `...`
  3. 预期行为: `...`
  4. 实际行为: `...`
- **错误日志**: 完整的错误信息或日志

### 提出新功能

在提出新功能之前，请先考虑：

1. 这个功能是否符合项目目标？
2. 是否有现有的解决方案？
3. 是否有其他人也会需要这个功能？

创建 Feature Request 时请包含：

- **标题**: 简洁描述功能
- **问题描述**: 当前情况及不足
- **建议方案**: 详细的解决方案描述
- **替代方案**: 其他可能的实现方式
- **附加信息**: 相关示例、截图等

### 提交代码

#### 设置开发环境

1. Fork 项目仓库
2. Clone 你的 fork:
   ```bash
   git clone https://github.com/yourusername/pdf2md.git
   cd pdf2md
   ```

3. 创建虚拟环境:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # 或
   venv\Scripts\activate     # Windows
   ```

4. 安装开发依赖:
   ```bash
   pip install -e ".[dev]"
   ```

5. 安装预提交钩子（可选）:
   ```bash
   pip install pre-commit
   pre-commit install
   ```

#### 开发流程

1. 创建功能分支:
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/your-bug-fix
   ```

2. 进行开发和测试:
   ```bash
   # 运行测试
   python -m pytest tests/

   # 运行特定测试
   python -m pytest tests/unit/test_utils.py -v

   # 运行测试并查看覆盖率
   python -m pytest tests/ --cov=pdf2md --cov-report=html
   ```

3. 代码格式化:
   ```bash
   # 使用 black 格式化代码
   black pdf2md/ tests/

   # 使用 isort 整理导入
   isort pdf2md/ tests/

   # 类型检查
   mypy pdf2md/
   ```

4. 提交代码:
   ```bash
   git add .
   git commit -m "描述你的更改"
   ```

5. 推送到你的 fork:
   ```bash
   git push origin feature/your-feature-name
   ```

6. 创建 Pull Request

#### Pull Request 指南

创建 PR 时，请确保：

- [ ] 标题简洁明确
- [ ] 描述中包含：
  - 改变的动机
  - 相关的 Issue 编号（如 `Fixes #123`）
  - 实现细节
  - 测试情况
- [ ] 所有测试通过
- [ ] 代码通过格式化和类型检查
- [ ] 添加了必要的测试
- [ ] 更新了相关文档

#### 代码规范

##### Python 代码

- 遵循 [PEP 8](https://peps8.org/) 风格指南
- 使用类型注解（Type Hints）
- 编写清晰的文档字符串（docstrings）
- 保持函数简洁（通常不超过 50 行）
- 使用有意义的变量和函数名

##### 文档字符串格式

```python
def process_file(self, file_path: str, resume: bool = False) -> ProcessResult:
    """Process a PDF file and convert it to Markdown.

    Args:
        file_path: Path to the PDF file to process.
        resume: Whether to resume from a checkpoint.

    Returns:
        ProcessResult containing the processing status and output information.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not a valid PDF.

    Example:
        >>> pipeline = Pipeline()
        >>> result = pipeline.process_file("/path/to/file.pdf")
        >>> if result.success:
        ...     print(f"Output: {result.output_dir}")
    """
    pass
```

##### 命名约定

- **类名**: `PascalCase` (如 `TextExtractor`)
- **函数/方法名**: `snake_case` (如 `process_file`)
- **常量**: `UPPER_CASE` (如 `MAX_IMAGE_WIDTH`)
- **私有方法**: `_leading_underscore` (如 `_internal_method`)

##### 错误处理

```python
# 好的做法
def process_file(self, file_path: str) -> ProcessResult:
    """Process a PDF file."""
    try:
        # 处理逻辑
        result = self._do_processing(file_path)
        return ProcessResult(success=True, ...)
    except FileNotFoundError as e:
        logger.error(f"File not found: {file_path}")
        return ProcessResult(success=False, error_message=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return ProcessResult(success=False, error_message=str(e))

# 避免的做法
def process_file(self, file_path: str) -> ProcessResult:
    # 不要在函数中直接退出程序
    sys.exit(1)
```

---

## 测试指南

### 运行测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行单元测试
python -m pytest tests/unit/

# 运行集成测试
python -m pytest tests/integration/

# 运行特定测试文件
python -m pytest tests/unit/test_utils.py

# 运行特定测试类
python -m pytest tests/unit/test_utils.py::TestLogger

# 运行特定测试方法
python -m pytest tests/unit/test_utils.py::TestLogger::test_init

# 查看详细输出
python -m pytest tests/ -v

# 查看打印输出
python -m pytest tests/ -v -s

# 并行运行测试（需要 pytest-xdist）
python -m pytest tests/ -n auto
```

### 测试覆盖率

```bash
# 生成覆盖率报告
python -m pytest tests/ --cov=pdf2md --cov-report=html

# 查看终端覆盖率
python -m pytest tests/ --cov=pdf2md --cov-report=term-missing
```

### 编写测试

```python
import pytest
from pdf2md.utils import FileManager

class TestFileManager:
    """Test cases for FileManager class."""

    def test_init_default(self):
        """Test FileManager initialization with default parameters."""
        fm = FileManager()
        assert fm.output_dir is None

    def test_init_with_output_dir(self):
        """Test FileManager initialization with output_dir."""
        fm = FileManager(output_dir="/tmp/output")
        assert fm.output_dir == Path("/tmp/output")

    def test_scan_directory_with_pdfs(self, tmp_path):
        """Test scanning directory with PDF files."""
        # 创建临时测试文件
        (tmp_path / "test1.pdf").touch()
        (tmp_path / "test2.pdf").touch()

        fm = FileManager()
        result = fm.scan_directory(str(tmp_path))

        assert len(result) == 2
        assert all(f.endswith(".pdf") for f in result)

    # 使用 fixtures
    @pytest.fixture
    def sample_pdf(self, tmp_path):
        """Create a sample PDF file for testing."""
        pdf_file = tmp_path / "sample.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")
        return pdf_file

    def test_process_sample_pdf(self, sample_pdf):
        """Test processing a sample PDF."""
        fm = FileManager()
        is_valid = fm.validate_pdf(str(sample_pdf))
        assert is_valid
```

### 测试最佳实践

1. **独立性**: 每个测试应该独立运行，不依赖其他测试
2. **清晰性**: 测试名称应该清楚地描述测试内容
3. **可读性**: 测试代码应该易于理解
4. **及时性**: 遇到 bug 时先写测试再修复
5. **覆盖边界**: 测试正常情况和边界情况

---

## 文档贡献

### 文档位置

- `docs/API.md` - API 参考文档
- `docs/EXAMPLES.md` - 使用示例
- `docs/TROUBLESHOOTING.md` - 故障排除指南
- `docs/PROGRESS.md` - 项目进度
- `README.md` - 项目说明（英文）
- `README.zh.md` - 项目说明（中文）

### 文档格式

- 使用 Markdown 格式
- 包含代码示例和命令
- 提供清晰的章节结构
- 添加适当的表情符号增强可读性

### 文档检查清单

- [ ] 内容准确无误
- [ ] 代码示例可以运行
- [ ] 链接有效
- [ ] 格式一致
- [ ] 拼写和语法正确

---

## 项目结构

```
pdf2md/
├── pdf2md/                 # 主包
│   ├── __init__.py
│   ├── core/              # 核心处理
│   ├── ocr/               # OCR 引擎
│   ├── extractor/         # 内容提取
│   ├── deduplicator/      # 去重处理
│   ├── summary/           # 摘要提取
│   ├── markdown/          # Markdown 生成
│   ├── utils/             # 工具函数
│   └── cli/               # 命令行接口
├── tests/                 # 测试
│   ├── unit/              # 单元测试
│   └── integration/       # 集成测试
├── docs/                  # 文档
│   ├── API.md
│   ├── EXAMPLES.md
│   ├── PROGRESS.md
│   └── TROUBLESHOOTING.md
├── fixtures/              # 测试数据
├── pyproject.toml         # 项目配置
├── requirements.txt       # 依赖列表
├── .gitignore            # Git 忽略规则
├── CLAUDE.md             # 开发指南
├── README.md             # 项目说明（英文）
├── README.zh.md          # 项目说明（中文）
└── CONTRIBUTING.md       # 贡献指南（本文件）
```

---

## 发布流程

### 版本号管理

项目使用 [语义化版本](https://semver.org/lang/zh-CN/)：

- `MAJOR.MINOR.PATCH`
  - MAJOR: 不兼容的 API 变更
  - MINOR: 向后兼容的功能性新增
  - PATCH: 向后兼容的问题修正

### 发布步骤

1. 更新版本号:
   - `pyproject.toml` 中的 version
   - `pdf2md/__init__.py` 中的 `__version__`

2. 更新 CHANGELOG.md

3. 创建发布标签:
   ```bash
   git tag -a v0.1.0 -m "Release version 0.1.0"
   git push origin v0.1.0
   ```

4. 创建 GitHub Release

---

## 许可证

通过贡献代码，您同意您的贡献将在项目的许可证下发布。

---

## 社区准则

### 我们的承诺

为了营造开放和友好的环境，我们承诺：

- 使用友好和包容的语言
- 尊重不同的观点和经验
- 优雅地接受建设性批评
- 关注对社区最有利的事情
- 对其他社区成员表示同理心

### 不可接受的行为

- 使用性化的语言或图像
- 人身攻击或侮辱性言论
- 公开或私下的骚扰
- 未经许可发布他人的私人信息
- 其他不道德或不专业的行为

---

## 获取帮助

如果您有任何问题或需要帮助：

1. 查看 [文档](docs/) 和 [示例](docs/EXAMPLES.md)
2. 搜索 [Issues](https://github.com/yourusername/pdf2md/issues)
3. 创建新的 Issue 寻求帮助
4. 加入我们的讨论区（如果有）

---

## 致谢

感谢所有贡献者的支持！我们感谢以下方式：

- 在代码中添加作者注释
- 在 CHANGELOG 中提及贡献
- 在 GitHub 上显示贡献者列表

---

再次感谢您的贡献！❤️