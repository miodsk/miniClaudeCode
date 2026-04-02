# Live2D Chat Web 应用规格

## 1. 概述

将 CLI 交互界面迁移到 Web 前端，使用 Live2D 看板娘作为 lead 的视觉化身。

**技术栈**:
- 后端: FastAPI (Python)
- 前端: React + TypeScript + Vite
- 动画: Live2D Cubism 2.x (现有模型)
- LLM: DeepSeek Chat (已有)

## 2. 项目结构

```
claudestudy/
├── backend/
│   ├── main.py              # FastAPI 应用
│   ├── api/
│   │   └── chat.py          # 聊天 API 路由
│   └── core/
│       ├── chat_engine.py   # 核心聊天引擎（从 main.py 提取）
│       └── session.py       # 会话状态管理
├── frontend/                 # React 项目
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── Live2DModel.tsx
│   │   │   └── MessageList.tsx
│   │   ├── hooks/
│   │   │   └── useChat.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── index.html
├── public/
│   └── live2d/              # Live2D 模型 (已有)
│       └── 341_casual-2023/
└── AGENTS.md                # (已有)
```

## 3. 后端 API 设计

### REST Endpoints

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/chat` | 发送消息，返回 AI 响应 |
| GET | `/api/history` | 获取对话历史 |
| POST | `/api/reset` | 重置会话 |
| GET | `/api/status` | 服务状态检查 |

### POST /api/chat

**请求**:
```json
{
  "message": "你好"
}
```

**响应**:
```json
{
  "response": "你好！有什么可以帮助你的吗？",
  "tool_calls": [
    {"name": "task_create", "args": {...}, "result": "..."}
  ],
  "team_events": [
    {"agent": "researcher", "content": "..."}
  ]
}
```

### 响应触发 Live2D 动画

通过响应内容中的情感关键字触发 Live2D 动画：

| 关键字 | 动画 |
|--------|------|
| 思考、想想、考虑 | thinking01 |
| 开心、高兴、好的 | smile01 |
| 抱歉、遗憾、难过 | sad01 |
| 惊讶、哇、真的吗 | surprised01 |
| 生气、愤怒 | angry01 |

## 4. 前端组件

### ChatInterface
- 消息列表（滚动）
- 输入框 + 发送按钮
- 加载状态显示

### Live2DModel
- 加载 Live2D 模型
- 播放表情/动作
- 与后端通信触发动画

### MessageList
- 用户消息（右侧）
- AI 消息（左侧）
- Tool call 结果展示

## 5. Live2D 集成

### 模型位置
`public/live2d/341_casual-2023/`

### 支持的动画
- **动作**: idle01 (待机), nod01 (点头), smile01-07, angry01-07, cry01-06, sad01-02, surprised01-02, thinking01-02 等
- **表情**: default, smile01-07, angry01/02/07, cry01-04, sad01/02, serious01/02, surprised01/02, thinking01/02 等

### 动画触发逻辑
1. 后端返回响应时分析情感关键字
2. 通过 WebSocket 或轮询推送动画指令
3. 前端播放对应表情/动作

## 6. 后端核心逻辑

从 `main.py` 提取的聊天引擎保持不变：

```
用户消息 → TeamManager → DeepSeek LLM → 工具执行 → 团队周期 → 响应
```

关键组件：
- `TeamManager`: 多代理管理
- `execute_tool_calls`: 工具调用执行
- `prepare_main_messages`: 消息准备/压缩
- `BG_MANAGER`: 后台任务管理

## 7. 依赖

### 后端 (pyproject.toml)
```toml
dependencies = [
    ...
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "sse-starlette>=2.2.0",
]
```

### 前端 (frontend/package.json)
```json
{
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "@live2d/core": "...",
    "pixi-live2d": "..."
  }
}
```

## 8. 开发流程

1. **Phase 1**: FastAPI 后端搭建
   - 创建 backend 目录结构
   - 实现 /api/chat 端点
   - 测试与 main.py 等效的功能

2. **Phase 2**: React 前端基础
   - Vite + React 项目初始化
   - ChatInterface 组件
   - API 集成

3. **Phase 3**: Live2D 集成
   - Live2D 模型加载
   - 动画触发系统
   - 表情/动作映射
