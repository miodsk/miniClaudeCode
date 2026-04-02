from __future__ import annotations

# pyright: reportAny=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false

import asyncio
import json
import re
import uuid
from collections.abc import AsyncIterator, Iterable
from typing import cast

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.load import load
from langchain_core.messages import AnyMessage
from langchain_core.messages import messages_from_dict

from backend.core.chat_engine import execute_lead_turn
from backend.core.live2d_mapper import map_response_to_live2d
from backend.core.schema import (
    ChatRequest,
    Live2DMeta,
    SSECompleteEvent,
    SSEDeltaEvent,
    SSEErrorEvent,
    SSEMetadata,
    SSEStartEvent,
)
from backend.core.session_store import SessionPayload, SessionStore

router = APIRouter()
api_router = router

_DEFAULT_SESSION_ID = "sess_default"
_TEXT_SEGMENT_PATTERN = re.compile(r"\S+\s*")
_SPECIAL_HUMAN_PREFIXES = ("<team_cycle>", "<reminder>")


def _coerce_message(message: object) -> AnyMessage:
    if hasattr(message, "type") and hasattr(message, "content"):
        return cast(AnyMessage, message)

    if not isinstance(message, dict):
        raise ValueError(f"Unsupported session message format: {message}")

    if "lc" in message:
        return cast(AnyMessage, load(message))

    if "type" in message and "data" in message:
        return cast(AnyMessage, messages_from_dict([message])[0])

    message_type = message.get("type")
    data = {key: value for key, value in message.items() if key != "type"}
    if message_type in {"human", "ai", "system", "chat", "function", "tool"}:
        return cast(
            AnyMessage,
            messages_from_dict([{"type": message_type, "data": data}])[0],
        )

    raise ValueError(f"Unsupported session message format: {message}")


def _extract_text(content: object) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict) and part.get("type") == "text":
                text_parts.append(str(part.get("text", "")))
        return "".join(text_parts)

    return "" if content is None else str(content)


def _to_ui_message(
    message_id: str, role: str, text: str, **extra: object
) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": message_id,
        "role": role,
        "content": text,
        "parts": [{"type": "text", "text": text}],
    }
    payload.update(extra)
    return payload


def _is_valid_ui_message_list(messages: object) -> bool:
    return isinstance(messages, list) and all(
        isinstance(message, dict) for message in messages
    )


def _derive_ui_messages(
    serialized_messages: Iterable[object],
) -> list[dict[str, object]]:
    ui_messages: list[dict[str, object]] = []
    user_index = 0
    assistant_index = 0

    for serialized in serialized_messages:
        message = _coerce_message(serialized)
        message_type = getattr(message, "type", "")
        text = _extract_text(getattr(message, "content", "")).strip()

        if not text:
            continue

        if message_type == "human":
            if any(text.startswith(prefix) for prefix in _SPECIAL_HUMAN_PREFIXES):
                continue
            user_index += 1
            ui_messages.append(_to_ui_message(f"user-{user_index}", "user", text))
            continue

        if message_type == "ai":
            assistant_index += 1
            ui_messages.append(
                _to_ui_message(f"assistant-{assistant_index}", "assistant", text)
            )

    return ui_messages


def _resolve_session_id(request_session_id: str, session: SessionPayload) -> str:
    stored_session_id = session.get("session_id")
    if (
        isinstance(stored_session_id, str)
        and stored_session_id
        and stored_session_id != _DEFAULT_SESSION_ID
    ):
        return stored_session_id

    if request_session_id:
        return request_session_id

    return _DEFAULT_SESSION_ID


def _serialize_messages(messages: Iterable[object]) -> list[dict[str, object]]:
    serialized_messages: list[dict[str, object]] = []
    for message in messages:
        if hasattr(message, "to_json"):
            serialized_messages.append(cast(dict[str, object], message.to_json()))
        elif isinstance(message, dict):
            serialized_messages.append(dict(message))
        else:
            raise ValueError(f"Message is not serializable: {message}")
    return serialized_messages


def _split_text_segments(text: str) -> list[str]:
    segments = [match.group(0) for match in _TEXT_SEGMENT_PATTERN.finditer(text)]
    if segments:
        return segments
    return [text] if text else []


