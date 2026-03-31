---
name: git
description: Git 工作流辅助工具
---

# Git 工作流

## 基本流程

1. **创建分支**: `git checkout -b feature/xxx`
2. **开发**: 修改代码
3. **提交**: `git add . && git commit -m "描述"`
4. **推送**: `git push origin feature/xxx`

## 提交信息规范

```
<type>: <subject>

<body>
```

### Type 类型
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档
- `style`: 格式
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建

## 分支命名

- `feature/xxx`: 功能分支
- `fix/xxx`: 修复分支
- `hotfix/xxx`: 紧急修复

## Git Worktree

### 适用场景

- 需要为不同 agent 或不同任务提供独立工作目录时
- 希望避免多个任务在同一目录下互相覆盖文件时
- 想在不复制整个仓库的前提下提供隔离工作区时

### 核心概念

- 一个仓库可以同时挂载多个工作目录
- 多个 worktree 共享同一个 Git 历史和对象库
- 每个 worktree 通常对应一个独立分支和一个独立目录

### 常用命令

```bash
git worktree list
git worktree add <path> -b <branch>
git worktree remove <path>
git worktree prune
```

### 推荐流程

1. 先查看现有工作树：`git worktree list`
2. 为新任务创建独立目录和分支：`git worktree add <path> -b <branch>`
3. 在新目录中执行该任务，避免污染主工作区
4. 任务结束后清理工作树：`git worktree remove <path>`
5. 如有失效记录，再执行：`git worktree prune`

### 使用规则

- 为每个隔离任务使用独立分支名
- 不要让多个 worktree 同时使用同一个分支
- 在删除 worktree 前，先确认其中没有未提交改动
- 不要把 worktree 当成独立仓库，它们共享同一个 Git 数据库
- 如果任务需要长期隔离执行，优先使用 worktree 而不是手动复制项目目录
