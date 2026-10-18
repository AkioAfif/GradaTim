"""Pydantic request/response schemas - goal.py (FR-1, FR-2)"""

from datetime import date, datetime
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from app.core import waktu
from app.models.goal import Goal
from app.models.milestone import Milestone
from app.schemas.task import TaskRead, task_ke_read

JudulGoal = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=255)]
DeskripsiGoal = Annotated[str, Field(max_length=2000)]


def _deadline_tidak_lampau(deadline: date) -> date:
    if deadline < waktu.hari_ini():
        raise ValueError("Deadline tidak boleh di masa lalu")
    return deadline


class GoalCreate(BaseModel):
    judul_goal: JudulGoal
    deskripsi: Optional[DeskripsiGoal] = None
    deadline: date

    @field_validator("deadline")
    @classmethod
    def deadline_tidak_lampau(cls, value: date) -> date:
        return _deadline_tidak_lampau(value)


class GoalUpdate(BaseModel):
    """Status goal sengaja belum bisa diubah: nilai status goal belum disepakati tim."""

    judul_goal: Optional[JudulGoal] = None
    deskripsi: Optional[DeskripsiGoal] = None
    deadline: Optional[date] = None

    @field_validator("deadline")
    @classmethod
    def deadline_tidak_lampau(cls, value: Optional[date]) -> Optional[date]:
        return None if value is None else _deadline_tidak_lampau(value)

    @model_validator(mode="after")
    def wajib_tidak_null(self) -> "GoalUpdate":
        # deskripsi boleh dikosongkan (null); judul dan deadline wajib ada seperti saat membuat goal
        for field in ("judul_goal", "deadline"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} tidak boleh kosong")
        return self


class GoalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_goal: int
    judul_goal: str
    deskripsi: Optional[str]
    deadline: Optional[datetime]
    status: str


class MilestoneRead(BaseModel):
    id_milestone: int
    id_parent_milestone: Optional[int]
    judul_milestone: str
    deskripsi: Optional[str]
    deadline: Optional[datetime]
    urutan: int
    status: str
    tipe: Optional[str]
    tasks: list[TaskRead]


class GoalDetail(GoalRead):
    # daftar datar urut `urutan`; frontend menyusun pohon bulanan → mingguan dari id_parent_milestone
    milestones: list[MilestoneRead]


class DecomposeRequest(BaseModel):
    menit_harian: Optional[int] = Field(
        default=None, ge=15, le=720,
        description="Override waktu luang per hari (menit). Kosong = dihitung dari jam aktif − kegiatan rutin (D6).",
    )


def _milestone_ke_read(milestone: Milestone) -> MilestoneRead:
    tasks = sorted(milestone.tasks, key=lambda t: (t.deadline is None, t.deadline or datetime.min, t.id_task))
    return MilestoneRead(
        id_milestone=milestone.id_milestone,
        id_parent_milestone=milestone.id_parent_milestone,
        judul_milestone=milestone.judul_milestone,
        deskripsi=milestone.deskripsi,
        deadline=milestone.deadline,
        urutan=milestone.urutan,
        status=milestone.status,
        tipe=milestone.tipe,
        tasks=[task_ke_read(t) for t in tasks],
    )


def goal_ke_detail(goal: Goal, milestones: list[Milestone]) -> GoalDetail:
    """Mapper ORM → GoalDetail. `milestones` sudah urut dan sudah memuat tasks + prasyarat."""
    return GoalDetail(
        **GoalRead.model_validate(goal).model_dump(),
        milestones=[_milestone_ke_read(m) for m in milestones],
    )
