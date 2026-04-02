# Live2D Lead Web UI

## TL;DR
> **Summary**: 将当前 `main.py` 驱动的 CLI lead 交互改造成浏览器主界面：Python/FastAPI 继续承载 agent harness，现有 `frontend/` React/Vite 应用承载聊天 UI，Vercel AI SDK 负责 assistant 文本消息层；当前阶段只打通 **POST-based SSE 文本流**，由前端使用 `@microsoft/fetch-event-source` 消费；Live2D 不作为本计划的技术选型核心，而是作为**已有前端能力 / 集成前提**处理。
> **Deliverables**:
> - 可复用的 Python chat engine（从 CLI loop 提取）
> - FastAPI `health/session/chat/reset` API 与静态资源挂载
> - 基于现有 `frontend/` 的 POST-based SSE transport + browser chat shell
> - 固定的 `metadata.live2d` 契约，供前端已有 Live2D 能力消费
> - JSON 会话持久化 + mem0 长期记忆适配层（可选增强）
> - 可用的 CLI debug 入口
> **Effort**: L
> **Parallel**: YES - 3 waves
> **Critical Path**: 0 → 1 → 2 → 3 → 4 → 7 → 8 → 9

## Context
### Original Request
- 使用 Live2D 作为 lead 的表达方式。
- 浏览器前端成为新的主交互界面。
- 前端聊天层使用 Vercel AI SDK。

### Clarified Scope
- Live2D 相关底层实现不是本次计划的主问题；默认用户已在前端实现模型加载与动作播放能力。
- 当前阶段只约束 **backend `metadata.live2d` 契约**、**POST-based SSE 文本流**、**Web chat shell**、以及 **前端已有 Live2D 能力的集成边界**。
- 音频明确延期到后续阶段，不属于当前任务范围、验收条件或依赖关系。
- 不在本计划内重新选型或重写 Live2D runtime；不把 `pixi-live2d-display` / Pixi 版本链路作为实现主线。

### Manual Review Summary
- 当前 `main.py` 仍包含完整 lead loop orchestration，尚未抽离到 `backend/core/`。
- `backend/api/` 与 `backend/core/` 目录已存在但为空。
- `pyproject.toml` 当前只有 `mem0ai`，没有 `fastapi` / `uvicorn`。
- `frontend/` 已存在，并非 greenfield：`HomeChatPanel.tsx` 是静态展示页，`Canvas.tsx` 是旧 Live2D 实验代码。
- `frontend/package.json` 已包含 `@microsoft/fetch-event-source`，可直接作为 POST-based SSE 客户端能力。
- 仓库内旧文档 `docs/plans/2026-04-01-live2d-chat-design.md` 与本计划冲突：其旧模型路径和前端情绪推断逻辑均不得再作为实现依据。

### Supersession / Single Source of Truth
- 本文件是 Web UI 迁移的唯一实现计划。
- `docs/plans/2026-04-01-live2d-chat-design.md` 仅保留为历史背景，不得作为当前执行依据。
- 废弃路径：
  - `public/live2d/341_casual-2023/` 作为正式模型接入路径
  - 前端根据 assistant 文本内容自行推断 emotion
  - 旧 `Canvas.tsx` 中硬编码动作名作为正式行为契约

## Work Objectives
### Core Objective
- 在不破坏现有 Python harness 核心行为的前提下，交付一个以 Web 为主入口的 lead 聊天界面，并通过 **POST-based SSE 文本流** 与固定 metadata 契约让前端安全消费文本和 Live2D 状态。

### Deliverables
- `backend/` 下完整的 FastAPI 应用与可复用核心模块。
- `frontend/` 下基于现有 Vite/React 应用改造的 POST-based SSE transport 与聊天 UI。
- 固定的 `metadata.live2d` 契约与前端消费边界。
- JSON 会话持久化方案与 mem0 长期记忆适配层。
- 保持可用的 CLI 调试入口。

