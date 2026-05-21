# Document Update Templates

Reusable templates for updating specific document sections.

---

## PROGRESS.md Templates

### Timeline Entry
```markdown
| YYYY-MM-DD HH:MM | [事件类别]: [简要描述] | [产出文件/影响范围] |
```

### Review Record Entry
```markdown
| Task N | [审查类型] | [审查范围] | [发现问题数] | [修复数] |
```

### Metric Row
```markdown
| [指标名称] | [当前值] | [目标值] | {pass/fail} |
```

---

## LESSON.md Templates

### New Lesson
```markdown
### X.Y [简短标题]

**问题**: [描述]

**影响**: [如果不处理会怎样]

**教训**: [如何避免/最佳实践]
```

### New Pattern
```markdown
### X.Y [模式名称]

```python
[可复用代码]
```

[适用场景说明]
```

---

## IMPLEMENTATION_PLAN.md Templates

### New Phase Entry
```markdown
### 阶段 N: [阶段名称]（✅ 已完成 / 🔄 进行中 / ⏳ 待开始）

| 步骤 | 内容 | 产出 |
|------|------|------|
| N.1 | [具体任务] | [产出物] |
```

### Review Record Entry
```markdown
| 审查轮次 | 审查范围 | 发现问题 | 修复情况 |
|----------|----------|----------|----------|
| N | [Task/模块] | [数量和类型] | [已修复/待修复] |
```

---

## TECH.md Templates

### New Module Entry
```markdown
### 3.N [模块名称]

```python
[函数签名或接口定义]
```

| 属性 | 值 |
|------|-----|
| 参数 | [参数列表] |
| 返回值 | [返回类型] |
| 职责 | [做什么] |
| 依赖 | [依赖哪些模块] |
```

### New Design Decision
```markdown
### 5.N [决策名称]

**决策**: [做了什么决定]

**理由**: [为什么这么做]

**约束**: [有什么限制]
```

---

## BACKEND.md Templates

### New Log Entry
```markdown
| [事件名称] | [级别] | `[日志示例消息]` |
```

### New Error Scenario
```markdown
| [错误类型] | [表现] | [处理] |
```

---

## FRONTEND.md Templates

### New CLI Example
```markdown
#### 场景 N: [场景名称]

```bash
python pdf2md.py [参数]
```

输出：
```
[预期输出]
```

退出码: [0/1]
```

---

## README Templates

### New Feature Entry
```markdown
- **[特性名称]**: [简要描述]
```

### New Doc Link
```markdown
| [DOC_NAME](docs/spec/DOC_NAME.md) | [英文描述] |
```

### New Doc Link (Chinese)
```markdown
| [DOC_NAME](docs/spec/DOC_NAME.md) | [中文描述] |
```
