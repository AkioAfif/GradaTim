"""Pydantic request/response schemas - jadwal.py (FR-4, FR-5, FR-11)"""

from datetime import datetime, time

from pydantic import BaseModel


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
    status: str  # terjadwal | selesai


class JadwalMingguan(BaseModel):
    """Isi kalender satu minggu [mulai, akhir) — Senin 00:00 sampai Senin berikutnya."""

    mulai: datetime
    akhir: datetime
    jam_aktif_mulai: time
    jam_aktif_selesai: time
    kegiatan_rutin: list[BlokKalender]
    agenda: list[BlokKalender]
    sesi: list[SesiRead]


class TaskTidakMuat(BaseModel):
    id_task: int
    nama_task: str


class HasilPenjadwalanRead(BaseModel):
    """Hasil penjadwalan otomatis satu goal (FR-4)."""

    sesi_baru: list[SesiRead]
    # task yang tidak muat sebelum akhir minggu / deadline goal — tidak dijadwalkan sama sekali
    tidak_muat: list[TaskTidakMuat]
