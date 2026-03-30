from langchain_core.tools import tool
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum
from pathlib import Path
import json


class TodoStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Todo(BaseModel):
    id: int
    subject: str
    status: TodoStatus
    blocks: List[int] = []
    blocked_by: List[int] = []
    description: str = ""


class TaskManager:
    def __init__(self, tasks_dir: str):
        self.tasks_dir = Path(tasks_dir)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def _get_next_id(self) -> int:
        """获取下一个任务ID，避免重复"""
        tasks = self.list_tasks()
        if not tasks:
            return 1
        return max(t.id for t in tasks) + 1

    def _save_task(self, task: Todo):
        """保存任务到文件"""
        task_path = self.tasks_dir / f"task_{task.id}.json"
        task_path.write_text(task.model_dump_json(indent=4), encoding="utf-8")

    def _clear_dependency(self, completed_task_id: int):
        """完成任务时，自动从其他任务的 blocked_by 中移除"""
        for task in self.list_tasks():
            if completed_task_id in task.blocked_by:
                task.blocked_by.remove(completed_task_id)
                self._save_task(task)

    def list_tasks(self) -> List[Todo]:
        """列出所有任务"""
        tasks = []
        for f in self.tasks_dir.glob("task_*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            tasks.append(Todo(**data))
        return sorted(tasks, key=lambda t: t.id)

    def get_task(self, task_id: int) -> Todo:
        """获取单个任务详情"""
        task_path = self.tasks_dir / f"task_{task_id}.json"
        if not task_path.exists():
            raise FileNotFoundError(f"任务 {task_id} 不存在")
        data = json.loads(task_path.read_text(encoding="utf-8"))
        return Todo(**data)

    def create_task(self, subject: str, blocked_by: List[int] = None) -> Todo:
        """创建新任务"""
        task_id = self._get_next_id()
        task = Todo(
            id=task_id,
            subject=subject,
            status=TodoStatus.PENDING,
            blocks=[],
            blocked_by=blocked_by or [],
            description="",
        )
        self._save_task(task)
        return task

    def update_task(
        self,
        task_id: int,
        status: Optional[str] = None,
        subject: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Todo:
        """更新任务状态，完成时自动解锁后续任务"""
        task = self.get_task(task_id)

        if subject is not None:
            task.subject = subject
        if status is not None:
            task.status = status
        if description is not None:
            task.description = description

        # 完成时自动解锁
        if status == TodoStatus.COMPLETED:
            self._clear_dependency(task_id)

        self._save_task(task)
        return task

    def list_ready(self) -> List[Todo]:
        """列出可执行的任务（pending 且 blocked_by 为空）"""
        return [
            t
            for t in self.list_tasks()
            if t.status == TodoStatus.PENDING and not t.blocked_by
        ]

    def list_blocked(self) -> List[Todo]:
        """列出被卡住的任务"""
        return [
            t
            for t in self.list_tasks()
            if t.status == TodoStatus.PENDING and t.blocked_by
        ]


# 全局单例
TASK_MANAGER = TaskManager(".tasks")


@tool
def task_create(subject: str, blocked_by: str = "") -> str:
    """
    创建新任务。

    Args:
        subject: 任务标题
        blocked_by: 前置依赖任务ID，逗号分隔（如 "1,2" 表示依赖任务1和2）

    Returns:
        创建的任务信息
    """
    blocked_list = []
    if blocked_by.strip():
        blocked_list = [int(x.strip()) for x in blocked_by.split(",")]

    task = TASK_MANAGER.create_task(subject, blocked_by=blocked_list)

    # 更新依赖任务的 blocks 字段
    for dep_id in blocked_list:
        try:
            dep_task = TASK_MANAGER.get_task(dep_id)
            if task.id not in dep_task.blocks:
                dep_task.blocks.append(task.id)
                TASK_MANAGER._save_task(dep_task)
        except FileNotFoundError:
            pass

    return f"已创建任务 #{task.id}: {task.subject}\n依赖: {task.blocked_by or '无'}"


@tool
def task_update(task_id: int, status: str = "") -> str:
    """
    更新任务状态。

    Args:
        task_id: 任务ID
        status: 新状态 (pending/in_progress/completed)

    Returns:
        更新后的任务信息
    """
    kwargs = {"task_id": task_id}
    if status:
        kwargs["status"] = status

    task = TASK_MANAGER.update_task(**kwargs)

    result = f"任务 #{task.id}: {task.subject}\n状态: {task.status}"
    if status == "completed" and task.blocks:
        result += f"\n已解锁后续任务: {task.blocks}"
    return result


@tool
def task_list(show_all: bool = True) -> str:
    """
    列出所有任务。

    Args:
        show_all: 是否显示所有任务，默认True

    Returns:
        任务列表
    """
    tasks = TASK_MANAGER.list_tasks()
    if not tasks:
        return "暂无任务"

    lines = []
    for t in tasks:
        status_mark = {
            "pending": "[ ]",
            "in_progress": "[>]",
            "completed": "[x]",
        }.get(t.status, "[?]")
        blocked = f" (等待: {t.blocked_by})" if t.blocked_by else ""
        lines.append(f"{status_mark} #{t.id}: {t.subject}{blocked}")

    ready = TASK_MANAGER.list_ready()
    blocked = TASK_MANAGER.list_blocked()
    lines.append(f"\n可执行: {len(ready)} 个 | 被卡住: {len(blocked)} 个")

    return "\n".join(lines)


@tool
def task_get(task_id: int) -> str:
    """
    获取任务详情。

    Args:
        task_id: 任务ID

    Returns:
        任务详细信息
    """
    try:
        task = TASK_MANAGER.get_task(task_id)
        return (
            f"任务 #{task.id}: {task.subject}\n"
            f"状态: {task.status}\n"
            f"描述: {task.description or '无'}\n"
            f"依赖(blocked_by): {task.blocked_by or '无'}\n"
            f"阻塞(blocks): {task.blocks or '无'}"
        )
    except FileNotFoundError:
        return f"任务 {task_id} 不存在"
