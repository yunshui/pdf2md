# FRONTEND.md - Frontend Specification Document

**Project**: pdf2md
**Date**: 2026-05-21
**Version**: 1.0

---

## 1. 概述

pdf2md 是一个纯命令行工具，**没有图形界面（GUI）或 Web 前端**。所有用户交互通过终端命令行完成。

---

## 2. 命令行接口

### 2.1 基本用法

```bash
python pdf2md.py <path>
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `path` | 位置参数 | 是 | 文件路径或目录路径 |
| `-h`, `--help` | 选项 | 否 | 显示帮助信息并退出 |

### 2.2 帮助输出

```
usage: pdf2md.py [-h] path

Convert PDF, DOCX, DOC, and TXT files to Markdown via a remote conversion API.

positional arguments:
  path        Path to a PDF/DOCX/DOC/TXT file or directory containing such
              files.

options:
  -h, --help  show this help message and exit
```

### 2.3 使用场景

#### 场景 1: 转换单个文件

```bash
python pdf2md.py documents/report.pdf
```

#### 场景 2: 批量转换目录下所有文件

```bash
python pdf2md.py documents/
```

工具会自动扫描目录下所有支持格式的文件（`.pdf`, `.docx`, `.doc`, `.txt`），按文件名排序逐个处理。

#### 场景 3: 传入不支持的格式

```bash
python pdf2md.py data/example-output.json
```

输出：
```
[2026-05-21 10:00:00] WARNING  File has unsupported extension '.json': data/example-output.json
[2026-05-21 10:00:00] ERROR    No files to process. Exiting.
```

退出码: 1

---

## 3. 控制台输出

### 3.1 正常转换流程输出

```
[2026-06-01 10:00:00] INFO   pdf2md started. Config loaded from conf/setting.json
[2026-06-01 10:00:00] INFO   Processing path: documents/report.pdf
[2026-06-01 10:00:00] INFO   Found 1 file(s) to process.
[2026-06-01 10:00:00] INFO   Processing documents/report.pdf (1048576 bytes)
[2026-06-01 10:00:00] INFO   Output directory: output/report_md
[2026-06-01 10:00:00] INFO   Calling API for report.pdf pages 0-4 (attempt 1/3)
[2026-06-01 10:00:05] INFO   API response in 5.2s, status=completed
[2026-06-01 10:00:05] INFO   Wrote output report_0-4.md (5230 bytes) for report.pdf
[2026-06-01 10:00:05] INFO   Calling API for report.pdf pages 5-9 (attempt 1/3)
[2026-06-01 10:00:06] INFO   API response in 1.0s, status=completed
[2026-06-01 10:00:06] INFO   No more content from API for report.pdf at pages 5-9
[2026-06-01 10:00:06] INFO   Calling summarize API (attempt 1/3)
[2026-06-01 10:00:10] INFO   Summarize API returned 350 chars
[2026-06-01 10:00:10] INFO   Wrote summary file output/report_md/report.md
[2026-06-01 10:00:10] INFO   Processed 1 files: 1 success, 0 failed
```

### 3.2 失败重试输出

```
[2026-06-01 10:00:00] INFO   Processing documents/report.pdf (1048576 bytes)
[2026-06-01 10:00:00] INFO   Output directory: output/report_md
[2026-06-01 10:00:00] INFO   Calling API for report.pdf pages 0-4 (attempt 1/3)
[2026-06-01 10:00:32] ERROR  Request failed after 32.0s: ConnectionError (attempt 1)
[2026-06-01 10:00:34] INFO   Calling API for report.pdf pages 0-4 (attempt 2/3)
[2026-06-01 10:01:06] ERROR  Request failed after 32.0s: ConnectionError (attempt 2)
[2026-06-01 10:01:08] INFO   Calling API for report.pdf pages 0-4 (attempt 3/3)
[2026-06-01 10:01:40] ERROR  Request failed after 32.0s: ConnectionError (attempt 3)
[2026-06-01 10:01:40] ERROR  API call failed for report.pdf pages 0-4
[2026-06-01 10:01:40] INFO   Processed 1 files: 0 success, 1 failed
```

### 3.3 文件名冲突输出

```
[2026-05-21 10:00:00] INFO   Wrote output report_ab3de.md (5230 bytes) for report.pdf (index 0)
```

---

## 4. 退出码

| 退出码 | 含义 | 示例场景 |
|--------|------|----------|
| 0 | 全部成功 | 10 个文件全部转换成功 |
| 1 | 有失败 | 10 个文件中 1 个失败 |
| 2 | 参数错误 | 未提供 path 参数（argparse 默认行为） |

---

## 5. 配置文件交互

配置文件 `conf/setting.json` 在首次运行时自动创建，用户可以直接编辑。

### 示例配置

```json
{
  "api_url": "http://123.192.49.73:8000/file_parse",
  "client_id": "bf-mkd",
  "max_retries": 3,
  "retry_delay": 2,
  "timeout": 120,
  "output_dir": "output",
  "log_dir": "logs",
  "page_num": 10,
  "summarize_api_url": "http://123.192.49.9:8086/v1/chat/completions",
  "summarize_api_key": "123",
  "summarize_model": "qwen3.5",
  "summarize_prompt": "You are a document summarization assistant..."
}
```

### 配置错误反馈

**场景 1: JSON 格式错误**

```
Error: Failed to parse config file /path/to/conf/setting.json: Expecting ',' delimiter: line 3 column 5 (char 45)
```

**场景 2: 缺少必需字段**

```
Error: Config file /path/to/conf/setting.json is missing required keys: timeout, max_retries
```

**场景 3: 字段类型错误**

```
Error: Config file /path/to/conf/setting.json has invalid value types: max_retries (expected int, got str), timeout (expected int, got NoneType)
```