### Definition of Done (verifiable)
- `uv run python -m unittest discover tests -v` 通过。
- `uv run python -c "from backend.main import app; print(app.title)"` 成功导入 FastAPI 应用。
- 在 `frontend/` 下 `npm install && npm run test -- --run && npm run build` 通过。
- `curl http://127.0.0.1:8000/api/health` 返回健康状态。
- `POST /api/chat` 直接返回 `text/event-stream` 响应，并能持续输出 assistant 文本事件。
- SSE 文本流能驱动 assistant message 增量渲染，且接口事件中包含可消费的 `metadata.live2d`。
- 页面刷新后能从 JSON 会话恢复消息；`POST /api/reset` 清空 JSON 会话但不要求清空 mem0。
- 前端已有 Live2D 能力可仅通过 `metadata.live2d` 与临时 loading state 接线，不要求在本计划中重写 runtime。

### Must Have
- Python 后端是会话与 agent 执行的唯一真相源。
- 后端负责分配 `assistant_message_id` / `turn_id`，前端不得自行生成回复标识。
- 前端只消费 `metadata.live2d`，不得自行推断 emotion。
- 当前阶段仅做文本流式返回；音频不作为当前接口 contract、UI contract 或 QA 条件的一部分。
- Live2D 是集成前提，不是本计划的 runtime 选型战场。
- mem0 为可选增强层；启用失败不能阻塞 chat API。
- CLI 调试入口继续可用。

### Must NOT Have
- 不做多用户。
- 不做多会话列表。
- 不做完整 AI SDK stream protocol 兼容。
- 不做前端情绪分析。
- 不在当前阶段实现 WebSocket 音频、音频回放、音频同步或音频 side-channel。
- 不重写或重新选型 Live2D runtime。
- 不让执行者在实现时回退到旧文档或旧模型路径。

