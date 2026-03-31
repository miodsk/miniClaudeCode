from .web_search import search
from .read_file import read_file
from .write_file import write_file
from .safe_path import get_safe_path
from .list_dir import list_dir
from .todo_list import task_create, task_update, task_list, task_get
from .sub_agent_task import sub_agent_task
from .load_skill import load_skill
from .compact import compact
from .background_task import background_run, background_check

# 父智能体工具：所有工具
father_tools = [
    search,
    read_file,
    write_file,
    get_safe_path,
    list_dir,
    task_create,
    task_update,
    task_list,
    task_get,
    sub_agent_task,
    load_skill,
    compact,
    background_run,
    background_check,
]

# 子智能体工具：基础工具（不含 task 系列、load_skill、compact，防止递归和依赖）
son_tools = [search, read_file, write_file, get_safe_path, list_dir]
