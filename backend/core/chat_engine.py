from __future__ import annotations

# pyright: reportAny=false, reportExplicitAny=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false

import os
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from dotenv import load_dotenv
from langchain_core.load import load
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langchain_core.messages import messages_from_dict
from langchain_deepseek import ChatDeepSeek
from pydantic import SecretStr

from graph.execute_tool_calls import TODO_TOOL_NAMES, execute_tool_calls
from graph.message_compaction import auto_compact
from graph.prepare_main_messages import prepare_main_messages
from graph.tool_policy import get_static_tools_for_agent
from graph.tools.background_task import BG_MANAGER
from graph.tools.load_skill import SKILL_LOADER
from team import TeamManager

_ = load_dotenv()

KEEP_RECENT = 3
THRESHOLD = 50000
TRANSCRIPT_DIR = Path(".transcripts")

DEFAULT_LEAD_SYSTEM_PROMPT = f"""你是团队负责人 lead，负责理解用户需求、拆解任务、必要时委派给 researcher 或 coder，并基于队友结果给出最终答复。

工作规则：
1. 你直接面对用户，最终答复由你给出。
2. 做多步任务时，先用 task_create、task_update、task_list、task_get 管理计划和状态。
3. 当任务需要调研、阅读文件、查找信息时，优先考虑委派给 researcher。
4. 当任务需要改文件、落地实现或执行后台命令时，优先考虑委派给 coder。
5. 委派时要写清楚目标、范围和期望输出。
6. 只有在收到 researcher 或 coder 的回报后，才能把其结果当作已完成事实使用。
7. 如果任务不需要委派，你也可以自己直接完成。
8. 遇到不熟悉的领域时，先用 load_skill 工具加载相关技能知识。
9. 遇到耗时命令时，优先使用 background_run；需要时用 background_check 查看状态。
10. 当需要委派给 researcher 或 coder 时，使用 send_message 发送清晰的子任务。
11. 如需让某位队友优雅停止工作，使用 request_shutdown 发起请求，等待其明确响应。
12. 如果 coder 提交了 merge_request，审查后使用 respond_merge_request 给出批准或拒绝。
13. 如需查看当前未读团队邮件摘要，可使用 check_mail。

可用技能:
{SKILL_LOADER.get_descriptions()}"""


@dataclass(slots=True)
class LeadTurnResult:
    assistant_text: str
    tool_calls: list[dict[str, Any]]
    team_responses: dict[str, AnyMessage]
    needs_compact: bool
    messages: list[AnyMessage]


@lru_cache(maxsize=1)
def get_default_lead_llm() -> ChatDeepSeek:
    return ChatDeepSeek(
        model="deepseek-chat",
        api_key=SecretStr(os.getenv("DEEPSEEK_API_KEY") or ""),
        temperature=0.2,
    )


def _coerce_message(message: object) -> AnyMessage:
    if isinstance(message, (HumanMessage, SystemMessage)):
        return message

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
            AnyMessage, messages_from_dict([{"type": message_type, "data": data}])[0]
        )

    raise ValueError(f"Unsupported session message format: {message}")


def _restore_messages(
    session_messages: Sequence[object] | None,
    lead_system_prompt: str,
) -> list[AnyMessage]:
    if not session_messages:
        return [SystemMessage(content=lead_system_prompt)]

    restored_messages = [_coerce_message(message) for message in session_messages]
    if not restored_messages or not isinstance(restored_messages[0], SystemMessage):
        restored_messages.insert(0, SystemMessage(content=lead_system_prompt))
    return restored_messages


def _extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_chunks: list[str] = []
        for chunk in content:
            if isinstance(chunk, str):
                text_chunks.append(chunk)
                continue

            if isinstance(chunk, dict) and chunk.get("type") == "text":
                text_chunks.append(str(chunk.get("text", "")))

        return "".join(text_chunks)

    return "" if content is None else str(content)


