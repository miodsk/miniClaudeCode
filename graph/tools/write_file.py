from langchain_core.tools import tool

@tool
def write_file(file_path: str, content: str) -> str:
    """
    将内容写入文件
    """
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)
    return f"文件已写入: {file_path}"