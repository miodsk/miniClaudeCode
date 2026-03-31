from pathlib import Path
import os
import uuid
from dotenv import load_dotenv
from langchain_core.tools import tool
from pydantic import BaseModel
load_dotenv()
import subprocess
from enum import Enum
from threading import Lock,Thread
WORKDIR = os.getenv("WORKDIR")
COMMAND_TIMEOUT = 300
class Status(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
class BgTask(BaseModel):
    task_id: str
    command:str
    status:Status
    return_code:int | None
    output:str
class Notification(BaseModel):
    task_id: str
    command:str
    status:Status
    preview:str

def get_project_root():
    """获取项目根目录（包含 .git 文件夹或特定标志文件的位置）"""
    current = Path.cwd()

    # 向上查找直到找到项目根目录
    for parent in current.parents:
        # 查找标志文件/文件夹
        if (parent / ".git").exists():
            return parent
        if (parent / "pyproject.toml").exists():
            return parent
        if (parent / "setup.py").exists():
            return parent
        if (parent / "requirements.txt").exists():
            return parent

    # 如果找不到，返回当前目录
    return current


root_dir = get_project_root()
work_dir = root_dir / WORKDIR if WORKDIR else root_dir


def run_command_sync(command: str):
    try:
        result = subprocess.run(
            command,
            cwd=work_dir,
            capture_output=True,
            text=True,
            shell=True,
            check=False,
            encoding='utf-8',
            timeout=COMMAND_TIMEOUT
        )
        output = f"stdout:\n{result.stdout or ''}\n\nstderr:\n{result.stderr or ''}"
        code = result.returncode
        if result.returncode == 0:
            return {
                "status": "completed",
                "return_code": code,
                "output": output
            }
        else:
            return {
                "status": "failed",
                "return_code": code,
                "output": output
            }
    except subprocess.TimeoutExpired as e:
        output = f"stdout:\n{e.stdout or ''}\n\nstderr:\n{e.stderr or ''}"
        return {
            "status": "timeout",
            "return_code": None,
            "output": output or f"Error: Timeout ({COMMAND_TIMEOUT}s)"
        }
    except Exception as e:
        return {
            "status": "failed",
            "return_code": None,
            "output": f"Error: {e}"
        }
class BackgroundManager:
    def __init__(self):
        self.tasks = {}
        self._notification_queue = []
        self._lock = Lock()

    def run(self, command: str) -> str:
        task_id = str(uuid.uuid4())[:8]
        with self._lock:
            self.tasks[task_id] = {
                "task_id": task_id,
                "command": command,
                "status": "running",
                "return_code": None,
                "output": "",
            }
        thread = Thread(target=self._execute, args=(task_id, command), daemon=True)
        thread.start()
        return task_id
    def _execute(self, task_id, command):
        result = run_command_sync(command)
        with self._lock:
            self.tasks[task_id]["status"] = result["status"]
            self.tasks[task_id]["return_code"] = result["return_code"]
            self.tasks[task_id]["output"] = result["output"]
            self._notification_queue.append({
                "task_id": task_id,
                "command": command,
                "status": result["status"],
                "preview": result["output"][:200],
            })
    def drain_notifications(self):
        with self._lock:
            items = self._notification_queue[:]
            self._notification_queue.clear()
            return items
    def check(self, task_id: str = ""):
        with self._lock:
            if task_id:
                task = self.tasks.get(task_id)
                if not task:
                    return "没找到任务"
                return str(task)

            if not self.tasks:
                return "暂无后台任务"

            lines = []
            for task in self.tasks.values():
                lines.append(f"[{task['status']}] {task['task_id']} - {task['command']}")
            return "\n".join(lines)
BG_MANAGER = BackgroundManager()


@tool
def background_run(command: str) -> str:
    """后台执行一个耗时命令，立即返回任务ID。"""
    task_id = BG_MANAGER.run(command)
    return f"后台任务 {task_id} 已启动: {command}"


@tool
def background_check(task_id: str = "") -> str:
    """查看后台任务状态；不传 task_id 时列出全部任务。"""
    return BG_MANAGER.check(task_id)
