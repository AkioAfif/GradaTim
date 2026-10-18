"""Pydantic request/response schemas - task.py"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

from app.models.task import Task

# sama dengan app.core.status.TASK_STATUSES; Literal agar nilai lain dijawab 422
TaskStatus = Literal["todo", "in_progress", "done"]


class TaskRead(BaseModel):
    id_task: int
    id_milestone: int
    id_parent_task: Optional[int]
    nama_task: str
    deskripsi: Optional[str]
    deadline: Optional[datetime]
    durasi_estimasi: Optional[int]
    status: str
    tingkat_effort: Optional[str]
    tingkat_impact: Optional[str]
    prasyarat: list[int]  # id_task yang harus selesai sebelum task ini


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


def task_ke_read(task: Task) -> TaskRead:
    """Mapper ORM → TaskRead. `task.prasyarat` sebaiknya sudah di-selectinload."""
    return TaskRead(
        id_task=task.id_task,
        id_milestone=task.id_milestone,
        id_parent_task=task.id_parent_task,
        nama_task=task.nama_task,
        deskripsi=task.deskripsi,
        deadline=task.deadline,
        durasi_estimasi=task.durasi_estimasi,
        status=task.status,
        tingkat_effort=task.tingkat_effort,
        tingkat_impact=task.tingkat_impact,
        prasyarat=sorted(dep.id_task_prasyarat for dep in task.prasyarat),
    )