## Verification Strategy
- Test decision: tests-after；后端继续沿用 `unittest`，前端至少验证 `npm run test -- --run` + `npm run build`。
- QA policy: 每个任务都必须绑定命令型验收和至少 1 个 happy / 1 个 failure 场景。
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`

## Protocol Contract Principles
- 每次 assistant 回复由 backend 创建唯一 `assistant_message_id`（可等同于 `turn_id`）。
- 当前阶段采用 **POST-based SSE**：浏览器端通过 `@microsoft/fetch-event-source` 发起 `POST /api/chat`，并消费标准 `text/event-stream` 响应。
- 后端必须返回标准 SSE line-based framing：`event:` / `data:` / 空行结尾。
- 后端必须设置 `Content-Type: text/event-stream`；客户端通过 `AbortController` 终止进行中的流。
- SSE 最小事件语义：`start` / `delta` / `state` / `complete` / `error`。
- `metadata.live2d` 必须在当前阶段接口中有明确位置，至少在 `start` 与 `complete` 事件中可用；前端不得自行推断。
- reset/cancel 必须能终止该 session 下未完成的文本流。

## Execution Strategy
### Parallel Execution Waves
Wave 0: dependency/runtime alignment (Task 0)

Wave 1: backend core extraction and contract (Tasks 1-4)

Wave 2: platform surfaces (Tasks 5-7)

Wave 3: product wiring & smoke coverage (Tasks 8-9)

### Dependency Matrix
| Task | Depends On |
|---|---|
| 0 | - |
| 1 | 0 |
| 2 | 1 |
| 3 | 1 |
| 4 | 2, 3 |
| 5 | 1, 3 |
| 6 | 1, 3 |
| 7 | 0, 2, 4 |
| 8 | 2, 4, 7 |
| 9 | 4, 5, 6, 7, 8 |
| F1-F4 | 0-9 |

### Agent Dispatch Summary
- Wave 0 → 1 task → unspecified-high
- Wave 1 → 4 tasks → unspecified-high / quick
- Wave 2 → 3 tasks → unspecified-high / quick / visual-engineering
- Wave 3 → 2 tasks → visual-engineering / unspecified-high
- Final Verification → 4 review passes

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [x] 0. Align backend dependencies and execution assumptions before implementation

  **What to do**: Update the plan and repo assumptions so execution starts from reality, not wishful thinking. Add Python web dependencies (`fastapi`, `uvicorn[standard]`) to the implementation scope, explicitly state that the existing `frontend/` app will be adapted rather than replaced, record that Live2D runtime internals are out of scope for this plan, and record that current streaming is POST-based SSE text only.
  **Must NOT do**: Do not introduce new product scope; do not reopen Live2D runtime selection; do not leave old docs as equally valid references; do not include audio in current-phase assumptions.

  **Parallelization**: Can Parallel: NO | Wave 0 | Blocks: [1, 4, 7, 8, 9] | Blocked By: []

  **References**:
  - `pyproject.toml:1-17`
  - `frontend/package.json:1-72`
  - `docs/plans/2026-04-01-live2d-chat-design.md:103-115`
  - `.sisyphus/plans/live2d-lead-web-ui.md`

  **Acceptance Criteria**:
  - [ ] Plan text explicitly states `frontend/` is adapted, not recreated.
  - [ ] Plan text explicitly treats Live2D as an integration prerequisite.
  - [ ] Python dependency additions required for FastAPI are identified before Task 4 starts.
  - [ ] Old design doc is marked non-authoritative for execution.
  - [ ] Current-phase streaming assumptions are POST-based SSE text only.

  **QA Scenarios**:
  ```
  Scenario: Execution assumptions are no longer contradictory
    Tool: Read
    Steps: Read the revised plan sections: TL;DR, Clarified Scope, Supersession, Task 0.
    Expected: No section still claims GET-based SSE or dual-stream SSE+WS for the current phase.
    Evidence: .sisyphus/evidence/task-0-plan-alignment.txt

  Scenario: Old design doc is no longer an implementation source
    Tool: Read
    Steps: Read the revised plan and verify the supersession note explicitly demotes `docs/plans/2026-04-01-live2d-chat-design.md`.
    Expected: The new plan names itself the single implementation source of truth.
    Evidence: .sisyphus/evidence/task-0-plan-alignment-error.txt
  ```

- [x] 1. Extract a reusable backend chat engine from the CLI loop

  **What to do**: Create `backend/core/chat_engine.py` that encapsulates one lead request/response cycle currently embedded in `main.py`. Preserve the existing ordering: deliver mail → prepare messages → invoke lead LLM → execute tool calls → run `team_cycle()` → append team responses → handle compact/reminder flags. Return a structured result object callable from both FastAPI and CLI wrappers.
  **Must NOT do**: Do not rewrite `TeamManager`; do not change mailbox semantics; do not change tool policy groupings; do not make the engine web-framework-specific.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [2, 3, 5, 6] | Blocked By: [0]

  **References**:
  - `main.py:48-131`
  - `graph/prepare_main_messages.py:9-39`
  - `graph/execute_tool_calls.py:14-36`
  - `team.py:56-147`
  - `team.py:612-626`
  - `tests/test_team_manager.py:10-192`

  **Acceptance Criteria**:
  - [ ] `backend/core/chat_engine.py` exposes a single-request execution API callable from FastAPI and CLI wrappers.
  - [ ] Existing `tests/test_team_manager.py` continues to pass unchanged.
  - [ ] New tests cover: plain assistant reply, assistant tool call path, `team_cycle()` summary injection.
  - [ ] No orchestration branch from the current CLI loop remains only in CLI code.

  **QA Scenarios**:
  ```
  Scenario: Engine returns a normal assistant turn
    Tool: Bash
    Steps: Run `uv run python -m unittest tests.test_chat_engine -v`
    Expected: Tests prove a single call produces assistant text and preserves tool/team ordering without starting the CLI loop.
    Evidence: .sisyphus/evidence/task-1-chat-engine.txt

  Scenario: Engine handles tool/team side effects deterministically
    Tool: Bash
    Steps: Run the tool-call + team-cycle cases in `tests.test_chat_engine`.
    Expected: Result object includes executed tool results and appended team summary; no duplicate execution occurs.
    Evidence: .sisyphus/evidence/task-1-chat-engine-error.txt
  ```

- [x] 2. Define the turn-level backend contract and canonical Live2D metadata mapper

  **What to do**: Create a schema module plus `backend/core/live2d_mapper.py` that defines request/response payloads, turn identifiers, SSE event payloads, and canonical assistant metadata. Hard-code V1 semantic states (`idle`, `thinking`, `speaking`, `reacting`) and emotions (`neutral`, `happy`, `sad`, `angry`). This task only defines the contract that the frontend message/avatar layers consume; it does not implement avatar runtime behavior.
  **Must NOT do**: Do not bind the canonical contract to old asset motion names; do not inspect React component state; do not leave metadata shape implicit; do not include audio frame metadata in the current-phase schema.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: [4, 7, 8, 9] | Blocked By: [1]

  **References**:
  - `main.py:75-87`
  - `graph/prepare_main_messages.py:29-39`
  - `graph/execute_tool_calls.py:17-35`
  - `frontend/src/pages/Home/Canvas.tsx:44-59` (anti-pattern only)
  - `https://ai-sdk.dev/docs/ai-sdk-ui/message-metadata`

  **Acceptance Criteria**:
  - [ ] A single schema module defines the exact backend turn-level contract used by FastAPI, POST-based SSE, and frontend transport.
  - [ ] `metadata.live2d` always contains all agreed keys, even in fallback cases.
  - [ ] Schema/mapper tests cover: default neutral response, explicit happy response, explicit sad/error response, tool-running/thinking response, and required turn identifiers.
  - [ ] Invalid/missing mapping outputs degrade safely without raising.

  **QA Scenarios**:
  ```
  Scenario: Contract produces stable metadata and turn identifiers
    Tool: Bash
    Steps: Run `uv run python -m unittest tests.test_live2d_mapper -v`
    Expected: Each canonical state returns deterministic metadata, and fixtures prove `assistant_message_id` / `turn_id` are present in stream payload contracts.
    Evidence: .sisyphus/evidence/task-2-live2d-mapper.txt

  Scenario: Unknown semantic input falls back safely
    Tool: Bash
    Steps: Run the fallback-path tests in `tests.test_live2d_mapper`.
    Expected: Output falls back to agreed defaults and no exception escapes.
    Evidence: .sisyphus/evidence/task-2-live2d-mapper-error.txt
  ```