def _sse_event(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _build_complete_message(
    *,
    assistant_message_id: str,
    assistant_text: str,
    live2d: Live2DMeta,
) -> dict[str, object]:
    return _to_ui_message(
        assistant_message_id,
        "assistant",
        assistant_text,
        metadata={"live2d": live2d.model_dump()},
    )


def _get_session_response(session: SessionPayload) -> dict[str, object]:
    metadata = dict(cast(dict[str, object], session.get("metadata", {})))
    ui_messages = metadata.get("ui_messages")
    if not _is_valid_ui_message_list(ui_messages):
        ui_messages = _derive_ui_messages(
            cast(list[object], session.get("messages", []))
        )
        metadata["ui_messages"] = ui_messages

    return {
        "session_id": _resolve_session_id(
            str(session.get("session_id", _DEFAULT_SESSION_ID)), session
        ),
        "messages": cast(list[dict[str, object]], ui_messages),
        "metadata": metadata,
    }


async def _stream_chat_events(
    *,
    session_id: str,
    assistant_message_id: str,
    assistant_text: str,
    live2d: Live2DMeta,
) -> AsyncIterator[str]:
    start_event = SSEStartEvent(
        session_id=session_id,
        assistant_message_id=assistant_message_id,
        metadata=SSEMetadata(live2d=live2d),
    )
    yield _sse_event("start", start_event.model_dump())

    yield _sse_event(
        "state",
        {
            "assistant_message_id": assistant_message_id,
            "metadata": {"live2d": live2d.model_dump()},
        },
    )

    for sequence, segment in enumerate(_split_text_segments(assistant_text), start=1):
        delta_event = SSEDeltaEvent(
            assistant_message_id=assistant_message_id,
            sequence=sequence,
            text=segment,
        )
        yield _sse_event("delta", delta_event.model_dump())
        await asyncio.sleep(0)

    complete_event = SSECompleteEvent(
        assistant_message_id=assistant_message_id,
        finish_reason="stop",
        message=_build_complete_message(
            assistant_message_id=assistant_message_id,
            assistant_text=assistant_text,
            live2d=live2d,
        ),
    )
    yield _sse_event("complete", complete_event.model_dump())


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/session")
async def get_session() -> dict[str, object]:
    return _get_session_response(SessionStore().load())


@router.post("/reset")
async def reset_session() -> dict[str, str]:
    SessionStore().reset()
    return {"status": "reset"}


@router.post("/chat")
async def post_chat(request: ChatRequest) -> StreamingResponse:
    store = SessionStore()
    session = store.load()
    session_id = _resolve_session_id(request.session_id, session)
    assistant_message_id = str(uuid.uuid4())

    try:
        result = execute_lead_turn(
            user_message=request.message.text,
            session_id=session_id,
            session_messages=cast(list[object], session.get("messages", [])),
        )
        live2d = map_response_to_live2d(result)

        serialized_messages = _serialize_messages(result.messages)
        metadata = dict(cast(dict[str, object], session.get("metadata", {})))
        existing_ui_messages = metadata.get("ui_messages")
        if _is_valid_ui_message_list(existing_ui_messages):
            ui_messages = [
                dict(message)
                for message in cast(list[dict[str, object]], existing_ui_messages)
            ]
        else:
            ui_messages = _derive_ui_messages(
                cast(list[object], session.get("messages", []))
            )

        ui_messages.append(
            _to_ui_message(request.message.id, "user", request.message.text)
        )
        ui_messages.append(
            _build_complete_message(
                assistant_message_id=assistant_message_id,
                assistant_text=result.assistant_text,
                live2d=live2d,
            )
        )

        metadata["ui_messages"] = ui_messages
        metadata["last_live2d"] = live2d.model_dump()
        metadata["last_trigger"] = request.trigger

        store.save(
            {
                "session_id": session_id,
                "messages": serialized_messages,
                "metadata": metadata,
            }
        )

        event_stream = _stream_chat_events(
            session_id=session_id,
            assistant_message_id=assistant_message_id,
            assistant_text=result.assistant_text,
            live2d=live2d,
        )
    except Exception as exc:
        error_message = str(exc)

        async def error_stream() -> AsyncIterator[str]:
            error_event = SSEErrorEvent(error=error_message)
            yield _sse_event("error", error_event.model_dump())

        event_stream = error_stream()

    return StreamingResponse(
        event_stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


__all__ = ["api_router", "router"]
