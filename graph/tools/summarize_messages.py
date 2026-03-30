from langchain_core.tools import tool
from langchain_core.messages import (
    BaseMessage,      # 基类
    HumanMessage,     # 用户消息
    AIMessage,        # AI 响应
    SystemMessage,    # 系统消息
    ToolMessage,      # 工具调用结果
)
from typing import List
from langchain_deepseek import ChatDeepSeek
from dotenv import load_dotenv
import os
load_dotenv()

deepseek = ChatDeepSeek(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0.2,
)


@tool
def summarize_messages(messages: List[BaseMessage]) -> str:
    """
    总结一段对话历史。当你发现对话太长、需要提取核心要点或回顾之前的决策时，请调用此工具。
    输入应为消息对象列表。
    """
    # 1. 将消息列表格式化为易读的文本字符串
    chat_history_str = ""
    for m in messages:
        role = "用户" if isinstance(m, HumanMessage) else "AI"
        chat_history_str += f"{role}: {m.content}\n"

    # 2. 调用模型进行总结（这里直接复用你定义的 deepseek 实例）
    prompt = f"请简要总结以下对话的核心内容，忽略琐碎的寒暄：\n\n{chat_history_str}"
    response = deepseek.invoke(prompt)

    return response.content