- [x] 3. Implement JSON-backed single-session persistence with restore and reset semantics

  **What to do**: Create `backend/core/session_store.py` that persists the single active session to `.sessions/default.json`. Persist AI SDK-friendly messages, current `session_id`, and last known assistant metadata needed for page restore. Implement atomic writes, reset, load-on-start, and corruption recovery.
  **Must NOT do**: Do not store long-term memory in the session file; do not make the session store multi-user; do not keep session truth only in frontend local state.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: [4, 5, 6, 7, 9] | Blocked By: [1]

  **References**:
  - `graph/tools/todo_list.py:24-100`
  - `main.py:128-131`
  - `tests/test_team_manager.py:141-188`

  **Acceptance Criteria**:
  - [ ] `.sessions/default.json` is created lazily and rewritten atomically.
  - [ ] Load returns a valid empty session when the file is missing or malformed.
  - [ ] Reset clears only session history/state and leaves memory adapter state untouched.
  - [ ] Tests cover create/load/update/reset/corruption fallback.

  **QA Scenarios**:
  ```
  Scenario: Session survives restore and reset operations
    Tool: Bash
    Steps: Run `uv run python -m unittest tests.test_session_store -v`
    Expected: Tests prove save → load → reset flow preserves agreed semantics and JSON shape.
    Evidence: .sisyphus/evidence/task-3-session-store.txt

  Scenario: Corrupted JSON does not crash the app
    Tool: Bash
    Steps: Run the corruption cases in `tests.test_session_store`.
    Expected: Store returns an empty default session and rewrites a valid file on next save.
    Evidence: .sisyphus/evidence/task-3-session-store-error.txt
  ```

