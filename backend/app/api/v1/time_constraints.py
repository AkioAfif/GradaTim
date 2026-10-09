"""Kegiatan rutin mingguan (time_constraint): kuliah, gym, ... — dipakai menghitung waktu luang (D10)"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.common import ambil_milik_user, validasi_gabungan
from app.api.deps import get_current_user, get_db
from app.models.time_constraint import TimeConstraint
from app.models.user import User
from app.schemas.time_constraint import TimeConstraintCreate, TimeConstraintRead, TimeConstraintUpdate

router = APIRouter()

TIDAK_DITEMUKAN = "Kegiatan rutin tidak ditemukan"


def _ambil(db: Session, id_constraint: int, user: User) -> TimeConstraint:
    return ambil_milik_user(db, TimeConstraint, id_constraint, user, TIDAK_DITEMUKAN)


@router.get("", response_model=list[TimeConstraintRead])
def list_time_constraints(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[TimeConstraint]:
    query = (
        select(TimeConstraint)
        .where(TimeConstraint.id_user == current_user.id_user)
        .order_by(TimeConstraint.hari_dalam_minggu, TimeConstraint.waktu_mulai, TimeConstraint.id_constraint)
    )
    return list(db.scalars(query))


@router.post("", response_model=TimeConstraintRead, status_code=status.HTTP_201_CREATED)
def create_time_constraint(
    payload: TimeConstraintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TimeConstraint:
    baris = TimeConstraint(id_user=current_user.id_user, **payload.model_dump())
    db.add(baris)
    db.commit()
    db.refresh(baris)
    return baris


@router.get("/{id_constraint}", response_model=TimeConstraintRead)
def get_time_constraint(
    id_constraint: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> TimeConstraint:
    return _ambil(db, id_constraint, current_user)


@router.patch("/{id_constraint}", response_model=TimeConstraintRead)
def update_time_constraint(
    id_constraint: int,
    payload: TimeConstraintUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TimeConstraint:
    baris = _ambil(db, id_constraint, current_user)
    valid = validasi_gabungan(TimeConstraintCreate, baris, payload)
    for field, value in valid.model_dump().items():
        setattr(baris, field, value)
    db.commit()
    db.refresh(baris)
    return baris


@router.delete("/{id_constraint}", status_code=status.HTTP_204_NO_CONTENT)
def delete_time_constraint(
    id_constraint: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> None:
    db.delete(_ambil(db, id_constraint, current_user))
    db.commit()
