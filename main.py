from langchain_deepseek import ChatDeepSeek
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
import json
from graph.tools import father_tools
from graph.tools.load_skill import SKILL_LOADER
import os
import time
from pathlib import Path

load_dotenv()

tools_map = {tool.name: tool for tool in father_tools}

deepseek = ChatDeepSeek(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0.2,
).bind_tools(father_tools)

SYSTEM_PROMPT = f"""你是一个有用的助手，可以帮助我完成一些任务。

做多步任务时，先用 todo 工具列出计划，然后逐步完成并更新状态。
状态: pending(待做) → in_progress(进行中) → completed(完成)

可用技能:
{SKILL_LOADER.get_descriptions()}

遇到不熟悉的领域时，先用 load_skill 工具加载相关技能知识。"""

# Layer 1: micro_compact 配置
KEEP_RECENT = 3  # 保留最近的 tool_result 数量

# Layer 2: auto_compact 配置
THRESHOLD = 50000  # token 阈值
TRANSCRIPT_DIR = Path(".transcripts")


def micro_compact(messages: list) -> list:
    """Layer 1: 把超过 KEEP_RECENT 的 ToolMessage 替换为占位符"""
    tool_name_map = {}
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_name_map[tc.id] = tc.name

    tool_messages = [
        (i, msg) for i, msg in enumerate(messages) if isinstance(msg, ToolMessage)
    ]

    if len(tool_messages) <= KEEP_RECENT:
        return messages

    for idx, msg in tool_messages[:-KEEP_RECENT]:
        if isinstance(msg.content, str) and len(msg.content) > 100:
            tool_name = tool_name_map.get(msg.tool_call_id, "unknown")
            msg.content = f"[Previous: used {tool_name}]"

    return messages


def estimate_tokens(messages: list) -> int:
    """粗略估算 token 数（约4字符=1token）"""
    return len(str(messages)) // 4


def auto_compact(messages: list) -> list:
    """
    Layer 2: token 超阈值时自动压缩。
    1. 保存完整对话到磁盘
    2. 让 LLM 总结对话
    3. 用总结替换 messages
    """
    # 1. 保存 transcript 到磁盘
    TRANSCRIPT_DIR.mkdir(exist_ok=True)
    timestamp = int(time.time())
    transcript_path = TRANSCRIPT_DIR / f"transcript_{timestamp}.jsonl"
    with open(transcript_path, "w", encoding="utf-8") as f:
        for msg in messages:
            f.write(json.dumps(msg.to_json(), ensure_ascii=False) + "\n")
    print(f"[auto_compact] 对话已保存到: {transcript_path}")

    # 2. 让 LLM 总结对话
    messages_str = json.dumps([m.to_json() for m in messages], ensure_ascii=False)
    # 截断，防止过长
    messages_str = messages_str[:80000]

    summary_response = deepseek.invoke(
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

    # 3. 返回新的 messages，保留 SystemMessage + 总结
    return [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"[对话已压缩] {summary}"),
        AIMessage(content="明白，我了解了之前的对话内容，继续工作。"),
    ]


def loop():
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    rounds_since_todo = 0

    while True:
        query = input("请输入你的问题：")
        if query.lower() in ("q", "exit", "退出"):
            break
        messages.append(HumanMessage(content=query))

        while True:
            # Layer 1: micro_compact 每次 LLM 调用前执行
            micro_compact(messages)

            # Layer 2: token 超阈值时自动压缩
            if estimate_tokens(messages) > THRESHOLD:
                print("[auto_compact] token 超阈值，开始压缩对话...")
                messages[:] = auto_compact(messages)

            response = deepseek.invoke(input=messages)
            print(f"AI 回复: {response.content}\n工具调用: {response.tool_calls}")
            messages.append(response)

            if not response.tool_calls:
                break

            used_todo = False
            need_compact = False  # Layer 3: compact 工具标记

            for tool_call in response.tool_calls:
                if tool_call["name"] == "compact":
                    # Layer 3: compact 工具，标记需要压缩
                    need_compact = True
                    result = "压缩已触发"
                else:
                    selected_tool = tools_map[tool_call["name"]]
                    print(f"调用工具：{selected_tool.name}")
                    print(f"工具参数：{tool_call['args']}")
                    result = selected_tool.invoke(tool_call["args"])

                if tool_call["name"] == "todo":
                    used_todo = True

                messages.append(
                    ToolMessage(tool_call_id=tool_call["id"], content=str(result))
                )

            # Layer 3: LLM 主动调用 compact 工具时触发压缩
            if need_compact:
                print("[manual compact] LLM 请求压缩对话...")
                messages[:] = auto_compact(messages)

            # nag reminder: 3轮没更新todo就提醒
            if used_todo:
                rounds_since_todo = 0
            else:
                rounds_since_todo += 1

            if rounds_since_todo >= 3:
                print("[提醒] 请更新你的 todo 列表")
                messages.append(
                    HumanMessage(content="<reminder>请更新你的 todo 列表</reminder>")
                )
                rounds_since_todo = 0

        # 保存对话历史
        readable_history = [m.to_json() for m in messages]
        with open("output.json", "w", encoding="utf-8") as f:
            json.dump(readable_history, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    loop()
