"""FR-3 & FR-4: Today Action List & Progress Tracker (FR-10: checklist status task)"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, get_db
from app.models.goal import Goal
from app.models.milestone import Milestone
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskRead, TaskStatus, TaskStatusUpdate, task_ke_read

router = APIRouter()

TIDAK_DITEMUKAN = "Task tidak ditemukan"


def _task_milik(user: User) -> Select[tuple[Task]]:
    """Task milik user: kepemilikan lewat task → milestone → goal → user dalam satu query join."""
    return (
        select(Task)
        .join(Milestone, Task.id_milestone == Milestone.id_milestone)
        .join(Goal, Milestone.id_goal == Goal.id_goal)
        .where(Goal.id_user == user.id_user)
        .options(selectinload(Task.prasyarat))
    )


def _ambil(db: Session, id_task: int, user: User) -> Task:
    task = db.scalar(_task_milik(user).where(Task.id_task == id_task))
    if task is None:  # tidak ada atau milik user lain → sama-sama 404
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=TIDAK_DITEMUKAN)
    return task


@router.get("", response_model=list[TaskRead])
def list_tasks(
    id_goal: Optional[int] = None,
    status: Optional[TaskStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TaskRead]:
    query = _task_milik(current_user)
    if id_goal is not None:
        query = query.where(Goal.id_goal == id_goal)
    if status is not None:
        query = query.where(Task.status == status)
    query = query.order_by(Task.deadline.asc().nulls_last(), Task.id_task)
    return [task_ke_read(t) for t in db.scalars(query)]


@router.get("/{id_task}", response_model=TaskRead)
def get_task(
    id_task: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> TaskRead:
    return task_ke_read(_ambil(db, id_task, current_user))


@router.patch("/{id_task}", response_model=TaskRead)
def update_task_status(
    id_task: int,
    payload: TaskStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    """Ubah status task (checklist FR-10). Baris jadwal_task sengaja tidak disentuh."""
    task = _ambil(db, id_task, current_user)
    task.status = payload.status
    db.commit()
    return task_ke_read(_ambil(db, id_task, current_user))