def _infer_rounds_since_todo(messages: Sequence[AnyMessage]) -> int:
    rounds_since_todo = 0

    for message in reversed(messages):
        if isinstance(message, HumanMessage) and isinstance(message.content, str):
            if "<reminder>请更新你的 todo 列表</reminder>" in message.content:
                break

        tool_calls = getattr(message, "tool_calls", None) or []
        if not tool_calls:
            continue

        if any(tool_call.get("name") in TODO_TOOL_NAMES for tool_call in tool_calls):
            break

        rounds_since_todo += 1

    return rounds_since_todo


def execute_lead_turn(
    user_message: str,
    session_id: str,
    session_messages: Sequence[object] | None = None,
    *,
    llm: Any | None = None,
    lead_system_prompt: str = DEFAULT_LEAD_SYSTEM_PROMPT,
    threshold: int = THRESHOLD,
    transcript_dir: Path = TRANSCRIPT_DIR,
    keep_recent: int = KEEP_RECENT,
    bg_manager: Any = BG_MANAGER,
) -> LeadTurnResult:
    _ = session_id

    base_llm = llm or get_default_lead_llm()
    team = TeamManager(lead_system_prompt=lead_system_prompt)
    team.agents["lead"].messages = _restore_messages(
        session_messages, lead_system_prompt
    )
    messages = team.agents["lead"].messages
    lead_tools = get_static_tools_for_agent("lead") + team.get_agent_tools("lead")
    lead_tools_map = {tool.name: tool for tool in lead_tools}
    lead_llm = base_llm.bind_tools(lead_tools)
    rounds_since_todo = _infer_rounds_since_todo(messages)
    collected_tool_calls: list[dict[str, Any]] = []
    collected_team_responses: dict[str, AnyMessage] = {}
    assistant_text = ""
    needs_compact = False

    team.submit_user_task(user_message)

    while True:
        team.deliver_mail("lead")

        prepare_main_messages(
            messages=messages,
            llm=base_llm,
            system_prompt=lead_system_prompt,
            threshold=threshold,
            transcript_dir=transcript_dir,
            keep_recent=keep_recent,
            bg_manager=bg_manager,
        )

        response = lead_llm.invoke(input=messages)
        messages.append(response)
        assistant_text = _extract_text_content(getattr(response, "content", ""))

        tool_calls = list(getattr(response, "tool_calls", None) or [])
        if not tool_calls:
            break

        collected_tool_calls.extend(tool_calls)

        state = execute_tool_calls(response, messages, lead_tools_map)
        used_todo = state["used_todo"]
        requested_compact = state["need_compact"]

        team_responses = team.team_cycle(base_llm)
        if team_responses:
            collected_team_responses.update(team_responses)
            lines: list[str] = []
            for agent_name, agent_response in team_responses.items():
                content = (
                    agent_response.content
                    if getattr(agent_response, "content", None)
                    else "(无内容)"
                )
                lines.append(f"[{agent_name}] {content}")
            messages.append(
                HumanMessage(
                    content="<team_cycle>\n" + "\n\n".join(lines) + "\n</team_cycle>"
                )
            )

        if requested_compact:
            needs_compact = True
            messages[:] = auto_compact(
                messages,
                llm=base_llm,
                system_prompt=lead_system_prompt,
                transcript_dir=transcript_dir,
            )

        if used_todo:
            rounds_since_todo = 0
        else:
            rounds_since_todo += 1

        if rounds_since_todo >= 3:
            messages.append(
                HumanMessage(content="<reminder>请更新你的 todo 列表</reminder>")
            )
            rounds_since_todo = 0

    return LeadTurnResult(
        assistant_text=assistant_text,
        tool_calls=collected_tool_calls,
        team_responses=collected_team_responses,
        needs_compact=needs_compact,
        messages=messages,
    )


__all__ = ["DEFAULT_LEAD_SYSTEM_PROMPT", "LeadTurnResult", "execute_lead_turn"]
