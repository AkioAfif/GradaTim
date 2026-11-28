"""Ekspor dataset model personalisasi (docs/AI.md §2). Arti tiap kolom: docs/KAMUS_DATA_DATASET.md.

Satu baris = satu sesi jadwal_task yang sudah berakhir. Semua sesi ikut (termasuk yang belum
dikonfirmasi dan sesi eksplorasi) agar tingkat konfirmasi bisa dilaporkan; untuk training, ambil
baris yang `label`-nya terisi.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.status import JADWAL_DILEWATI, JADWAL_SELESAI
from app.models import Goal, JadwalTask, Milestone, MoodQuestionnaire, Task

KOLOM_FITUR = [
    "jam_mulai",
    "hari",
    "durasi_menit",
    "jam_sebelum_mulai",
    "effort",
    "impact",
    "durasi_estimasi_task",
    "sisa_hari_deadline",
    "urutan_sesi_hari_itu",
    "jumlah_sesi_hari_itu",
    "riwayat_selesai",
    "riwayat_dilewati",
    "tingkat_selesai_riwayat",
]
# nomor_questionnaire 1..5 → nama kolom (urutan sama dengan MoodAnswers)
KOLOM_MOOD = ["mood_q1_fokus", "mood_q2_tenang", "mood_q3_motivasi", "mood_q4_tidur", "mood_q5_kesiapan"]
KOLOM = [
    "id_sesi",
    "user",
    "tanggal",
    "minggu",
    "status",
    "label",
    "dipindah",
    "eksplorasi",
    "fitur_versi",
    *KOLOM_FITUR,
    "mood_diisi",
    *KOLOM_MOOD,
]

_LABEL = {JADWAL_SELESAI: 1, JADWAL_DILEWATI: 0}


def baris_dataset(db: DbSession, sampai: datetime) -> list[dict[str, Any]]:
    """Semua sesi yang berakhir paling lambat `sampai`, urut waktu mulai.

    - user disamarkan (`u01`, `u02`, ... menurut id_user) agar dataset aman masuk lampiran laporan.
    - label: 1 = selesai, 0 = dilewati (dikonfirmasi user), None = belum dikonfirmasi.
    - fitur dari snapshot `jadwal_task.fitur`; kosong untuk sesi yang dibuat sebelum snapshot ada.
    - mood dari kuesioner hari yang sama, HANYA bila diisi sebelum sesi mulai (`diisi_pada`); selain itu
      mood_diisi = 0 dan kolom mood kosong — mencegah kebocoran informasi masa depan.
    """
    rows = db.execute(
        select(JadwalTask, Goal.id_user)
        .join(Task, JadwalTask.id_task == Task.id_task)
        .join(Milestone, Task.id_milestone == Milestone.id_milestone)
        .join(Goal, Milestone.id_goal == Goal.id_goal)
        .where(JadwalTask.waktu_selesai <= sampai)
        .order_by(JadwalTask.waktu_mulai, JadwalTask.id_jadwal)
    ).all()
    id_users = sorted({uid for _, uid in rows})
    kode_user = {uid: f"u{i:02d}" for i, uid in enumerate(id_users, start=1)}
    mood = {
        (m.id_user, m.tanggal): m
        for m in db.scalars(select(MoodQuestionnaire).where(MoodQuestionnaire.id_user.in_(id_users))).all()
    }

    hasil = []
    for sesi, uid in rows:
        fitur = sesi.fitur or {}
        m: Optional[MoodQuestionnaire] = mood.get((uid, sesi.waktu_mulai.date()))
        pakai_mood = m is not None and m.diisi_pada is not None and m.diisi_pada <= sesi.waktu_mulai
        jawaban = {a.nomor_questionnaire: a.nilai_jawaban for a in m.answers} if pakai_mood else {}
        hari = sesi.waktu_mulai.date()
        hasil.append({
            "id_sesi": sesi.id_jadwal,
            "user": kode_user[uid],
            "tanggal": hari.isoformat(),
            "minggu": (hari - timedelta(days=hari.weekday())).isoformat(),  # Senin; untuk split per waktu
            "status": sesi.status,
            "label": _LABEL.get(sesi.status),
            "dipindah": int(sesi.dipindah),
            "eksplorasi": int(sesi.eksplorasi),
            "fitur_versi": fitur.get("versi"),
            **{k: fitur.get(k) for k in KOLOM_FITUR},
            "mood_diisi": int(pakai_mood),
            **{kolom: jawaban.get(i) for i, kolom in enumerate(KOLOM_MOOD, start=1)},
        })
    return hasil


def _persen(bagian: int, total: int) -> Optional[float]:
    return round(100 * bagian / total, 1) if total else None


def ringkasan(baris: list[dict[str, Any]]) -> dict[str, Any]:
    """Angka yang dilaporkan bersama dataset (docs/AI.md §2): tingkat konfirmasi total & per user,
    porsi eksplorasi, sesi tanpa snapshot, dan porsi sesi dengan mood."""
    total = len(baris)
    terkonfirmasi = [b for b in baris if b["label"] is not None]
    per_user: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for b in baris:
        per_user[b["user"]].append(b)
    return {
        "sesi_berakhir": total,
        "selesai": sum(b["label"] == 1 for b in baris),
        "dilewati": sum(b["label"] == 0 for b in baris),
        "belum_dikonfirmasi": total - len(terkonfirmasi),
        "tingkat_konfirmasi_persen": _persen(len(terkonfirmasi), total),
        "eksplorasi": sum(b["eksplorasi"] for b in baris),
        "eksplorasi_persen": _persen(sum(b["eksplorasi"] for b in baris), total),
        "dipindah": sum(b["dipindah"] for b in baris),
        "tanpa_snapshot": sum(b["fitur_versi"] is None for b in baris),
        "dengan_mood_persen": _persen(sum(b["mood_diisi"] for b in baris), total),
        "per_user": {
            user: {
                "sesi_berakhir": len(bs),
                "terkonfirmasi": sum(b["label"] is not None for b in bs),
                "tingkat_konfirmasi_persen": _persen(sum(b["label"] is not None for b in bs), len(bs)),
            }
            for user, bs in sorted(per_user.items())
        },
    }
