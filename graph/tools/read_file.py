from langchain_core.tools import tool
from typing import Optional
@tool
def read_file(file_path: str,limit:Optional[int]=None) -> str:
    """
    读取文件内容
    """
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read(limit) if limit else file.read()
    return content