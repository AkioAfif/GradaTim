"""Pydantic request/response schemas - time_constraint.py (kegiatan rutin mingguan)"""

from datetime import time
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

NamaKegiatan = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
HariDalamMinggu = Annotated[int, Field(ge=0, le=6, description="0=Senin ... 6=Minggu")]


class TimeConstraintCreate(BaseModel):
    """Kegiatan rutin mingguan. `waktu_selesai` < `waktu_mulai` berarti melewati tengah malam
    (mis. 22:00-01:00), sama seperti `scheduler.WeeklyWindow`."""

    nama: NamaKegiatan
    hari_dalam_minggu: HariDalamMinggu
    waktu_mulai: time
    waktu_selesai: time

    @field_validator("waktu_mulai", "waktu_selesai")
    @classmethod
    def tanpa_zona_waktu(cls, value: time) -> time:
        if value.tzinfo is not None:
            raise ValueError("Jam tidak boleh memakai zona waktu (gunakan jam lokal WIB)")
        return value

    @model_validator(mode="after")
    def jam_mulai_beda_dengan_selesai(self) -> "TimeConstraintCreate":
        if self.waktu_mulai == self.waktu_selesai:
            raise ValueError("Jam mulai dan jam selesai tidak boleh sama")
        return self


class TimeConstraintUpdate(BaseModel):
    nama: Optional[NamaKegiatan] = None
    hari_dalam_minggu: Optional[HariDalamMinggu] = None
    waktu_mulai: Optional[time] = None
    waktu_selesai: Optional[time] = None


class TimeConstraintRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_constraint: int
    id_user: int
    nama: str
    hari_dalam_minggu: int
    waktu_mulai: time
    waktu_selesai: time
