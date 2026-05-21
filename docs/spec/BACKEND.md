# BACKEND.md - Backend Specification Document

**Project**: pdf2md
**Date**: 2026-05-21
**Version**: 1.0

---

## 1. 概述

pdf2md 本身是一个本地命令行工具，不包含服务端后端。它**消费**一个外部的 PDF-to-Markdown 转换 API。本文档描述该 API 的接口规范和本地处理逻辑。

---

## 2. 外部 API 接口

### 2.1 基本信息

| 项目 | 值 |
|------|------|
| 协议 | HTTP |
| 方法 | POST |
| 路径 | `/convert2markdown` |
| 默认地址 | `http://123.192.49.73:8000` |
| Content-Type | `application/json` |
| 认证 | 请求头 `client_id` |

### 2.2 请求格式

```http
POST /convert2markdown HTTP/1.1
Host: 123.192.49.73:8000
client_id: bf-mkd
Content-Type: application/json

{
  "files": [
    "<base64-encoded-file-content-1>",
    "<base64-encoded-file-content-2>"
  ]
}
```

**字段说明**:

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `files` | `array[string]` | 是 | Base64 编码的文件内容数组。每次请求发送一个文件（单元素数组）。 |

**Base64 编码**:
- 读取文件二进制内容
- 使用标准 Base64 编码（`base64.b64encode()`）
- 解码为 ASCII 字符串

### 2.3 响应格式

```json
{
  "task_id": "a65f4a9a-aa11-4a99-b004-5d9d2b3f17a1",
  "status": "completed",
  "backend": "hybrid-auto-engine",
  "file_names": ["file_0"],
  "version": "3.1.8",
  "results": {
    "0": {
      "md_content": "# Document Title\n\nConverted markdown content..."
    },
    "1": {
      "md_content": "# Second Page\n\n..."
    }
  }
}
```

**字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | 任务唯一标识（UUID 格式） |
| `status` | string | 任务状态（`completed`, `failed` 等） |
| `backend` | string | 使用的转换引擎名称 |
| `file_names` | array[string] | API 返回的文件名称列表 |
| `version` | string | API 版本号 |
| `results` | object | 转换结果，键为索引字符串（"0", "1"...），值为包含 `md_content` 的对象 |
| `results.{index}.md_content` | string | 转换后的 Markdown 文本内容 |

### 2.4 可能的 HTTP 状态码

| 状态码 | 含义 | 处理策略 |
|--------|------|----------|
| 200 | 请求成功 | 解析 JSON，提取 results |
| 4xx | 客户端错误（参数错误等） | 重试（配置的重试次数内） |
| 5xx | 服务端错误 | 重试（配置的重试次数内） |

### 2.5 错误场景

| 错误类型 | 表现 | 处理 |
|----------|------|------|
| 连接失败 | `ConnectionError` | 重试 |
| 请求超时 | `Timeout` | 重试 |
| SSL 错误 | `SSLError` | 重试 |
| 其他请求异常 | `RequestException` | 重试 |
| 返回非 JSON | `JSONDecodeError` | 不重试，标记失败 |

---

## 3. 本地处理逻辑

### 3.1 文件读取与编码

```
磁盘文件 → 读取二进制内容 (rb) → base64.b64encode() → decode("ascii") → Base64 字符串
```

- 读取整个文件到内存
- Base64 编码后大小约为原始的 133%
- 无文件大小限制（当前版本）

### 3.2 API 客户端实现

```python
def call_api(config, logger, base64_content, file_name):
```

**流程**:
1. 构建请求体 `{"files": [base64_content]}`
2. 设置请求头 `client_id` 和 `Content-Type`
3. 进入重试循环（1 到 max_retries）
4. 发送 POST 请求，记录耗时
5. 根据响应状态决定：成功返回、重试、或标记失败
6. 重试间隔使用 `time.sleep(config["retry_delay"])`

**超时配置**: 使用 `timeout=config["timeout"]`（默认 120 秒），包括连接超时和读取超时。

### 3.3 响应解析

```python
def extract_md_content(response_data):
```

- 从 `response_data["results"]` 中提取所有 `md_content`
- 返回 `[(index, content), ...]` 元组列表
- 对非 dict 类型的 result 值进行类型保护（跳过）
- 对缺失 `md_content` 键的项使用空字符串默认值

### 3.4 文件写入

```python
def get_unique_path(output_dir, base_name):
```

**流程**:
1. 尝试 `{output_dir}/{base_name}.md`
2. 如果文件已存在，生成 5 位随机小写字母后缀
3. 重复直到找到不存在的文件名
4. 使用 UTF-8 编码写入文件

---

## 4. 日志系统

### 4.1 日志架构

```
                    ┌─────────────────┐
                    │   pdf2md logger  │
                    │   Level: DEBUG   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼                             ▼
     ┌──────────────────┐        ┌──────────────────┐
     │  FileHandler     │        │  StreamHandler   │
     │  Level: DEBUG    │        │  Level: INFO     │
     │  Format: [time]  │        │  Format: [time]  │
     │  → logs/*.log    │        │  → stdout        │
     └──────────────────┘        └──────────────────┘
```

### 4.2 日志格式

```
[%(asctime)s] %(levelname)-5s  %(message)s
```

日期格式: `%Y-%m-%d %H:%M:%S`

### 4.3 日志轮转策略

- **按天轮转**: 文件名包含日期 `pdf2md-YYYYMMDD.log`
- 新一天自动创建新文件
- 不清理历史日志（手动管理）

### 4.4 关键日志事件

| 事件 | 级别 | 示例 |
|------|------|------|
| 程序启动 | INFO | `pdf2md started. Config loaded from conf/setting.json` |
| 找到文件 | INFO | `Found 3 file(s) to process.` |
| 编码成功 | INFO | `Encoded report.pdf (1048576 bytes, base64 size: 1398102).` |
| API 调用中 | INFO | `Calling API for report.pdf (attempt 1/3)` |
| API 成功 | INFO | `API response in 5.2s, status=completed` |
| 写入输出 | INFO | `Wrote output report.md (5230 bytes) for report.pdf (index 0)` |
| 汇总信息 | INFO | `Processed 3 files: 2 success, 1 failed` |
| 扩展名不支持 | WARNING | `File has unsupported extension '.json': data.json` |
| 无 Markdown 内容 | WARNING | `API returned no markdown content for report.pdf` |
| 文件读取失败 | ERROR | `Failed to read file report.pdf: Permission denied` |
| API 请求失败 | ERROR | `Request failed after 32.0s: ConnectionError (attempt 1)` |
| 写入失败 | ERROR | `Failed to write output for report.pdf (index 0): Disk full` |

---

## 5. 配置管理

### 5.1 加载流程

1. 查找 `conf/setting.json`（相对于脚本目录）
2. 不存在 → 创建目录和默认文件 → 返回默认值
3. 存在 → 解析 JSON
4. 验证所有必需键存在
5. 验证所有值类型正确
6. 返回配置字典

### 5.2 路径解析

`log_dir` 和 `output_dir` 如果是相对路径，则在脚本启动时相对于脚本所在目录解析为绝对路径。

---

## 6. 错误处理策略

### 6.1 分级处理

```
致命错误（EXIT 1）:
  - 路径不存在
  - 配置格式错误
  - 配置缺少必需字段
  - 配置值类型错误

文件级错误（跳过，继续下一个）:
  - 文件读取失败
  - API 调用全部重试失败
  - 输出文件写入失败
  - 不支持的文件格式
```

### 6.2 失败隔离

每个文件的处理在独立的 try/except 块中。单个文件失败不会中断其他文件的处理。
