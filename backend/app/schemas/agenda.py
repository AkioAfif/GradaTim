"""Pydantic request/response schemas - agenda.py (acara sekali jalan, FR-5)"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.core import waktu
from app.schemas.time_constraint import NamaKegiatan


class AgendaCreate(BaseModel):
    """Datetime ber-timezone dikonversi ke WIB naive; datetime tanpa timezone dianggap WIB."""

    nama: NamaKegiatan
    waktu_mulai: datetime
    waktu_selesai: datetime

    @field_validator("waktu_mulai", "waktu_selesai")
    @classmethod
    def normalisasi_wib(cls, value: datetime) -> datetime:
        return waktu.ke_wib_naif(value)

    @model_validator(mode="after")
    def rentang_valid(self) -> "AgendaCreate":
        if self.waktu_selesai <= self.waktu_mulai:
            raise ValueError("Waktu selesai harus setelah waktu mulai")
        if self.waktu_mulai.date() != self.waktu_selesai.date():
            raise ValueError("Agenda harus selesai di hari yang sama")
        return self


class AgendaUpdate(BaseModel):
    nama: Optional[NamaKegiatan] = None
    waktu_mulai: Optional[datetime] = None
    waktu_selesai: Optional[datetime] = None


class AgendaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_agenda: int
    id_user: int
    nama: str
    waktu_mulai: datetime
    waktu_selesai: datetime
    # diisi hanya pada respons POST/PATCH; agenda tetap disimpan walau bentrok
    peringatan_bentrok: list[str] = []
