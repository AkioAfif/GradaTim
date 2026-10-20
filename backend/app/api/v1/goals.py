"""FR-2: AI Goal Decomposition & CRUD"""

from datetime import timedelta
from typing import Literal, Optional

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
from app.schemas.goal import (
    DecomposeRequest,
    GoalCreate,
    GoalDetail,
    GoalRead,
    GoalUpdate,
    RincianMingguRead,
    goal_ke_detail,
    rincian_ke_read,
)
from app.services import ai_service, goal_service

router = APIRouter()

TIDAK_DITEMUKAN = "Goal tidak ditemukan"


def _ambil(db: Session, id_goal: int, user: User) -> Goal:
    return ambil_milik_user(db, Goal, id_goal, user, TIDAK_DITEMUKAN)


def _detail(db: Session, goal: Goal) -> GoalDetail:
    milestones = db.scalars(
        select(Milestone)
        .where(Milestone.id_goal == goal.id_goal)
        .options(selectinload(Milestone.tasks).selectinload(Task.prasyarat))
    ).all()
    # urutan pohon: Bulan 1, minggu-minggunya, Bulan 2, ... (milestone datar lama: menurut urutan)
    return goal_ke_detail(goal, sorted(milestones, key=goal_service.urutan_milestone))


def _tolak(kode: int, detail: str) -> HTTPException:
    return HTTPException(status_code=kode, detail=detail)


def _menit_harian(db: Session, user: User, payload: Optional[DecomposeRequest]) -> int:
    """menit_harian dari body bila diisi, selain itu dihitung dari jam aktif − kegiatan rutin (D6)."""
    if payload is not None and payload.menit_harian is not None:
        return payload.menit_harian
    try:
        return goal_service.hitung_menit_harian(db, user)
    except goal_service.WaktuLuangTidakCukup as e:
        raise _tolak(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e


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
    """Susun rencana goal dengan AI lalu simpan (FR-2, D4, D11): milestone `bulanan` → `mingguan`
    untuk seluruh durasi goal, dan task untuk minggu ini saja (minggu berikutnya dirinci belakangan).

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

    menit_harian = _menit_harian(db, current_user, payload)

    request = GoalDecompositionRequest(
        judul_goal=goal.judul_goal,
        deskripsi=goal.deskripsi,
        deadline=goal.deadline.date(),
        menit_harian=menit_harian,
    )
    try:
        rencana = ai_service.rencanakan_goal(request, today=today)
    except ai_service.AIServiceError as e:
        raise _tolak(status.HTTP_502_BAD_GATEWAY, f"Gagal memproses goal dengan AI: {e}") from e

    goal_service.simpan_dekomposisi(db, goal, rencana)
    db.refresh(goal)
    return _detail(db, goal)


HARI_SABTU = 5  # date.weekday()


@router.post("/{id_goal}/rinci-minggu", response_model=RincianMingguRead)
def rinci_minggu(
    id_goal: int,
    minggu: Literal["ini", "depan"] = "ini",
    payload: Optional[DecomposeRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RincianMingguRead:
    """Rinci task untuk target mingguan minggu ini (atau minggu depan, mulai hari Sabtu) dengan AI,
    berdasarkan progres task minggu-minggu sebelumnya (D11).

    Idempotent: bila minggu itu sudah punya task, task yang ada dikembalikan (`baru: false`) tanpa
    memanggil AI. Endpoint ini tidak menjadwalkan; panggil `POST /jadwal/goal/{id_goal}` sesudahnya
    (task minggu depan baru masuk jadwal saat minggunya tiba).
    """
    goal = _ambil(db, id_goal, current_user)
    today = waktu.hari_ini()
    tanggal = today
    if minggu == "depan":
        if today.weekday() < HARI_SABTU:
            raise _tolak(status.HTTP_409_CONFLICT, "Task minggu depan baru bisa dirinci mulai hari Sabtu")
        tanggal = today + timedelta(days=7)

    milestone = goal_service.milestone_minggu(db, goal, tanggal)
    if milestone is None:
        raise _tolak(status.HTTP_404_NOT_FOUND, f"Goal tidak punya target untuk minggu {minggu}")
    if milestone.tasks:
        return rincian_ke_read(milestone, baru=False)

    request = goal_service.rincian_minggu_request(db, goal, milestone, _menit_harian(db, current_user, payload))
    try:
        tasks = ai_service.rinci_minggu(request, today=today)
    except ai_service.AIServiceError as e:
        raise _tolak(status.HTTP_502_BAD_GATEWAY, f"Gagal merinci minggu dengan AI: {e}") from e

    goal_service.simpan_task_minggu(db, milestone, tasks)
    db.refresh(milestone)
    return rincian_ke_read(milestone, baru=True)
