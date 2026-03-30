from langchain_core.tools import tool


@tool
def compact(focus: str = "") -> str:
    """
    触发对话压缩。当对话太长、需要腾出上下文空间时调用此工具。

    Args:
        focus: 压缩时要保留的重点内容描述（可选）

    Returns:
        压缩已触发的确认消息
    """
    # 实际的压缩逻辑在 main.py 的 auto_compact 函数里
    # 这里只是返回一个标记，让代码检测到后触发压缩
    if focus:
        return f"压缩已触发，重点保留: {focus}"
    return "压缩已触发"
