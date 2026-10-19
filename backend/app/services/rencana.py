"""Kerangka kalender rencana goal (D4, D11) — logika murni tanpa database & tanpa AI

Sistem yang menghitung tanggal; AI hanya mengisi judul & tujuan tiap target (dan task minggu ini).
    - Minggu = minggu kalender Senin–Minggu. Minggu ke-1 dimulai hari ini (bisa kurang dari 7 hari),
      minggu terakhir dipotong di deadline goal.
    - Bulan = bulan kalender. Minggu yang melintasi dua bulan masuk ke bulan yang memiliki hari
      terbanyak dari minggu itu (seri → bulan yang lebih awal).
Keputusan desain: docs/KEPUTUSAN_DESAIN_PENJADWALAN.md (D4, D11)
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta

NAMA_BULAN = (
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
)


@dataclass(frozen=True)
class MingguRencana:
    minggu_ke: int  # 1, 2, ... sepanjang goal
    mulai: date
    akhir: date  # inklusif

    @property
    def jumlah_hari(self) -> int:
        return (self.akhir - self.mulai).days + 1


@dataclass
class BulanRencana:
    bulan_ke: int  # 1, 2, ... sepanjang goal
    tahun: int
    bulan: int  # 1–12
    minggu: list[MingguRencana] = field(default_factory=list)

    @property
    def nama(self) -> str:
        return f"{NAMA_BULAN[self.bulan - 1]} {self.tahun}"


def daftar_minggu(hari_ini: date, deadline: date) -> list[MingguRencana]:
    """Minggu kalender dari hari ini sampai deadline (inklusif)."""
    if deadline < hari_ini:
        raise ValueError("Deadline sudah lewat")
    minggu = []
    mulai = hari_ini
    while mulai <= deadline:
        minggu_ini_akhir = mulai + timedelta(days=6 - mulai.weekday())  # Minggu
        akhir = min(minggu_ini_akhir, deadline)
        minggu.append(MingguRencana(len(minggu) + 1, mulai, akhir))
        mulai = minggu_ini_akhir + timedelta(days=1)
    return minggu


def _bulan_minggu(minggu: MingguRencana) -> tuple[int, int]:
    """(tahun, bulan) yang memiliki hari terbanyak dari minggu ini; seri → yang lebih awal."""
    hari = Counter((d.year, d.month) for d in (minggu.mulai + timedelta(days=i) for i in range(minggu.jumlah_hari)))
    return max(sorted(hari), key=lambda b: hari[b])  # max() mengambil yang pertama jika seri


def kerangka_rencana(hari_ini: date, deadline: date) -> list[BulanRencana]:
    """Minggu kalender dari hari ini sampai deadline, dikelompokkan per bulan kalender."""
    bulan: list[BulanRencana] = []
    for m in daftar_minggu(hari_ini, deadline):
        tahun, nomor_bulan = _bulan_minggu(m)
        if not bulan or (bulan[-1].tahun, bulan[-1].bulan) != (tahun, nomor_bulan):
            bulan.append(BulanRencana(len(bulan) + 1, tahun, nomor_bulan))
        bulan[-1].minggu.append(m)
    return bulan
