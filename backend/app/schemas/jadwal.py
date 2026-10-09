"""Pydantic request/response schemas - jadwal.py (FR-4, FR-5, FR-11)"""

from datetime import datetime, time, timedelta, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# Semua waktu di database adalah WIB tanpa timezone. Waktu dari client yang membawa timezone
# (mis. "2026-10-07T06:00:00Z" dari toISOString() JavaScript) diubah ke WIB.
WIB = timezone(timedelta(hours=7))


class BlokKalender(BaseModel):
    """Kegiatan rutin atau agenda pada tanggal & jam konkret."""

    nama: str
    waktu_mulai: datetime
    waktu_selesai: datetime


class SesiRead(BaseModel):
    """Satu sesi pengerjaan task (baris jadwal_task)."""

    id_jadwal: int
    id_task: int
    id_goal: int
    nama_task: str
    waktu_mulai: datetime
    waktu_selesai: datetime
    status: str  # terjadwal | selesai | dilewati


class JadwalMingguan(BaseModel):
    """Isi kalender satu minggu [mulai, akhir) — Senin 00:00 sampai Senin berikutnya."""

    mulai: datetime
    akhir: datetime
    jam_aktif_mulai: time
    jam_aktif_selesai: time
    kegiatan_rutin: list[BlokKalender]
    agenda: list[BlokKalender]
    sesi: list[SesiRead]


class TaskRingkas(BaseModel):
    id_task: int
    nama_task: str


class HasilPenjadwalanRead(BaseModel):
    """Hasil penjadwalan otomatis satu goal (FR-4)."""

    sesi_baru: list[SesiRead]
    # task yang tidak muat sebelum akhir minggu / deadline goal — tidak dijadwalkan sama sekali
    tidak_muat: list[TaskRingkas]


class SusunUlangRequest(BaseModel):
    # task yang hari ini ditunda karena mood (D7) — sesinya yang belum lewat hari ini dipindah mulai besok
    ditunda: list[int] = Field(default_factory=list)


class HasilSusunUlangRead(BaseModel):
    """Hasil penyusunan ulang jadwal minggu ini (FR-11)."""

    dipindah: list[TaskRingkas]  # task yang sesinya dijadwalkan ulang
    # tidak muat lagi minggu ini → user memilih konsekuensinya (D12)
    tidak_muat: list[TaskRingkas]
    sesi_baru: list[SesiRead]
    sesi_dilewati: list[SesiRead]  # sesi terlewat, kini berstatus `dilewati` (riwayat)


class SesiUpdate(BaseModel):
    """Ubah satu sesi: tandai selesai / batal selesai, dan/atau pindah waktu (keduanya wajib bersama)."""

    status: Optional[Literal["terjadwal", "selesai"]] = None
    waktu_mulai: Optional[datetime] = None
    waktu_selesai: Optional[datetime] = None

    @field_validator("waktu_mulai", "waktu_selesai")
    @classmethod
    def ke_wib(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is not None and value.tzinfo is not None:
            return value.astimezone(WIB).replace(tzinfo=None)
        return value

    @model_validator(mode="after")
    def cek_isian(self) -> "SesiUpdate":
        if (self.waktu_mulai is None) != (self.waktu_selesai is None):
            raise ValueError("waktu_mulai dan waktu_selesai harus diisi bersamaan")
        if self.waktu_mulai is not None and self.waktu_selesai <= self.waktu_mulai:
            raise ValueError("waktu_selesai harus setelah waktu_mulai")
        if self.status is None and self.waktu_mulai is None:
            raise ValueError("Tidak ada yang diubah")
        return self