- [x] 4. Build the FastAPI application surface and POST-based SSE API contract

  **What to do**: Add required Python web dependencies, create `backend/main.py` and `backend/api/chat.py`, and implement exactly four HTTP routes: `GET /api/health`, `GET /api/session`, `POST /api/chat`, `POST /api/reset`. Mount repo-root `public/` under `/assets` and configure dev CORS for the Vite origin. `POST /api/chat` accepts the agreed request shape and directly returns a `text/event-stream` response that emits `start/delta/state/complete/error` events for the same assistant turn.
  **Must NOT do**: Do not expose raw `TeamManager` internals; do not let frontend-originated message arrays become canonical truth; do not use `GET /api/chat/stream`; do not add WebSocket/audio endpoints in the current phase.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [7, 8, 9] | Blocked By: [2, 3]

  **References**:
  - `pyproject.toml:1-17`
  - `main.py:48-131`
  - `frontend/package.json:12-51`
  - `https://ai-sdk.dev/docs/ai-sdk-ui/transport`

  **Acceptance Criteria**:
  - [ ] `backend.main:app` imports successfully and mounts `/api/*` plus `/assets/*`.
  - [ ] `GET /api/session` returns canonical JSON session data mapped to AI SDK-friendly messages.
  - [ ] `POST /api/chat` accepts the agreed request shape and returns a valid `text/event-stream` response.
  - [ ] `POST /api/chat` emits `start/delta/state/complete/error` events tied to the same assistant turn.
  - [ ] `POST /api/reset` clears the JSON session store and leaves mem0 untouched.

  **QA Scenarios**:
  ```
  Scenario: FastAPI endpoints return the agreed contract
    Tool: Bash
    Steps: Start `uv run python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`; then run `curl -s http://127.0.0.1:8000/api/health`, `curl -s http://127.0.0.1:8000/api/session`, and one `POST /api/chat` streaming smoke request.
    Expected: Health is healthy, session returns a valid object, and `POST /api/chat` returns standard `text/event-stream` data including `assistant_message_id` and `metadata.live2d`.
    Evidence: .sisyphus/evidence/task-4-fastapi-api.txt

  Scenario: Reset clears JSON state and terminates active text streams safely
    Tool: Bash
    Steps: After a successful chat call and active stream, issue `curl -s -X POST http://127.0.0.1:8000/api/reset` and fetch `/api/session` again.
    Expected: Session history is empty/default, active text streams terminate safely, and the backend remains ready for another turn.
    Evidence: .sisyphus/evidence/task-4-fastapi-api-error.txt
  ```

- [x] 5. Preserve a separate CLI debug entry that reuses the new backend core

  **What to do**: Refactor `main.py` so it becomes a thin CLI wrapper around the new backend core. Keep the current interactive `input()` experience and `q/exit/退出` handling, but isolate it from the primary web session by assigning `.sessions/cli-debug.json`.
  **Must NOT do**: Do not leave a second copy of the orchestration loop in `main.py`; do not let CLI and web share the same session file; do not remove the debug entrypoint.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [9] | Blocked By: [1, 3]

  **References**:
  - `main.py:56-135`
  - `main.py:128-131`
  - `backend/core/chat_engine.py`

  **Acceptance Criteria**:
  - [ ] `main.py` contains only wrapper logic plus debug-specific persistence/output behavior.
  - [ ] CLI uses a dedicated debug session path/ID and does not touch the main web session JSON file.
  - [ ] Existing team-manager tests remain green after the refactor.

  **QA Scenarios**:
  ```
  Scenario: CLI debug path still answers and exits cleanly
    Tool: Bash
    Steps: Run `printf "你好\nq\n" | uv run python main.py`
    Expected: CLI prints one assistant response, does not crash, and exits on `q`.
    Evidence: .sisyphus/evidence/task-5-cli-debug.txt

  Scenario: CLI does not overwrite the web session file
    Tool: Bash
    Steps: Seed the main session JSON, run the CLI smoke test, then inspect `.sessions/default.json` and `.sessions/cli-debug.json`.
    Expected: Only the CLI debug session artifact changes; the main web session file remains intact.
    Evidence: .sisyphus/evidence/task-5-cli-debug-error.txt
  ```

- [x] 6. Add a mem0 long-term memory adapter with explicit config gating and non-blocking fallback

  **What to do**: Create `backend/core/memory_adapter.py` that wraps `mem0` behind a narrow interface: `search_relevant_memories()` before a chat turn and `record_turn()` after a successful assistant reply. Gate activation behind explicit env checks and degrade safely when config is missing or mem0 raises.
  **Must NOT do**: Do not write full chat transcripts into mem0; do not make mem0 a hard startup dependency; do not call mem0 from the frontend.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [9] | Blocked By: [1, 3]

  **References**:
  - `pyproject.toml:7-17`
  - `main.py:15-21`
  - `https://docs.mem0.ai/open-source/python-quickstart`
  - `https://docs.mem0.ai/components/llms/models/deepseek`
  - `https://docs.mem0.ai/components/embedders/models/openai`

  **Acceptance Criteria**:
  - [ ] Adapter exposes explicit enabled/disabled state and never crashes the request path when misconfigured.
  - [ ] Retrieval is scoped to the single local user/session identity chosen by the backend.
  - [ ] Only condensed long-term facts are written; raw session JSON remains the restore source.
  - [ ] Tests cover enabled mode via mocks and disabled mode via missing env/config.

  **QA Scenarios**:
  ```
  Scenario: Memory adapter degrades cleanly when config is absent
    Tool: Bash
    Steps: Run `uv run python -m unittest tests.test_memory_adapter -v`
    Expected: Missing env vars cause a disabled adapter state, not a thrown startup/runtime error.
    Evidence: .sisyphus/evidence/task-6-memory-adapter.txt

  Scenario: Memory write/read failures do not block assistant response flow
    Tool: Bash
    Steps: Run the mocked failure-path cases in `tests.test_memory_adapter`.
    Expected: Adapter returns empty retrievals / warning states while the calling code continues successfully.
    Evidence: .sisyphus/evidence/task-6-memory-adapter-error.txt
  ```

