# APP_FLOW.md - Application Flow Document

**Project**: pdf2md
**Date**: 2026-05-21
**Version**: 1.0

---

## 1. 整体流程图

```
START
  │
  ▼
[1. 解析命令行参数]
  │
  ├─ 无参数 → 显示帮助信息 → EXIT(2)
  │
  └─ 有参数
       │
       ▼
[2. 验证路径存在性]
  │
  ├─ 路径不存在 → 输出错误到 stderr → EXIT(1)
  │
  └─ 路径存在
       │
       ▼
[3. 加载配置 conf/setting.json]
  │
  ├─ 文件不存在 → 创建 conf/ 目录 → 写入默认配置 → 返回默认值
  ├─ JSON 格式错误 → 输出错误 → EXIT(1)
  ├─ 缺少必需字段 → 输出错误 → EXIT(1)
  ├─ 字段类型错误 → 输出错误 → EXIT(1)
  └─ 配置正常 → 返回配置字典
       │
       ▼
[4. 解析相对路径为绝对路径]
  │  log_dir  和 output_dir 如果不是绝对路径，则相对于脚本目录解析
       │
       ▼
[5. 初始化日志系统]
  │  创建 logs/ 目录（如不存在）
  │  创建日志文件 pdf2md-YYYYMMDD.log
  │  注册文件 Handler（DEBUG 级别）和控制台 Handler（INFO 级别）
       │
       ▼
[6. 解析输入文件列表]
  │
  ├─ 路径是文件
  │   ├─ 扩展名在支持列表 → 返回 [文件路径]
  │   └─ 扩展名不在支持列表 → 输出警告日志 → 返回 []
  │
  ├─ 路径是目录
  │   ├─ glob 匹配 *.{pdf,docx,doc,txt} → 去重、排序 → 返回文件列表
  │   └─ 无匹配文件 → 输出警告日志 → 返回 []
  │
  └─ 文件列表为空 → 输出错误 → EXIT(1)
       │
       ▼
[7. 创建 output/ 目录（如不存在）]
       │
       ▼
[8. 逐文件处理循环]
  │
  │  success_count = 0, failure_count = 0
  │
  │  ┌─────────────────────────────────────┐
  │  │ 对于每个 file_path:                 │
  │  │                                     │
  │  │  [8.1 读取文件并 Base64 编码]       │
  │  │   ├─ 成功 → 记录原始大小、base64大小│
  │  │   └─ 失败(OSError) → 记录错误       │
  │  │                  → failure_count++  │
  │  │                  → continue         │
  │  │                                     │
  │  │  [8.2 调用 API（带重试）]           │
  │  │   循环 1..max_retries:              │
  │  │     ├─ 发送 POST 请求               │
  │  │     ├─ 200 → 解析 JSON → 返回结果   │
  │  │     ├─ 非200 → 记录错误 → 继续重试  │
  │  │     ├─ 连接/超时错误 → 继续重试     │
  │  │     ├─ JSON 解析错误 → 立即返回 None│
  │  │     └─ 超过重试次数 → 返回 None     │
  │  │                                     │
  │  │  [8.3 处理 API 响应]               │
  │  │   ├─ 返回 None → 记录失败           │
  │  │   │              → file_ok = False  │
  │  │   │                                 │
  │  │   └─ 返回结果 → 提取 md_content     │
  │  │       ├─ 无内容 → 记录警告          │
  │  │       └─ 有内容 → 逐条写入文件      │
  │  │           ┌─ 生成唯一输出路径       │
  │  │           │  ├─ 不存在 → 直接使用   │
  │  │           │  └─ 已存在 → 追加随机后缀│
  │  │           │                        │
  │  │           ├─ 写入 .md 文件（UTF-8） │
  │  │           ├─ 成功 → 记录输出信息    │
  │  │           └─ 失败(OSError) → 记录   │
  │  │              → file_ok = False      │
  │  │                                     │
  │  │  [8.4 更新计数器]                  │
  │  │   ├─ file_ok == True → success++    │
  │  │   └─ file_ok == False → failure++   │
  │  └─────────────────────────────────────┘
  │
  ▼
[9. 输出汇总日志]
  │  "Processed X files: Y success, Z failed"
       │
       ▼
[10. 退出]
  │
  ├─ failure_count == 0 → EXIT(0)
  └─ failure_count > 0  → EXIT(1)
       │
       ▼
END
```

---

## 2. API 调用重试流程

```
call_api(config, logger, base64_content, file_name)
  │
  │  for attempt in 1..max_retries:
  │    │
  │    ├─ 记录: "Calling API for {name} (attempt {n}/{max})"
  │    ├─ 记录开始时间
  │    │
  │    ├─ POST → 收到响应
  │    │   │
  │    │   ├─ HTTP 200
  │    │   │   ├─ 解析 JSON
  │    │   │   │   ├─ 成功 → 记录状态和耗时 → RETURN response
  │    │   │   │   └─ 失败(JSONDecodeError) → 记录错误 → RETURN None (不重试)
  │    │   │   │
  │    │   └─ HTTP 非 200 → 记录状态码和耗时
  │    │       ├─ attempt < max_retries → sleep(retry_delay) → continue
  │    │       └─ 已达最大重试次数 → RETURN None
  │    │
  │    └─ 请求异常 (ConnectionError/Timeout/SSL等)
  │        ├─ attempt < max_retries → sleep(retry_delay) → continue
  │        └─ 已达最大重试次数 → RETURN None
  │
  └─ RETURN None (循环结束兜底)
```

---

## 3. 文件名冲突处理流程

```
get_unique_path(output_dir, base_name)
  │
  ├─ path = "{output_dir}/{base_name}.md"
  │   │
  │   └─ 文件不存在 → RETURN path
  │
  └─ 文件已存在
       │
       └─ while 文件存在:
              │
              ├─ suffix = 5个随机小写字母 (如 "abcde")
              ├─ path = "{output_dir}/{base_name}_{suffix}.md"
              │
              └─ 文件不存在 → 退出循环 → RETURN path
```

---

## 4. 错误处理矩阵

| 错误场景 | 处理方式 | 日志级别 | 是否中断 | 是否重试 |
|----------|----------|----------|----------|----------|
| 路径不存在 | stderr 输出错误，退出 | - | 是 | - |
| 配置文件不存在 | 创建默认配置 | - | 否 | - |
| 配置文件 JSON 格式错误 | stderr 输出错误，退出 | - | 是 | - |
| 配置文件缺少必需字段 | stderr 输出错误，退出 | - | 是 | - |
| 配置文件字段类型错误 | stderr 输出错误，退出 | - | 是 | - |
| 文件扩展名不支持 | 跳过，继续处理下一个 | WARNING | 否（该文件） | - |
| 文件读取失败 (OSError) | 跳过，继续处理下一个 | ERROR | 否（该文件） | - |
| API 连接失败 | 记录错误，继续重试 | ERROR | 否 | 是 |
| API 超时 | 记录错误，继续重试 | ERROR | 否 | 是 |
| API 其他请求异常 (SSL等) | 记录错误，继续重试 | ERROR | 否 | 是 |
| API 返回非 200 | 记录错误，继续重试 | ERROR | 否 | 是 |
| API 返回无效 JSON | 记录错误，不重试 | ERROR | 否（该文件） | 否 |
| API 成功但无 md_content | 记录警告，视为成功 | WARNING | 否 | - |
| 输出文件写入失败 (OSError) | 记录错误，该文件标记失败 | ERROR | 否（该文件） | - |
