from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal

from langchain_core.messages import AnyMessage
from pydantic import BaseModel, ConfigDict

Live2DState = Literal["idle", "thinking", "speaking", "reacting"]
Live2DEmotion = Literal["neutral", "happy", "sad", "angry"]


class StrictModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")


class ChatMessage(StrictModel):
    id: str
    text: str


class ChatRequest(StrictModel):
    session_id: str
    message: ChatMessage
    trigger: str


class Live2DMeta(StrictModel):
    state: Live2DState
    emotion: Live2DEmotion
    motion: str
    expression: str


class SSEMetadata(StrictModel):
    live2d: Live2DMeta


class SSEStartEvent(StrictModel):
    session_id: str
    assistant_message_id: str
    metadata: SSEMetadata


class SSEDeltaEvent(StrictModel):
    assistant_message_id: str
    sequence: int
    text: str


class SSECompleteEvent(StrictModel):
    assistant_message_id: str
    finish_reason: str
    message: dict[str, object]


class SSEErrorEvent(StrictModel):
    error: str


@dataclass(slots=True)
class TurnResult:
    assistant_text: str
    tool_calls: list[dict[str, object]]
    team_responses: dict[str, AnyMessage]
    needs_compact: bool
    messages: list[AnyMessage]
    assistant_message_id: str


__all__ = [
    "ChatMessage",
    "ChatRequest",
    "Live2DEmotion",
    "Live2DMeta",
    "Live2DState",
    "SSECompleteEvent",
    "SSEDeltaEvent",
    "SSEErrorEvent",
    "SSEMetadata",
    "SSEStartEvent",
    "TurnResult",
]
