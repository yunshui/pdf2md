---
name: update-docs
description: Auto-update project documentation to reflect recent code changes
---

# update-docs - Auto Update Project Documentation

**Type**: Maintenance skill
**Trigger**: After any code change, feature implementation, or milestone completion
**Purpose**: Automatically update all project documentation to reflect current state

---

## How to Use

Invoke this skill when:
- A feature has been implemented and committed
- A bug has been fixed
- A code review has been completed
- A milestone is reached
- New lessons have been learned

The skill will:
1. Discover all existing project documentation
2. Analyze recent git changes
3. Update PROGRESS.md with new timeline, metrics, and status
4. Update LESSON.md with new lessons learned
5. Update IMPLEMENTATION_PLAN.md with completion status
6. Update TECH.md if architecture changed
7. Update FRONTEND.md/BACKEND.md if interfaces changed
8. Update README.md/README_ZH.md if user-facing changes
9. Update CLAUDE.md if project structure changed
10. Commit all documentation changes together

---

## Document Registry

Scan the project root and `docs/` directory for these files:

### Core Documents (docs/spec/)

| File | What to Update |
|------|---------------|
| `PRD.md` | Update feature completion table, add new requirements if scope expanded |
| `APP_FLOW.md` | Update flowcharts if new flows added, update error matrix |
| `TECH.md` | Update architecture diagram, add new modules, update design decisions |
| `FRONTEND.md` | Update CLI examples, add new output formats, update exit codes |
| `BACKEND.md` | Update API contract, add new error types, update logging entries |
| `IMPLEMENTATION_PLAN.md` | Update phase completion, add new test results, update review records |
| `PROGRESS.md` | **Always update**: timeline, task status, metrics, commit count, review stats |
| `LESSON.md` | **Always update**: add new lessons, update patterns, update metrics |

### User-Facing Documents (project root)

| File | What to Update |
|------|---------------|
| `README.md` | Update features table, add new usage examples, update file structure |
| `README_ZH.md` | Same as README.md but in Chinese |
| `CLAUDE.md` | Update file structure, add new config fields, update doc links |

### Design Documents (docs/superpowers/)

| File | What to Update |
|------|---------------|
| `docs/superpowers/specs/*.md` | Link from IMPLEMENTATION_PLAN.md if referenced |
| `docs/superpowers/plans/*.md` | Mark tasks as completed in PROGRESS.md |

---

## Update Procedures

### 1. Analyze Recent Changes

Run these commands to understand what changed:

```bash
# Recent commits
git log --oneline -10

# Files changed in recent commits
git diff --stat HEAD~5..HEAD

# Current project state
git status
```

### 2. Update PROGRESS.md

**Always update these sections:**

- **时间线 (Timeline)**: Append new events with timestamp
- **任务完成情况**: Update task status
- **代码审查统计**: Add new review rounds
- **关键指标**: Recalculate code lines, commit count, test coverage
- **遗留问题**: Add new TODOs or mark resolved

**Template for timeline entry:**
```markdown
| YYYY-MM-DD HH:MM | 事件描述 | 产出/影响 |
```

**Template for metrics:**
```markdown
| 代码行数 | {wc -l pdf2md.py} | < 500 | {pass/fail} |
| 提交次数 | {git rev-list --count HEAD} | - | - |
```

### 3. Update LESSON.md

**Check if any of these patterns occurred:**

- **Bug found and fixed**: Add to "遇到的问题与教训" section
- **Design decision made**: Add to "可复用的模式" section
- **Review feedback**: Extract the lesson, add to lessons learned
- **Performance optimization**: Add as a pattern or lesson

**Template for new lesson:**
```markdown
### X.Y [简短标题]

**问题**: [描述遇到的问题]

**影响**: [如果不修复会怎样]

**教训**: [从中学到什么，如何避免]
```

**Template for new pattern:**
```markdown
### X.Y [模式名称]

```python/code
[可复用代码模式]
```

[适用场景说明]
```

### 4. Update IMPLEMENTATION_PLAN.md

**Update sections:**
- **实施阶段**: Mark completed steps with ✅, add new phases
- **代码审查记录**: Add new review entries with issues found/fixed
- **测试策略**: Mark completed tests, add new test cases
- **技术决策记录**: Add new decisions with rationale

