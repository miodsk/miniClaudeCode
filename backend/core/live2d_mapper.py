from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import cast

from backend.core.chat_engine import LeadTurnResult
from backend.core.schema import Live2DEmotion, Live2DMeta, Live2DState

_STATE_TO_MOTION: dict[Live2DState, str] = {
    "idle": "idle01",
    "thinking": "thinking01",
    "speaking": "smile03",
    "reacting": "angry03",
}

_EMOTION_TO_EXPRESSION: dict[Live2DEmotion, str] = {
    "neutral": "neutral",
    "happy": "happy",
    "sad": "sad",
    "angry": "angry",
}

_POSITIVE_KEYWORDS = (
    "great",
    "glad",
    "happy",
    "thanks",
    "success",
    "completed",
    "done",
    "太棒",
    "很好",
    "开心",
    "高兴",
    "成功",
    "完成",
)

_NEGATIVE_KEYWORDS = (
    "sorry",
    "unfortunately",
    "regret",
    "sad",
    "unable",
    "cannot",
    "can't",
    "抱歉",
    "遗憾",
    "难过",
    "无法",
    "不能",
)

_ERROR_KEYWORDS = (
    "error",
    "exception",
    "traceback",
    "failed",
    "failure",
    "错误",
    "异常",
    "失败",
)


def _message_texts(response: LeadTurnResult) -> Iterable[str]:
    yield response.assistant_text
    for team_response in response.team_responses.values():
        content: object = getattr(team_response, "content", "")
        if isinstance(content, str):
            yield content
        elif isinstance(content, list):
            text_parts: list[str] = []
            for part in cast(list[object], content):
                if isinstance(part, str):
                    text_parts.append(part)
                elif isinstance(part, Mapping):
                    part_mapping = cast(Mapping[str, object], part)
                    part_type = part_mapping.get("type")
                    if part_type == "text":
                        text_value = part_mapping.get("text", "")
                        text_parts.append(str(text_value))
            if text_parts:
                yield "".join(text_parts)


def _contains_keyword(response: LeadTurnResult, keywords: tuple[str, ...]) -> bool:
    haystack = "\n".join(text.lower() for text in _message_texts(response) if text)
    return any(keyword.lower() in haystack for keyword in keywords)


def map_response_to_live2d(response: LeadTurnResult) -> Live2DMeta:
    state: Live2DState = "idle"
    emotion: Live2DEmotion = "neutral"

    if _contains_keyword(response, _ERROR_KEYWORDS):
        state = "reacting"
        emotion = "angry"
    elif response.tool_calls:
        state = "thinking"
        emotion = "neutral"
    else:
        if response.assistant_text.strip():
            state = "speaking"

        if _contains_keyword(response, _POSITIVE_KEYWORDS):
            emotion = "happy"
        elif _contains_keyword(response, _NEGATIVE_KEYWORDS):
            emotion = "sad"

    motion = _STATE_TO_MOTION[state]
    if emotion == "sad":
        motion = "sad01"

    return Live2DMeta(
        state=state,
        emotion=emotion,
        motion=motion,
        expression=_EMOTION_TO_EXPRESSION[emotion],
    )


__all__ = ["map_response_to_live2d"]
