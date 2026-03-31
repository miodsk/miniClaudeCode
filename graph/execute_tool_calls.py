from typing import Any

from langchain_core.messages import ToolMessage


TODO_TOOL_NAMES = {
    "task_create",
    "task_update",
    "task_list",
    "task_get",
}


def execute_tool_calls(
    response: Any, messages: list[Any], tools_map: dict[str, Any]
) -> dict[str, bool]:
    used_todo = False
    need_compact = False

    for tool_call in response.tool_calls:
        if tool_call["name"] == "compact":
            need_compact = True
            result = "压缩已触发"
        else:
            selected_tool = tools_map[tool_call["name"]]
            result = selected_tool.invoke(tool_call["args"])

        if tool_call["name"] in TODO_TOOL_NAMES:
            used_todo = True

        messages.append(ToolMessage(tool_call_id=tool_call["id"], content=str(result)))

    return {
        "used_todo": used_todo,
        "need_compact": need_compact,
    }
