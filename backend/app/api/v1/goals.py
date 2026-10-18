"""FR-2: AI Goal Decomposition & CRUD"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import exists, select
from sqlalchemy.orm import Session, selectinload

from app.api.common import ambil_milik_user
from app.api.deps import get_current_user, get_db
from app.core import waktu
from app.core.status import GOAL_ACTIVE
from app.models.goal import Goal
from app.models.milestone import Milestone
from app.models.task import Task
from app.models.user import User
from app.schemas.ai_decomposition import GoalDecompositionRequest
from app.schemas.goal import DecomposeRequest, GoalCreate, GoalDetail, GoalRead, GoalUpdate, goal_ke_detail
from app.services import ai_service, goal_service

router = APIRouter()

TIDAK_DITEMUKAN = "Goal tidak ditemukan"


def _ambil(db: Session, id_goal: int, user: User) -> Goal:
    return ambil_milik_user(db, Goal, id_goal, user, TIDAK_DITEMUKAN)


def _detail(db: Session, goal: Goal) -> GoalDetail:
    milestones = db.scalars(
        select(Milestone)
        .where(Milestone.id_goal == goal.id_goal)
        .order_by(Milestone.urutan, Milestone.id_milestone)
        .options(selectinload(Milestone.tasks).selectinload(Task.prasyarat))
    ).all()
    return goal_ke_detail(goal, list(milestones))


def _tolak(kode: int, detail: str) -> HTTPException:
    return HTTPException(status_code=kode, detail=detail)


@router.get("", response_model=list[GoalRead])
def list_goals(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[Goal]:
    query = select(Goal).where(Goal.id_user == current_user.id_user).order_by(Goal.id_goal.desc())
    return list(db.scalars(query))


@router.post("", response_model=GoalRead, status_code=status.HTTP_201_CREATED)
def create_goal(
    payload: GoalCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Goal:
    goal = Goal(
        id_user=current_user.id_user,
        judul_goal=payload.judul_goal,
        deskripsi=payload.deskripsi,
        deadline=waktu.akhir_hari(payload.deadline),
        status=GOAL_ACTIVE,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.get("/{id_goal}", response_model=GoalDetail)
def get_goal(
    id_goal: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> GoalDetail:
    return _detail(db, _ambil(db, id_goal, current_user))


@router.patch("/{id_goal}", response_model=GoalRead)
def update_goal(
    id_goal: int,
    payload: GoalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Goal:
    goal = _ambil(db, id_goal, current_user)
    perubahan = payload.model_dump(exclude_unset=True)
    if "deadline" in perubahan:
        perubahan["deadline"] = waktu.akhir_hari(perubahan["deadline"])
    for field, value in perubahan.items():
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return goal


@router.delete("/{id_goal}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    id_goal: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> None:
    # cascade ORM: milestone → task → task_dependency & jadwal_task
    db.delete(_ambil(db, id_goal, current_user))
    db.commit()


@router.post("/{id_goal}/decompose", response_model=GoalDetail, status_code=status.HTTP_201_CREATED)
def decompose_goal(
    id_goal: int,
    payload: Optional[DecomposeRequest] = None,
    replace: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalDetail:
    """Pecah goal dengan AI lalu simpan milestone & task-nya (FR-2).

    `?replace=true` mengganti hasil dekomposisi sebelumnya; tanpa itu, goal yang sudah punya
    milestone dijawab 409.
    """
    goal = _ambil(db, id_goal, current_user)
    today = waktu.hari_ini()
    if goal.deadline is None:
        raise _tolak(status.HTTP_422_UNPROCESSABLE_CONTENT, "Goal belum punya deadline")
    if goal.deadline.date() < today:
        raise _tolak(status.HTTP_422_UNPROCESSABLE_CONTENT, "Deadline tidak boleh di masa lalu")
    if not replace and db.scalar(select(exists().where(Milestone.id_goal == goal.id_goal))):
        raise _tolak(status.HTTP_409_CONFLICT, "Goal sudah didekomposisi")

    if payload is not None and payload.menit_harian is not None:
        menit_harian = payload.menit_harian
    else:
        try:
            menit_harian = goal_service.hitung_menit_harian(db, current_user)
        except goal_service.WaktuLuangTidakCukup as e:
            raise _tolak(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e

    request = GoalDecompositionRequest(
        judul_goal=goal.judul_goal,
        deskripsi=goal.deskripsi,
        deadline=goal.deadline.date(),
        menit_harian=menit_harian,
    )
    try:
        hasil = ai_service.decompose_goal(request, today=today)
    except ai_service.AIServiceError as e:
        raise _tolak(status.HTTP_502_BAD_GATEWAY, f"Gagal memproses goal dengan AI: {e}") from e

    goal_service.simpan_dekomposisi(db, goal, hasil, today)
    db.refresh(goal)
    return _detail(db, goal)
