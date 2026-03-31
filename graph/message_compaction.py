import json
import time
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage


def micro_compact(messages: list[Any], keep_recent: int = 3) -> list[Any]:
    """把超过 keep_recent 的 ToolMessage 替换为占位符。"""
    tool_name_map = {}
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tool_call in msg.tool_calls:
                if isinstance(tool_call, dict):
                    tool_call_id = tool_call.get("id")
                    tool_name = tool_call.get("name", "unknown")
                else:
                    tool_call_id = getattr(tool_call, "id", None)
                    tool_name = getattr(tool_call, "name", "unknown")

                if tool_call_id:
                    tool_name_map[tool_call_id] = tool_name

    tool_messages = [
        (index, msg)
        for index, msg in enumerate(messages)
        if isinstance(msg, ToolMessage)
    ]

    if len(tool_messages) <= keep_recent:
        return messages

    for _, msg in tool_messages[:-keep_recent]:
        if isinstance(msg.content, str) and len(msg.content) > 100:
            tool_name = tool_name_map.get(msg.tool_call_id, "unknown")
            msg.content = f"[Previous: used {tool_name}]"

    return messages


def estimate_tokens(messages: list[Any]) -> int:
    return len(str(messages)) // 4


def auto_compact(
    messages: list[Any],
    llm: Any,
    system_prompt: str,
    transcript_dir: Path,
) -> list[Any]:
    """
    token 超阈值时自动压缩。
    1. 保存完整对话到磁盘
    2. 让 LLM 总结对话
    3. 用总结替换 messages
    """
    transcript_dir.mkdir(exist_ok=True)
    timestamp = int(time.time())
    transcript_path = transcript_dir / f"transcript_{timestamp}.jsonl"
    with open(transcript_path, "w", encoding="utf-8") as file:
        for msg in messages:
            file.write(json.dumps(msg.to_json(), ensure_ascii=False) + "\n")
    print(f"[auto_compact] 对话已保存到: {transcript_path}")

    messages_str = json.dumps([msg.to_json() for msg in messages], ensure_ascii=False)
    messages_str = messages_str[:80000]

    summary_response = llm.invoke(
        [
            HumanMessage(
                content=(
                    "请总结以下对话，保留关键信息以便继续工作。"
                    "包括：1) 已完成什么 2) 当前状态 3) 关键决策。\n\n"
                    f"{messages_str}"
                )
            )
        ]
    )
    summary = summary_response.content

    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"[对话已压缩] {summary}"),
        AIMessage(content="明白，我了解了之前的对话内容，继续工作。"),
    ]
