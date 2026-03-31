from graph.tools.background_task import background_check, background_run
from graph.tools.compact import compact
from graph.tools.list_dir import list_dir
from graph.tools.load_skill import load_skill
from graph.tools.read_file import read_file
from graph.tools.safe_path import get_safe_path
from graph.tools.sub_agent_task import sub_agent_task
from graph.tools.todo_list import task_create, task_get, task_list, task_update
from graph.tools.web_search import search
from graph.tools.write_file import write_file


__all__ = [
    "search",
    "read_file",
    "write_file",
    "get_safe_path",
    "list_dir",
    "task_create",
    "task_update",
    "task_list",
    "task_get",
    "sub_agent_task",
    "load_skill",
    "compact",
    "background_run",
    "background_check",
    "TOOL_GROUPS",
    "AGENT_TOOL_POLICY",
    "get_static_tools_for_agent",
]


TOOL_GROUPS = {
    "inspect": [search, read_file, list_dir],
    "edit": [write_file, get_safe_path],
    "task_manage": [task_create, task_update],
    "task_read": [task_list, task_get],
    "background": [background_run, background_check],
    "knowledge": [load_skill],
    "context": [compact],
    "outsource": [sub_agent_task],
}


AGENT_TOOL_POLICY = {
    "lead": [
        "inspect",
        "task_manage",
        "task_read",
        "knowledge",
        "context",
        "outsource",
    ],
    "researcher": [
        "inspect",
        "task_read",
        "knowledge",
        "context",
    ],
    "coder": [
        "inspect",
        "edit",
        "task_read",
        "background",
        "knowledge",
        "context",
    ],
}


def get_static_tools_for_agent(agent_name: str) -> list:
    """根据角色名称解析静态工具列表。"""
    group_names = AGENT_TOOL_POLICY.get(agent_name)
    if group_names is None:
        raise ValueError(f"未知 agent: {agent_name}")

    resolved_tools = []
    seen_tool_names = set()

    for group_name in group_names:
        tools = TOOL_GROUPS.get(group_name)
        if tools is None:
            raise ValueError(f"未知工具组: {group_name}")

        for tool in tools:
            if tool.name not in seen_tool_names:
                resolved_tools.append(tool)
                seen_tool_names.add(tool.name)

    return resolved_tools
