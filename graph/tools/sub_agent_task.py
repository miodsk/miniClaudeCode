from langchain_core.tools import tool
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from dotenv import load_dotenv
import os

load_dotenv()

# 子智能体配置
SUB_MODEL = "deepseek-chat"
SUB_TEMPERATURE = 0.2


def create_subagent():
    """创建子智能体"""
    return ChatDeepSeek(
        model=SUB_MODEL,
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        temperature=SUB_TEMPERATURE,
    )


def run_subAgent(prompt: str, sub_tools) -> str:
    """
    运行子智能体，共享文件系统但使用独立的 messages 上下文。
    子智能体只返回最终文本摘要，不返回工具调用历史。
    """
    # 限制 prompt 长度，避免超限
    MAX_PROMPT_LEN = 5000
    if len(prompt) > MAX_PROMPT_LEN:
        prompt = prompt[:MAX_PROMPT_LEN] + "\n[...内容已截断...]"

    subagent = create_subagent().bind_tools(sub_tools)
    sub_messages = [HumanMessage(content=prompt)]
    MAX_TOOL_OUTPUT = 3000  # 限制单次工具输出长度

    try:
        for _ in range(30):  # 安全限制
            response = subagent.invoke(input=sub_messages)
            sub_messages.append(response)

            if not response.tool_calls:
                break

            for tool_call in response.tool_calls:
                selected_tool = next(
                    (t for t in sub_tools if t.name == tool_call["name"]), None
                )
                if selected_tool:
                    print(f"  [子智能体] 调用工具: {selected_tool.name}")
                    result = selected_tool.invoke(tool_call["args"])
                else:
                    result = f"未知工具: {tool_call['name']}"

                # 截断过长的工具输出
                result_str = str(result)
                if len(result_str) > MAX_TOOL_OUTPUT:
                    result_str = result_str[:MAX_TOOL_OUTPUT] + "\n[...输出已截断...]"

                sub_messages.append(
                    ToolMessage(tool_call_id=tool_call["id"], content=result_str)
                )

    except Exception as e:
        error_msg = str(e)
        if (
            "maximum context length" in error_msg.lower()
            or "tokens" in error_msg.lower()
        ):
            return f"[错误] 子任务上下文过长，超过了模型限制。请减少任务复杂度。"
        return f"[错误] 子任务执行失败: {error_msg}"

    # 只返回最终文本，子智能体的上下文全部丢弃
    if hasattr(response, "content") and response.content:
        return response.content
    return "(无返回内容)"


@tool
def sub_agent_task(prompt: str, description: str = "") -> str:
    """
    启动一个子智能体来处理子任务。

    Args:
        prompt: 子任务的具体描述
        description: 任务简短描述

    Returns:
        子智能体处理后的结果摘要
    """
    # 延迟导入避免循环依赖
    from graph.tools import son_tools

    print(f"[主智能体] 启动子任务: {description or prompt[:50]}...")
    result = run_subAgent(prompt, son_tools)
    print(f"[主智能体] 子任务完成，结果长度: {len(result)} 字符")
    return result