- [x] 7. Adapt the existing frontend app for POST-based SSE transport and backend session sync

  **What to do**: Reuse the existing `frontend/` Vite/React app instead of creating a new one. Add transport and chat hook modules (for example `frontend/src/chat/LeadChatTransport.ts` and `frontend/src/chat/useLeadChat.ts`) so the browser starts turns via `POST /api/chat`, consumes assistant text via `@microsoft/fetch-event-source`, restores history from `GET /api/session`, and exposes reset via `POST /api/reset`.
  **Must NOT do**: Do not scaffold a second frontend app; do not make frontend local state the source of truth; do not assume native `EventSource`; do not add current-phase audio transport.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: [8, 9] | Blocked By: [0, 2, 4]

  **References**:
  - `frontend/package.json:12-51`
  - `frontend/src/pages/Home/HomeChatPanel.tsx:1-188`
  - `frontend/src/pages/Home/index.tsx`
  - `https://ai-sdk.dev/docs/ai-sdk-ui/chatbot`

  **Acceptance Criteria**:
  - [ ] `frontend/` builds successfully after transport integration.
  - [ ] `useLeadChat` restores existing history on page load and sends only the latest user message to the backend.
  - [ ] The transport converts `POST /api/chat` SSE events into AI SDK-compatible message updates without mutating backend-only fields.
  - [ ] The transport uses `@microsoft/fetch-event-source` or equivalent POST-based SSE client behavior.
  - [ ] Transport/hook tests cover normal parsing, malformed-response handling, and repeated SSE event deduplication.

  **QA Scenarios**:
  ```
  Scenario: Frontend transport builds and parses assistant text stream
    Tool: Bash
    Steps: In `frontend/`, run `npm install && npm run test -- --run && npm run build`
    Expected: Transport/hook tests pass, including POST-based SSE text assembly by `assistant_message_id`, and the Vite production build succeeds.
    Evidence: .sisyphus/evidence/task-7-frontend-transport.txt

  Scenario: Malformed backend payload or repeated event surfaces a controlled error state
    Tool: Bash
    Steps: Run the mocked malformed-response test in the frontend test suite.
    Expected: Hook enters an error path or deduplicates safely without corrupting existing message history.
    Evidence: .sisyphus/evidence/task-7-frontend-transport-error.txt
  ```

