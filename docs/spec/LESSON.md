# LESSON.md - Lessons Learned Document

**Project**: pdf2md
**Date**: 2026-05-21
**Version**: 1.0

---

## 1. 项目回顾

pdf2md 项目从需求确认到实现完成，共经历 22 次提交、16 轮代码审查。通过子代理驱动开发模式（Subagent-Driven Development），每个任务独立实现并经两轮审查（Spec 合规审查 + 代码质量审查），确保了代码质量。后续补充了 34 个自动化测试，覆盖了全部核心函数和集成流程。

---

## 2. 做得好的方面

### 2.1 设计阶段投入充分

- 先进行需求澄清（确认输入格式、输出位置、文件名策略），再设计方案
- 提出了 3 种架构方案（单文件、模块化、面向对象），选择最适合的单文件方案
- 设计文档和计划文档在编码前完成，避免了方向性错误

**经验**: 花在设计和澄清上的时间，远比花在修复错误实现上的时间少。

### 2.2 子代理驱动开发有效

- 每个任务独立分发给子代理，上下文清晰，不受前面任务干扰
- 每任务两轮审查（Spec + 质量），发现问题 15 个，修复 14 个
- 审查发现的典型问题：Logger Handler 重复添加、路径解析不一致、竞争条件

**经验**: 每任务审查的成本远低于事后调试的成本。

### 2.3 错误处理完善

- 配置文件三种错误路径（不存在、格式错误、类型错误）都有明确反馈
- 主循环中每个文件的失败都被隔离，不影响其他文件
- 退出码正确反映整体处理结果

**经验**: 错误处理不是"额外工作"，是核心功能的一部分。

---

## 3. 遇到的问题与教训

### 3.1 代码审查发现了真正的 Bug

**问题**: Logger 的 Handler 在重复调用 `setup_logging()` 时会累积（Task 2 审查发现）。

**影响**: 如果脚本被测试框架多次调用，日志会重复输出。

**教训**: 即使简单的初始化函数也可能有隐藏的边界情况。代码审查的价值在于发现开发者"看不见"的问题。

### 3.2 路径解析不一致

**问题**: `load_config()` 使用 `script_dir` 解析路径，但 `setup_logging()` 直接使用配置中的相对路径（相对于 CWD）。

**影响**: 用户从不同目录运行脚本时，日志和输出文件会出现在不同位置。

**教训**: 路径解析策略必须全局一致。统一在 `main()` 中将相对路径解析为绝对路径后再传递。

### 3.3 文件读取与 getsize 的竞争条件

**问题**: 先读取文件（`file_to_base64`），再获取文件大小（`os.path.getsize`）。如果文件在两次调用之间被删除，会抛出未捕获的异常。

**教训**: 先获取大小，再读取内容。获取大小的操作应该在读取之前。

### 3.4 函数签名中的死参数

**问题**: `file_to_base64()` 被要求接受 `logger` 参数，但函数体内从未使用（Task 3 Spec 审查发现）。

**教训**: 不要盲目接受计划中的函数签名。如果参数不需要，就不应该存在。这减少了 API 的表面复杂度。

### 3.5 日志格式风格不一致

**问题**: 部分代码使用 f-string 日志（`logger.info(f"...{var}...")`），部分使用懒加载格式（`logger.info("...%s...", var)`）。

**教训**: 统一使用懒加载格式（`%s`），避免日志级别低于阈值时不必要的字符串格式化。

### 3.6 请求异常覆盖不全

**问题**: `call_api()` 只捕获了 `ConnectionError` 和 `Timeout`，遗漏了 `SSLError`、`TooManyRedirects` 等其他 `RequestException` 子类（最终审查发现）。

**教训**: 异常处理应该捕获基类（`RequestException`），而非逐一列举子类。基类捕获兜底，特定子类可以有特殊处理（如 JSONDecodeError 不重试）。

### 3.8 类型检查中 `__name__` 在元组上失败

**问题**: `load_config()` 中使用 `expected_type.__name__` 生成错误信息，但当 `expected_type` 是元组（如 `(int, float)`）时会抛出 `AttributeError`（测试修复发现）。

**教训**: 元组类型检查需要特殊处理，使用 `'/'.join(t.__name__ for t in expected_type)` 生成可读的错误信息。

### 3.9 测试中的配置隔离

**问题**: `main()` 总是从 `__file__` 所在目录读取配置，测试中创建的临时配置不会被读取（集成测试修复发现）。

**教训**: 通过 `patch("pdf2md.load_config")` 直接返回测试配置，避免测试依赖文件系统路径。

**问题**: `extract_md_content()` 假设 `results` 中所有值都是 dict，如果 API 返回异常格式会引发 `AttributeError`（最终审查发现）。

**教训**: 对外部 API 的响应做类型保护。不要信任外部数据的结构。

---

## 4. 可复用的模式

### 4.1 配置加载模式

```
查找配置 → 不存在则创建默认 → 解析 → 验证键 → 验证类型 → 返回
```

适用于所有需要配置的工具类脚本。

### 4.2 批量处理循环模式

```
for item in items:
    try:
        process(item)
    except Exception as e:
        log_error(e)
        failure_count += 1
        continue
    success_count += 1
```

确保单个失败不影响整体流程。

### 4.3 重试循环模式

```
for attempt in range(1, max_retries + 1):
    try:
        result = do_something()
        return result
    except RetriableError as e:
        if attempt < max_retries:
            sleep(delay)
            continue
        return None
    except NonRetriableError:
        return None  # 不重试
```

区分可重试错误和不可重试错误。

### 4.4 文件名冲突处理模式

```
path = f"{base_name}.ext"
if not exists(path):
    return path
while exists(path):
    suffix = random_string(5)
    path = f"{base_name}_{suffix}.ext"
return path
```

简单有效，适用于文件生成场景。

---

## 5. 改进建议（未来项目）

1. **自动化测试先行**: 在编码前先写好测试，而不是事后补充
2. **类型注解**: 使用 Python 类型注解（mypy）在静态分析阶段捕获类型错误
3. **配置 Schema**: 使用 pydantic 或 jsonschema 验证配置，替代手动类型检查
4. **文件大小限制**: 从一开始就添加 max_file_size 配置项
5. **CI/CD**: 设置 GitHub Actions 自动运行测试和 lint

---

## 6. 关键数据总结

| 指标 | 值 |
|------|-----|
| 总提交数 | 22 |
| 总代码行数 | 374（pdf2md.py） |
| 自动化测试 | 34（全部通过） |
| 代码审查轮次 | 16 |
| 审查发现问题数 | 17 |
| 已修复问题数 | 17 |
| 未修复问题数 | 0 |
| 需求覆盖度 | 28/28（100%） |
| 依赖数 | 1（requests） |
