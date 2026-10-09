"""FR-5: Agenda (acara sekali jalan) + peringatan bentrok"""

from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.common import ambil_milik_user, validasi_gabungan
from app.api.deps import get_current_user, get_db
from app.models.agenda import Agenda
from app.models.user import User
from app.schemas.agenda import AgendaCreate, AgendaRead, AgendaUpdate
from app.services import kalender_service

router = APIRouter()

TIDAK_DITEMUKAN = "Agenda tidak ditemukan"


def _ambil(db: Session, id_agenda: int, user: User) -> Agenda:
    return ambil_milik_user(db, Agenda, id_agenda, user, TIDAK_DITEMUKAN)


def _dengan_peringatan(db: Session, user: User, agenda: Agenda) -> AgendaRead:
    peringatan = kalender_service.peringatan_bentrok_agenda(db, user, agenda)
    return AgendaRead.model_validate(agenda).model_copy(update={"peringatan_bentrok": peringatan})


@router.get("", response_model=list[AgendaRead])
def list_agenda(
    mulai: Optional[date] = None,
    sampai: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Agenda]:
    """Agenda milik user, urut waktu mulai. `mulai`/`sampai` (inklusif) menyaring agenda yang
    beririsan dengan rentang [mulai 00:00, sampai+1 hari 00:00)."""
    if mulai is not None and sampai is not None and sampai < mulai:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Tanggal sampai tidak boleh sebelum tanggal mulai",
        )
    query = select(Agenda).where(Agenda.id_user == current_user.id_user)
    if mulai is not None:
        query = query.where(Agenda.waktu_selesai > datetime.combine(mulai, time.min))
    if sampai is not None:
        query = query.where(Agenda.waktu_mulai < datetime.combine(sampai + timedelta(days=1), time.min))
    return list(db.scalars(query.order_by(Agenda.waktu_mulai, Agenda.id_agenda)))


@router.post("", response_model=AgendaRead, status_code=status.HTTP_201_CREATED)
def create_agenda(
    payload: AgendaCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> AgendaRead:
    agenda = Agenda(id_user=current_user.id_user, **payload.model_dump())
    db.add(agenda)
    db.commit()
    db.refresh(agenda)
    return _dengan_peringatan(db, current_user, agenda)


@router.get("/{id_agenda}", response_model=AgendaRead)
def get_agenda(
    id_agenda: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Agenda:
    return _ambil(db, id_agenda, current_user)


@router.patch("/{id_agenda}", response_model=AgendaRead)
def update_agenda(
    id_agenda: int,
    payload: AgendaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgendaRead:
    agenda = _ambil(db, id_agenda, current_user)
    valid = validasi_gabungan(AgendaCreate, agenda, payload)
    for field, value in valid.model_dump().items():
        setattr(agenda, field, value)
    db.commit()
    db.refresh(agenda)
    return _dengan_peringatan(db, current_user, agenda)


@router.delete("/{id_agenda}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agenda(
    id_agenda: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> None:
    db.delete(_ambil(db, id_agenda, current_user))
    db.commit()
