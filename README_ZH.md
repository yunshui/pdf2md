# pdf2md

通过远程 API 将 PDF、DOCX、DOC 和 TXT 文件转换为 Markdown 格式。

## 快速开始

```bash
pip install -r requirements.txt
python pdf2md.py <文件或目录路径>
```

## 功能特性

- **多格式支持**: PDF、DOCX、DOC、TXT
- **批量处理**: 传入目录可一次性转换所有支持的文件
- **重试机制**: 可配置的网络请求重试次数和超时时间
- **文件重名处理**: 如果输出文件已存在，自动添加随机后缀（如 `report_abcde.md`）
- **详细日志**: 按天记录日志，包含耗时、重试次数、错误详情等信息

## 配置说明

配置文件位于 `conf/setting.json`（首次运行时自动生成）：

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `api_url` | `http://123.192.49.73:8000/convert2markdown` | API 接口地址 |
| `client_id` | `bf-mkd` | API 客户端标识 |
| `max_retries` | `3` | 最大重试次数 |
| `retry_delay` | `2` | 重试间隔（秒） |
| `timeout` | `120` | 请求超时时间（秒） |
| `output_dir` | `output` | Markdown 输出目录 |
| `log_dir` | `logs` | 日志存储目录 |

## 输出文件

- 转换后的 Markdown 文件保存在 `output/` 目录下
- 如果同名文件已存在，自动追加 5 位随机字符（例如 `report_abcde.md`）

## 日志文件

日志存储在 `logs/pdf2md-YYYYMMDD.log`，按天轮转。每条日志包含：
- 输入文件名和 Base64 编码大小
- API 调用次数和响应状态
- 每次请求耗时
- 输出文件名和大小
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