- [ ] 8. Compose the web chat shell and wire avatar/status updates through backend metadata

  **What to do**: Implement the browser UI composition (`AppShell`, `ChatPanel`, `MessageThread`, `StatusBadge`, page entry) on top of the existing `frontend/` app. Render AI SDK `messages[*].parts`, show ready/submitted/error states, add reset action, and feed the latest assistant `metadata.live2d` plus transient local `thinking` state into the existing avatar / Live2D integration boundary.
  **Must NOT do**: Do not parse assistant prose for sentiment; do not duplicate backend session persistence in local storage; do not let chat components depend on runtime-specific Pixi details; do not introduce audio UI in the current phase.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: [9] | Blocked By: [2, 4, 7]

  **References**:
  - `frontend/src/pages/Home/HomeChatPanel.tsx:1-188`
  - `frontend/src/pages/Home/Canvas.tsx:1-80` (integration boundary reference only)
  - `https://ai-sdk.dev/docs/ai-sdk-ui/message-metadata`

  **Acceptance Criteria**:
  - [ ] Browser UI restores prior messages from the backend session on load.
  - [ ] User send/reset flows work end-to-end with the agreed POST-based SSE contract.
  - [ ] Avatar / Live2D integration receives only backend metadata + temporary local waiting state and never raw sentiment inference logic.
  - [ ] Frontend build and component tests pass.

  **QA Scenarios**:
  ```
  Scenario: Chat shell renders restored messages and streamed text on one assistant turn
    Tool: Bash
    Steps: In `frontend/`, run `npm run test -- --run && npm run build`
    Expected: Tests confirm message rendering/reset wiring, streamed text assembly by `assistant_message_id`, and the build succeeds.
    Evidence: .sisyphus/evidence/task-8-chat-shell.txt

  Scenario: UI handles text-stream failure without corrupting history
    Tool: Bash
    Steps: Run the component/hook error-path tests with a mocked failed `POST /api/chat` SSE response.
    Expected: Existing messages remain intact, text-stream failure is represented explicitly, and no frontend-side emotion fallback is invented.
    Evidence: .sisyphus/evidence/task-8-chat-shell-error.txt
  ```

- [ ] 9. Add integrated smoke coverage, env contracts, and local run instructions

  **What to do**: Add end-to-end smoke coverage for the new stack, a root `.env.example`, and minimal run instructions in `README.md`. Document all required env vars (`DEEPSEEK_API_KEY`, optional `OPENAI_API_KEY`, `MEM0_ENABLED`, any frontend API base override if used), reset semantics, POST-based SSE text flow, and the fact that avatar / Live2D runtime capability is treated as a frontend integration prerequisite in this plan.
  **Must NOT do**: Do not leak secrets into docs; do not make mem0 mandatory in `.env.example`; do not leave startup procedure discoverable only from code; do not document audio as a current-phase behavior.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: [F1-F4] | Blocked By: [4, 5, 6, 7, 8]

  **References**:
  - `README.md:1-1`
  - `pyproject.toml:1-17`
  - `main.py:15-21`

  **Acceptance Criteria**:
  - [ ] Root `.env.example` exists and lists all required/optional variables without secrets.
  - [ ] `README.md` explains backend/frontend startup, reset semantics, mem0 fallback behavior, POST-based SSE reply flow, and frontend avatar integration assumptions.
  - [ ] Full backend test suite, frontend test/build, and SSE smoke checks pass together.
  - [ ] Smoke coverage proves chat remains functional even if avatar runtime is unavailable.

  **QA Scenarios**:
  ```
  Scenario: Full local stack smoke passes from clean checkout instructions
    Tool: Bash
    Steps: Run `uv run python -m unittest discover tests -v`; in `frontend/` run `npm install && npm run test -- --run && npm run build`; then start FastAPI and exercise `/api/health`, `/api/session`, `POST /api/chat` SSE text flow, and `/api/reset`.
    Expected: All checks pass, README instructions are sufficient, and each route/stream behaves as documented.
    Evidence: .sisyphus/evidence/task-9-stack-smoke.txt

  Scenario: Avatar runtime is unavailable but chat remains functional
    Tool: Bash
    Steps: Disable or mock the avatar integration entry, run the frontend/build smoke plus one `POST /api/chat` SSE request.
    Expected: UI falls back to non-blocking chat mode while text reply flow and session endpoints still succeed.
    Evidence: .sisyphus/evidence/task-9-stack-smoke-error.txt
  ```

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.

