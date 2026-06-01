# pdf2md

通过远程分页 API 和 LLM 摘要将 PDF、DOCX、DOC 和 TXT 文件转换为 Markdown 格式。

## 快速开始

```bash
pip install -r requirements.txt
python pdf2md.py <文件或目录路径>
```

## 功能特性

- **多格式支持**: PDF、DOCX、DOC、TXT
- **批量处理**: 传入目录可一次性转换所有支持的文件
- **分页处理**: 按页码范围分页调用 API，每个 chunk 独立保存
- **LLM 摘要**: 自动生成文档摘要，含 chunk 文件链接（可配置 OpenAI 兼容 API）
- **目录级输出**: 每个文件对应独立 `{name}_md/` 目录，含 chunk 和 summary 文件
- **重试机制**: 可配置的网络请求重试次数和超时时间
- **详细日志**: 按天记录日志，包含耗时、重试次数、错误详情等信息

## 配置说明

配置文件位于 `conf/setting.json`（首次运行时自动生成）：

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `api_url` | `http://123.192.49.73:8000/file_parse` | 分页解析 API 地址 |
| `client_id` | `bf-mkd` | API 客户端标识 |
| `max_retries` | `3` | 最大重试次数 |
| `retry_delay` | `2` | 重试间隔（秒） |
| `timeout` | `120` | 请求超时时间（秒） |
| `output_dir` | `output` | Markdown 输出目录 |
| `log_dir` | `logs` | 日志存储目录 |
| `page_num` | `5` | 每批处理页数 |
| `summarize_api_url` | `http://127.0.0.1:8000/v1/chat/completions` | LLM 摘要 API 地址 |
| `summarize_api_key` | `""` | LLM API 密钥（可选） |
| `summarize_model` | `gpt-4o` | LLM 模型名称 |
| `summarize_prompt` | *(内置模板)* | LLM 摘要提示模板 |

## 输出文件

每个输入文件对应一个独立的输出目录 `{stem_name}_md/`：

```
output/
└── report_md/
    ├── report.md              # 摘要文件（含 chunk 链接）
    ├── report_0-4.md          # 第 0-4 页内容
    ├── report_5-9.md          # 第 5-9 页内容
    └── ...
```

**摘要文件格式**:

```markdown
# report Summary

> AI-generated summary

{LLM 生成的摘要文本}

## Page Chunks

- [report_0-4.md](report_0-4.md)
- [report_5-9.md](report_5-9.md)
```

## 日志文件

日志存储在 `logs/pdf2md-YYYYMMDD.log`，按天轮转。每条日志包含：
- 输入文件名和大小
- API 调用次数、页码范围和响应状态
- 每次请求耗时
- chunk 和 summary 文件名和大小
- 失败时的错误详情

## 退出码

- `0`: 所有文件转换成功
- `1`: 部分文件转换失败

## 目录结构

```
pdf2md/
├── pdf2md.py              # 主程序脚本
├── conf/setting.json      # 配置文件
├── requirements.txt       # Python 依赖
├── output/                # Markdown 输出目录（运行时生成）
└── logs/                  # 日志目录（运行时生成）
```

## 使用示例

```bash
# 转换单个文件
python pdf2md.py report.pdf

# 转换目录下所有支持的文件
python pdf2md.py ./documents/
```

## 项目文档

| 文档 | 说明 |
|------|------|
| [PRD](docs/spec/PRD.md) | 产品需求文档：产品概述、用户故事、功能需求、API 契约 |
| [APP_FLOW](docs/spec/APP_FLOW.md) | 应用流程文档：完整流程图、重试流程、错误处理矩阵 |
| [TECH](docs/spec/TECH.md) | 技术架构文档：技术选型、架构总览、模块说明、设计决策 |
| [FRONTEND](docs/spec/FRONTEND.md) | 前端规范文档：CLI 接口定义、输出示例、退出码说明 |
| [BACKEND](docs/spec/BACKEND.md) | 后端规范文档：API 接口规范、本地处理逻辑、日志系统 |
| [IMPLEMENTATION_PLAN](docs/spec/IMPLEMENTATION_PLAN.md) | 实施计划文档：实施阶段、变更清单、测试策略 |
| [PROGRESS](docs/spec/PROGRESS.md) | 进度文档：项目时间线、任务完成情况、关键指标 |
| [LESSON](docs/spec/LESSON.md) | 经验总结文档：经验教训、可复用模式、改进建议 |
