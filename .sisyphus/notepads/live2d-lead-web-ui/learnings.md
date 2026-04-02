# Learnings: live2d-lead-web-ui

## 2026-04-02

### Backend Dependencies Alignment

**What was aligned:**
- Added explicit `uvicorn[standard]>=0.35.0` dependency to `pyproject.toml`
- `fastapi[standard]>=0.135.3` was already present but does NOT include uvicorn as a dependency

**Why this matters:**
- FastAPI only declares uvicorn as an optional dependency; without `uvicorn[standard]`, uvicorn is not installed
- Running the FastAPI app with `uvicorn` requires uvicorn to be installed
- Using `[standard]` extras ensures full stack including reload, h11, httptools, watchfiles, etc.

**Files modified:**
- `pyproject.toml`: added `uvicorn[standard]>=0.35.0` to dependencies array

**Unblocked tasks:** Tasks 1, 4, 7, 8, 9

### Backend Chat Engine Extraction

**What was extracted:**
- Added backend/core/chat_engine.py with LeadTurnResult and execute_lead_turn(...) for one complete lead turn
- Added backend/core/__init__.py to export the reusable backend interface

**Behavior preserved:**
- Per-turn orchestration keeps the CLI ordering: deliver_mail -> prepare_main_messages -> lead LLM invoke -> execute_tool_calls -> team_cycle() -> append <team_cycle> summary -> compact/reminder handling
- Tool calls are aggregated in the result, and teammate responses remain appended back into the lead message list as a synthetic HumanMessage

**Restore detail:**
- session_messages accepts live LangChain messages plus serialized message dicts, including to_json() payloads restored via langchain_core.load.load
- Reminder state is inferred from prior assistant tool-call turns so the todo nag logic can continue across restored sessions without changing mailbox semantics

**Verification:**
- from backend.core.chat_engine import execute_lead_turn imports successfully
- LSP diagnostics are clean for backend/core/chat_engine.py and backend/core/__init__.py

### SessionStore JSON Persistence

**What was added:**
- Added `backend/core/session_store.py` with `SessionData` + `SessionStore` for the canonical single-session JSON store at `.sessions/default.json`
- Updated `backend/core/__init__.py` exports so backend code can import the store from the shared core package

**Persistence semantics:**
- `load()` always returns the canonical shape: `session_id`, `messages`, `metadata`
- `save()` writes UTF-8 JSON through a same-directory temp file and swaps it into place with `os.replace(...)`
- `reset()` removes the persisted session file so the next load falls back to a fresh default session
- JSON parse corruption triggers backup rotation to `default.json.bak-<UTC timestamp>` before returning a fresh default session

**Why this matters:**
- Backend remains the single source of truth for conversation state across browser refreshes
- Atomic replace avoids partial writes leaving the main session file half-written on crashes/interruption

### Turn-Level Live2D Contract

**What was added:**
- Added `backend/core/schema.py` with explicit Pydantic request/SSE models and a `TurnResult` dataclass carrying the backend-assigned `assistant_message_id`
- Added `backend/core/live2d_mapper.py` with a canonical `metadata.live2d` mapper driven by tool-call presence, response sentiment, and error keywords

**Contract choices:**
- Request/event models use `extra="forbid"` so the backend metadata shape stays explicit and framework-agnostic
- Live2D states are canonicalized to `idle|thinking|speaking|reacting`, emotions to `neutral|happy|sad|angry`, and motion names stay generic (`idle01`, `thinking01`, `smile03`, `sad01`, `angry03`)

**Verification:**
- `uv run python -c "from backend.core.schema import *; from backend.core.live2d_mapper import *; print('imports ok')"` prints `imports ok`
- LSP diagnostics are clean for `backend/core/schema.py`, `backend/core/live2d_mapper.py`, and `backend/core/__init__.py`

### FastAPI POST-SSE Surface

**What was added:**
- Added `backend/main.py` with FastAPI app title `Live2D Lead Chat API`, `/api` router wiring, Vite-localhost CORS, and `/assets` static mount backed by repo-root `public/`
- Added `backend/api/chat.py` with `GET /health`, `GET /session`, `POST /chat`, and `POST /reset`

**Contract choices:**
- `POST /chat` keeps the backend session store as canonical truth, while `metadata.ui_messages` stores backend-derived AI SDK-friendly `user|assistant` messages for browser restoration
- SSE framing uses standard `event:` + `data:` lines via `StreamingResponse`, emitting `start`, `state`, per-segment `delta`, `complete`, and `error`
- `GET /session` filters system / reminder / team-cycle internal messages before returning browser-facing chat history

**Verification:**
- `uv run python -c "from backend.main import app; print(app.title)"` prints `Live2D Lead Chat API`
- LSP diagnostics are clean for `backend/api/chat.py`, `backend/api/__init__.py`, and `backend/main.py`

### Optional mem0 Memory Adapter

**What was added:**
- Added `backend/core/memory_adapter.py` with `MemoryAdapter.is_enabled()`, `search_relevant_memories()`, and `record_turn()`
- Updated `backend/core/__init__.py` to export `MemoryAdapter`
- Added `tests/test_memory_adapter.py` for disabled, enabled, and failure-path coverage

**Fallback semantics:**
- Adapter only attempts initialization when `MEM0_ENABLED=true` and `DEEPSEEK_API_KEY` is present; failed init stays disabled for the process lifetime
- Retrieval returns `[]` and writes are silent on any mem0 exception so chat request paths remain non-blocking
- `record_turn()` writes a condensed summary string plus metadata instead of a raw full-turn transcript

**Implementation note:**
- The installed `mem0ai` package exposes the runtime module as `mem0`; the adapter uses OSS-style `Memory.from_config(...)` when available and falls back safely if mem0 cannot initialize (for example missing embedder credentials)

**Verification:**
- `uv run python -m unittest tests.test_memory_adapter -v` passes
- `uv run python -c "from backend.core.memory_adapter import MemoryAdapter; print('import ok')"` prints `import ok`

### CLI Debug Wrapper Reuse

**What changed:**
- Refactored `main.py` into a thin interactive wrapper that calls `backend.core.chat_engine.execute_lead_turn(...)` instead of keeping a second orchestration loop in CLI code
- Added a dedicated CLI `SessionStore(session_file=Path(".sessions/cli-debug.json"))` so debug sessions stay isolated from the web-backed `.sessions/default.json`

**Wrapper behavior kept:**
- The CLI still uses `input("请输入你的问题：")` and exits on `q` / `exit` / `退出`
- Each turn still writes `output.json`, but the saved conversation now comes from the backend-core result messages serialized via `to_json()`

**Verification:**
- `uv run python -m unittest tests.test_main_cli -v` passes for the wrapper/session-store path
- `uv run python -m unittest tests.test_team_manager -v` stays green after the refactor
- `uv run python -c "from main import loop; print('main.py import ok')"` prints `main.py import ok`
