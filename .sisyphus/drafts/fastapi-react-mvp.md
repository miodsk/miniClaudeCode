# Draft: FastAPI React MVP

## Requirements (confirmed)
- 范围：完整 MVP
- 前端：React 19 + Vite + TypeScript
- 状态管理：Zustand
- 后端：FastAPI
- 部署/开发：前后端分离，本地开发
- 会话模型：本地单用户单会话
- 通信：WebSocket
- LLM 输出：结构化 JSON
- TTS：阿里云 TTS
- TTS 时机：整条回复完成后再播报
- researcher/coder 事件展示：右侧独立事件面板
- WebSocket 协议：细粒度事件流
- Assistant 文本传输：流式推送，TTS 在整条完成后生成
- 连接模型：单个 WebSocket 双向通信
- 前端消息层：使用 Vercel AI SDK

## Technical Decisions
- Assistant 回复与 emotion 同次结构化输出，避免二次分析
- WebSocket 作为统一实时通道，后续承载聊天事件、team 事件、TTS、Live2D 指令
- MVP 先按本地单会话设计，不引入多会话复杂度
- Assistant 文本采用流式事件推送，语音采用完成后单次生成，兼顾体验与实现复杂度
- 前后端通过单条 WebSocket 完成消息上行与事件下行，避免 HTTP/WS 双协议状态同步
- 前端聊天状态、消息对象与流式渲染优先对齐 Vercel AI SDK 数据模型

## Research Findings
- `main.py` 当前通过 `query = input()` 驱动 lead 循环
- `team_cycle()` 会消费 researcher/coder 邮箱并返回代理回复
- `execute_tool_calls()` 会把 tool result 追加回消息流
- `prepare_main_messages()` 会注入后台任务通知并做压缩
- 当前系统适合抽出一个 chat engine，供 CLI 与 Web 共用

## Open Questions
- 会话重置/历史恢复的 UX 方式
- 工具调用和 team 事件在前端显示到什么粒度
- Vercel AI SDK 是仅用于前端消息状态，还是后端协议也要兼容 AI SDK stream 格式

## Scope Boundaries
- INCLUDE: Web 聊天、结构化回复、team 事件面板、阿里云 TTS、WebSocket 事件协议
- EXCLUDE: 多用户、多会话、持久化数据库、Mem0、MCP 接入、Live2D 最终实现细节
