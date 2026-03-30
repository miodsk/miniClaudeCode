from langchain_core.tools import tool
from dotenv import load_dotenv
import os
from pathlib import Path
load_dotenv()
base_dir = os.getenv("BASE_DIR")
@tool
def get_safe_path(user_input_path: str) -> bool:
    """
    使用 pathlib 确保目标路径在安全的工作目录内。
    Args:
        user_input_path: 用户提供的相对路径
    Returns:
        如果路径安全返回 True，否则返回 False
    """
    # 1. 定义并解析基准目录的绝对路径
    base = Path(base_dir).resolve()

    # 2. 将用户输入连接到基准目录，并解析出最终的真实路径
    # .resolve() 会自动处理其中的 .. 和 ./，并追踪软链接
    target = (base / user_input_path).resolve()

    # 3. 检查目标路径是否属于基准目录（Python 3.9+ 核心方法）
    if not target.is_relative_to(base):
        return False

    return True