- [ ] F1. Plan Compliance Audit

  **QA Scenario**:
  ```
  Tool: Read + Bash
  Steps: Re-read this plan and create a checklist of Tasks 0-9 acceptance criteria; then run the exact verification commands referenced by each completed task.
  Expected: Every task has matching evidence, and no completed task lacks its declared QA proof.
  Evidence: .sisyphus/evidence/f1-plan-compliance.txt
  ```

- [ ] F2. Code Quality Review

  **QA Scenario**:
  ```
  Tool: Read + Bash
  Steps: Review all changed files; run `uv run python -m unittest discover tests -v`; in `frontend/` run `npm run test -- --run && npm run build`.
  Expected: No plan-induced regressions, no unverified changed area, and no failing backend/frontend checks.
  Evidence: .sisyphus/evidence/f2-code-quality.txt
  ```

- [ ] F3. Real Manual QA / API Smoke

  **QA Scenario**:
  ```
  Tool: Bash
  Steps: Start the backend, exercise `/api/health`, `/api/session`, `POST /api/chat` SSE text flow, `/api/reset`, then run the frontend locally against that backend and verify restore/send/reset/error-state behavior.
  Expected: End-to-end behavior matches the plan, SSE text flow works, and temporary frontend loading state never turns into frontend emotion inference.
  Evidence: .sisyphus/evidence/f3-manual-qa.txt
  ```

- [ ] F4. Scope Fidelity Check

  **QA Scenario**:
  ```
  Tool: Read
  Steps: Compare final changes against Must Have / Must NOT Have / Clarified Scope sections of this plan.
  Expected: No multi-user scope, no audio/WS scope creep, no frontend emotion inference, no Live2D runtime rewrite hidden inside implementation.
  Evidence: .sisyphus/evidence/f4-scope-fidelity.txt
  ```

## Commit Strategy
- Prefer one commit per implementation task once its tests/build checks pass.
- Keep backend extraction, API surface, frontend transport, chat shell wiring, and smoke/docs in separate commits to simplify rollback.
- Never mix mem0 fallback work with unrelated UI composition changes.

## Deferred Work
- Audio/TTS streaming is deferred to a later phase.
- If audio is reintroduced later, design it as an additive extension on top of the existing `assistant_message_id`, not as a blocker for the current text-streaming path.

## Success Criteria
- Web UI becomes the primary usable entry for lead interactions.
- Python harness behavior remains intact and reachable from CLI debug mode.
- Every assistant turn returned to the browser includes deterministic `metadata.live2d`, server-assigned identifiers, and POST-based SSE text-stream behavior.
- Session restore/reset semantics match the agreed contract.
- mem0 augments context when configured and silently degrades when unavailable.
- Frontend avatar / Live2D layer can consume backend metadata without frontend-side emotion inference.
- Avatar runtime 不可用时，聊天主流程仍然可用。
