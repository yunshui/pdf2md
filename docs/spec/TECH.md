# TECH.md - Technical Architecture Document

**Project**: pdf2md
**Date**: 2026-05-21
**Version**: 1.0

---

## 1. 技术选型

| 维度 | 选择 | 理由 |
|------|------|------|
| 语言 | Python 3.7+ | 脚本语言，适合快速开发命令行工具 |
| HTTP 客户端 | requests >= 2.28.0 | 成熟稳定，支持超时、重试、JSON 序列化 |
| 日志 | Python 标准库 logging | 内置，支持多 Handler、级别控制、格式化 |
| 配置 | JSON 文件 | 简单易读，无需额外解析库 |
| 架构 | 单文件脚本 | 功能明确，维护成本低，无需打包 |

---

## 2. 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                        pdf2md.py                         │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ argparse │→ │ load_    │→ │ setup_   │              │
│  │ CLI 解析 │  │ config   │  │ logging  │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│        │                                              │
│        ▼                                              │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ resolve_ │→ │ file_to_     │→ │ call_api     │    │
│  │ files    │  │ base64       │  │ (retry)      │    │
│  └──────────┘  └──────────────┘  └──────────────┘    │
│                                              │         │
│                                              ▼         │
│                                        ┌──────────┐   │
│                                        │ extract_ │   │
│                                        │ md_content│   │
│                                        └──────────┘   │
│                                              │        │
│                                              ▼        │
│                                        ┌──────────┐   │
│                                        │ get_     │   │
│                                        │ unique_  │   │
│                                        │ path     │   │
│                                        └──────────┘   │
│                                              │        │
│                                              ▼        │
│                                        ┌──────────┐   │
│                                        │ 写入 .md │   │
│                                        └──────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 模块说明

### 3.1 常量与配置

```python
DEFAULT_CONFIG = {
    "api_url": str,        # API 端点
    "client_id": str,      # API 客户端标识
    "max_retries": int,    # 最大重试次数
    "retry_delay": int,    # 重试间隔（秒）
    "timeout": int,        # 请求超时（秒）
    "output_dir": str,     # 输出目录
    "log_dir": str,        # 日志目录
}

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}
```

### 3.2 函数清单

| 函数名 | 参数 | 返回值 | 职责 | 依赖 |
|--------|------|--------|------|------|
| `load_config(script_dir)` | `script_dir: str` | `dict` | 加载/创建/验证配置 | os, json, sys, DEFAULT_CONFIG |
| `setup_logging(log_dir)` | `log_dir: str` | `logging.Logger` | 初始化日志系统 | logging, datetime, os |
| `resolve_files(path, logger)` | `path: str, logger` | `list[str]` | 解析输入文件列表 | os, glob, SUPPORTED_EXTENSIONS |
| `file_to_base64(file_path)` | `file_path: str` | `str` | 读取文件并 Base64 编码 | base64, open() |
| `call_api(config, logger, base64_content, file_name)` | 见参数 | `dict` / `None` | 调用转换 API（带重试） | requests, time, json |
| `extract_md_content(response_data)` | `response_data: dict` | `list[tuple]` | 从 API 响应提取 Markdown | - |
| `get_unique_path(output_dir, base_name)` | `output_dir: str, base_name: str` | `str` | 生成不冲突的输出路径 | os, random, string |
| `main()` | - | - | 程序入口，编排全流程 | 以上所有函数 |

---

## 4. 数据流

```
磁盘文件 (.pdf/.docx)
    │
    │  file_to_base64()
    ▼
Base64 字符串
    │
    │  call_api() → POST {"files": [base64]}
    ▼
API 响应 JSON
    {
      "status": "completed",
      "results": { "0": { "md_content": "..." } }
    }
    │
    │  extract_md_content()
    ▼
Markdown 内容列表
    [(index, md_content), ...]
    │
    │  get_unique_path() + 写入文件
    ▼
磁盘文件 (.md)
    output/{filename}.md
```

---

## 5. 关键设计决策

### 5.1 单文件架构

**决策**: 所有逻辑放在 `pdf2md.py` 一个文件中。

**理由**:
- 功能范围明确且有限（CLI 工具 + API 调用）
- 无复杂业务逻辑需要分层
- 降低维护成本，无需管理包/模块依赖
- 部署简单，无需打包

**约束**: 核心逻辑控制在 500 行以内。

### 5.2 同步顺序处理

**决策**: 文件逐个顺序处理，无并发。

**理由**:
- API 调用是主要耗时点（网络 IO），本地处理几乎瞬时
- 并发会增加 API 服务器压力
- 保持代码简单可靠

### 5.3 路径解析策略

**决策**: 相对路径（log_dir, output_dir）相对于脚本所在目录解析，而非当前工作目录。

**理由**:
- 用户从任意目录运行脚本时，日志和输出都在预期位置
- 避免输出文件散落在各处

### 5.4 重试策略

**决策**: 固定延迟重试（非指数退避），可配置次数和间隔。

**理由**:
- 重试次数少（默认 3），指数退避收益不大
- 固定延迟更易于理解和配置
- 未来可增加指数退避作为可选策略

### 5.5 日志级别设计

**决策**: 文件 Handler 记录 DEBUG，控制台 Handler 记录 INFO。

**理由**:
- 文件日志保留完整细节用于排查
- 控制台日志只显示关键信息，避免淹没用户

---

## 6. 外部依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | 3.7+ | 运行时 |
| requests | >= 2.28.0 | HTTP 客户端 |

无其他外部依赖。

---

## 7. 安全考量

| 风险 | 缓解措施 |
|------|----------|
| API 地址暴露 | 配置文件中，不硬编码在源码（默认值除外） |
| 大文件内存溢出 | 当前无限制，建议在配置中添加 max_file_size |
| 输出目录权限 | 使用 os.makedirs(exist_ok=True)，失败时捕获 OSError |

---

## 8. 扩展性考虑

未来可能的扩展方向：

1. **并发处理**: 引入 concurrent.futures 并行处理多文件
2. **文件大小限制**: 配置 max_file_size 字段，拒绝超大文件
3. **指数退避**: 将固定重试改为指数退避 + 随机抖动
4. **多 API 后端**: 支持配置多个 API 端点，自动降级
5. **缓存**: 相同文件重复转换时缓存结果
