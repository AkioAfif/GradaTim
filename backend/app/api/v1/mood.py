"""FR-6, FR-7: Kuesioner mood harian

Satu hasil per user per hari (tanggal WIB): mengisi ulang di hari yang sama menimpa hasil sebelumnya.
Yang disimpan hanya jawaban + `hasil_akhir` (capacity_index); detail hasil dihitung ulang dari jawaban
karena model mood deterministik. Respons juga berisi rekomendasi task hari ini (app/services/mood_service.py).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core import waktu
from app.models import MoodQuestionnaire, QuestionnaireAnswer, User
from app.schemas.mood import (
    MoodAnswers,
    MoodAssessment,
    MoodHariIni,
    RekomendasiRead,
    SesiHariIni,
    TaskRekomendasi,
)
from app.services import ai_service, mood_service

router = APIRouter()


def _nilai_mood(answers: MoodAnswers):
    try:
        return ai_service.assess_mood(answers)
    except ai_service.AIServiceError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e


def _mood_hari_ini(db: Session, user: User) -> MoodQuestionnaire | None:
    return db.scalars(
        select(MoodQuestionnaire).where(
            MoodQuestionnaire.id_user == user.id_user, MoodQuestionnaire.tanggal == waktu.hari_ini()
        )
    ).first()


def _ke_task_rekomendasi(item: mood_service.TaskHariIni) -> TaskRekomendasi:
    t = item.task
    return TaskRekomendasi(
        id_task=t.id_task,
        id_goal=t.milestone.id_goal,
        nama_task=t.nama_task,
        tingkat_effort=t.tingkat_effort,
        tingkat_impact=t.tingkat_impact,
        deadline=t.deadline,
        sesi=[SesiHariIni(id_jadwal=s.id_jadwal, waktu_mulai=s.waktu_mulai, waktu_selesai=s.waktu_selesai)
              for s in item.sesi],
    )


def _respons(
    db: Session, user: User, baris: MoodQuestionnaire, jawaban: MoodAnswers, hasil: MoodAssessment
) -> MoodHariIni:
    rekomendasi = mood_service.rekomendasi_hari_ini(db, user, hasil, baris.tanggal)
    return MoodHariIni(
        id_questionnaire=baris.id_questionnaire,
        tanggal=baris.tanggal,
        jawaban=jawaban,
        hasil=hasil,
        rekomendasi=RekomendasiRead(
            direkomendasikan=[_ke_task_rekomendasi(i) for i in rekomendasi.direkomendasikan],
            disarankan_ditunda=[_ke_task_rekomendasi(i) for i in rekomendasi.disarankan_ditunda],
        ),
    )


def _jawaban_tersimpan(baris: MoodQuestionnaire) -> MoodAnswers:
    # nomor_questionnaire 1–5 = urutan MoodAnswers.as_list()
    nilai = {a.nomor_questionnaire: a.nilai_jawaban for a in baris.answers}
    return MoodAnswers(**{nama: nilai[i] for i, nama in enumerate(MoodAnswers.model_fields, start=1)})


@router.post("", response_model=MoodHariIni)
def isi_kuesioner_mood(
    payload: MoodAnswers,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MoodHariIni:
    """Isi kuesioner mood hari ini. Jika hari ini sudah diisi, hasil lama ditimpa."""
    hasil = _nilai_mood(payload)  # sebelum menulis apa pun: model gagal → tidak ada yang tersimpan

    baris = _mood_hari_ini(db, current_user)
    if baris is None:
        baris = MoodQuestionnaire(id_user=current_user.id_user, tanggal=waktu.hari_ini())
        db.add(baris)
    baris.hasil_akhir = hasil.capacity_index
    baris.answers = [
        QuestionnaireAnswer(nomor_questionnaire=i, nilai_jawaban=nilai)
        for i, nilai in enumerate(payload.as_list(), start=1)
    ]
    db.commit()
    db.refresh(baris)
    return _respons(db, current_user, baris, payload, hasil)


@router.get("/hari-ini", response_model=MoodHariIni)
def lihat_mood_hari_ini(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> MoodHariIni:
    baris = _mood_hari_ini(db, current_user)
    if baris is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kuesioner mood hari ini belum diisi")
    jawaban = _jawaban_tersimpan(baris)
    return _respons(db, current_user, baris, jawaban, _nilai_mood(jawaban))
