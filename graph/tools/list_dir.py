import os
import sys
from pathlib import Path

from langchain.tools import tool
from dotenv import load_dotenv
load_dotenv()

@tool
def list_dir(path_str: str, recursive: bool = False) -> str:
    """
    列出文件夹内容。
    """
    base_path = Path(path_str)

    # 1. 基础检查
    if not base_path.exists():
        return f"错误: 路径 '{path_str}' 不存在。"
    if not base_path.is_dir():
        return f"错误: '{path_str}' 不是一个目录。"

    # 2. 获取内容
    if recursive:
        # rglob("*") 递归查找所有文件和文件夹
        # 使用 relative_to 保持路径层级感
        entries = [str(p.relative_to(base_path)) for p in base_path.rglob("*")]
    else:
        # iterdir() 只看当前层
        entries = [p.name for p in base_path.iterdir()]

    # 3. 排序并合并结果
    if not entries:
        return "目录为空。"

    return "\n".join(sorted(entries))