### 5. Update TECH.md

**Update if:**
- New files added/removed → Update architecture diagram
- New dependencies → Update external dependencies table
- New functions → Update function inventory table
- Design change → Add new entry to design decisions

### 6. Update FRONTEND.md / BACKEND.md

**Update if:**
- New CLI arguments → Update 命令行接口 section
- New output formats → Update 控制台输出 section
- New API behavior → Update API 接口 section
- New error types → Update 错误场景 table
- New log entries → Update 关键日志事件 table

### 7. Update README.md / README_ZH.md

**Update if:**
- New features → Add to 功能特性 / Features list
- New config fields → Update 配置说明 / Configuration table
- New file structure → Update 目录结构 / File Structure
- New doc files → Add to 项目文档 / Documentation table

### 8. Update CLAUDE.md

**Update if:**
- New project files → Update File Structure section
- New config options → Update Configuration section
- New doc files → Update Documentation section

---

## Document Linking Rules

### Cross-Reference Matrix

```
PRD.md
  ← referenced by: IMPLEMENTATION_PLAN.md (requirements mapping)
  → references: nothing

APP_FLOW.md
  ← referenced by: FRONTEND.md, BACKEND.md
  → references: PRD.md (FR-IDs)

TECH.md
  ← referenced by: IMPLEMENTATION_PLAN.md (decisions)
  → references: PRD.md (NFRs)

FRONTEND.md
  ← referenced by: README.md
  → references: APP_FLOW.md

BACKEND.md
  ← referenced by: README.md
  → references: APP_FLOW.md, PRD.md (API contract)

IMPLEMENTATION_PLAN.md
  ← referenced by: PROGRESS.md
  → references: TECH.md, PRD.md

PROGRESS.md
  ← referenced by: README.md (via status badge concept)
  → references: IMPLEMENTATION_PLAN.md

LESSON.md
  ← referenced by: nothing
  → references: PROGRESS.md (metrics)

README.md / README_ZH.md
  ← entry point
  → references: all docs/spec/ files

CLAUDE.md
  ← AI assistant entry point
  → references: README.md, all docs/spec/ files
```

### Linking Format

When adding links to any document, use this format:

**In README.md / README_ZH.md:**
```markdown
| [PRD](docs/spec/PRD.md) | Product requirements |
```

**In CLAUDE.md:**
```markdown
| [PRD](docs/spec/PRD.md) | Product requirements, user stories, feature specs |
```

**In IMPLEMENTATION_PLAN.md:**
```markdown
See [TECH.md § Design Decisions](TECH.md#5-关键设计决策) for rationale.
```

---

## Automation Checklist

When this skill is invoked, follow this checklist:

- [ ] Run `git log --oneline -10` to see recent changes
- [ ] Run `git diff --stat HEAD~N..HEAD` to see changed files
- [ ] Identify which documents need updates based on what changed
- [ ] Update PROGRESS.md (always)
- [ ] Update LESSON.md if new lessons learned
- [ ] Update IMPLEMENTATION_PLAN.md if tasks completed
- [ ] Update TECH.md if architecture changed
- [ ] Update FRONTEND.md if CLI/output changed
- [ ] Update BACKEND.md if API/logic changed
- [ ] Update README.md if user-facing changed
- [ ] Update README_ZH.md if user-facing changed (Chinese)
- [ ] Update CLAUDE.md if project structure changed
- [ ] Verify all document links are valid
- [ ] Commit all documentation changes together:
  ```bash
  git add docs/ README.md README_ZH.md CLAUDE.md
  git commit -m "docs: auto-update documentation for <change description>"
  ```

---

## Quick Reference

| Change Type | Documents to Update |
|-------------|-------------------|
| New feature | PROGRESS, PLAN, TECH, FRONTEND/BACKEND, READMEs, CLAUDE, LESSON |
| Bug fix | PROGRESS, LESSON, PLAN (review record) |
| Config change | FRONTEND, BACKEND, READMEs, CLAUDE |
| New dependency | TECH, requirements.txt |
| New file/module | TECH, APP_FLOW, PROGRESS |
| API change | BACKEND, APP_FLOW, FRONTEND, PRD |
| Review completion | PROGRESS, LESSON, PLAN |
| Milestone | PROGRESS, PLAN, READMEs, LESSON |
