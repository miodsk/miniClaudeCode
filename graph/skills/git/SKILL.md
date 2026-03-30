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
