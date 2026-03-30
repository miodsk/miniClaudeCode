---
name: test
description: 测试最佳实践
---

# 测试最佳实践

## 测试文件命名

```
tests/test_xxx.py          # 单元测试
tests/test_xxx_integration.py  # 集成测试
```

## pytest 基本用法

```python
import pytest

def test_xxx():
    assert result == expected
```

## 测试结构

1. **Arrange**: 准备数据
2. **Act**: 执行操作
3. **Assert**: 验证结果

## 覆盖率

- 目标: 80%+
- 关键路径必须覆盖
- 边界条件要测试
