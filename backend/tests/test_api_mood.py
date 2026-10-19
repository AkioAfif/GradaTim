"""Test endpoint /api/v1/mood (kuesioner mood harian, FR-6 & FR-7). Model mood asli, tanpa LLM."""

from datetime import timedelta

import pytest

from app.core import waktu
from app.models import MoodQuestionnaire, QuestionnaireAnswer
from app.schemas.mood import MoodAnswers
from app.services import ai_service

URL = "/api/v1/mood"


def jawaban(q1=3, q2=3, q3=3, q4=3, q5=3):
    return {"q1_focus": q1, "q2_calm": q2, "q3_motivated": q3, "q4_sleep": q4, "q5_readiness": q5}


def isi(client, headers, **kwargs):
    res = client.post(URL, json=jawaban(**kwargs), headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def test_tanpa_token_401(client):
    assert client.post(URL, json=jawaban()).status_code == 401
    assert client.get(f"{URL}/hari-ini").status_code == 401


def test_isi_kuesioner_menyimpan_jawaban_dan_hasil(client, db, auth_headers, hari_ini_beku):
    body = isi(client, auth_headers(), q1=5, q2=4, q3=3, q4=2, q5=1)

    harapan = ai_service.assess_mood(MoodAnswers(**jawaban(5, 4, 3, 2, 1)))
    assert body["tanggal"] == hari_ini_beku.isoformat()
    assert body["jawaban"] == jawaban(5, 4, 3, 2, 1)
    assert body["hasil"] == harapan.model_dump()

    baris = db.get(MoodQuestionnaire, body["id_questionnaire"])
    assert (baris.tanggal, baris.hasil_akhir) == (hari_ini_beku, harapan.capacity_index)
    assert sorted((a.nomor_questionnaire, a.nilai_jawaban) for a in baris.answers) == [
        (1, 5), (2, 4), (3, 3), (4, 2), (5, 1)
    ]


@pytest.mark.parametrize("nilai, level", [(1, "LOW"), (5, "HIGH")])
def test_level_kapasitas_ekstrem(client, auth_headers, hari_ini_beku, nilai, level):
    body = isi(client, auth_headers(), q1=nilai, q2=nilai, q3=nilai, q4=nilai, q5=nilai)
    assert body["hasil"]["capacity_level"] == level


def test_isi_ulang_hari_yang_sama_menimpa(client, db, auth_headers, hari_ini_beku):
    headers = auth_headers()
    pertama = isi(client, headers, q1=1, q2=1, q3=1, q4=1, q5=1)
    kedua = isi(client, headers, q1=5, q2=5, q3=5, q4=5, q5=5)

    assert kedua["id_questionnaire"] == pertama["id_questionnaire"]
    assert db.query(MoodQuestionnaire).count() == 1
    assert sorted(a.nilai_jawaban for a in db.query(QuestionnaireAnswer)) == [5] * 5  # jawaban lama terhapus
    assert db.get(MoodQuestionnaire, kedua["id_questionnaire"]).hasil_akhir == kedua["hasil"]["capacity_index"]


def test_hari_berbeda_baris_baru(client, db, auth_headers, monkeypatch, hari_ini_beku):
    headers = auth_headers()
    kemarin = isi(client, headers)
    monkeypatch.setattr(waktu, "hari_ini", lambda: hari_ini_beku + timedelta(days=1))
    besok = isi(client, headers)

    assert besok["id_questionnaire"] != kemarin["id_questionnaire"]
    assert besok["tanggal"] == (hari_ini_beku + timedelta(days=1)).isoformat()
    assert db.query(MoodQuestionnaire).count() == 2


def test_lihat_hari_ini(client, auth_headers, hari_ini_beku):
    headers = auth_headers()
    assert client.get(f"{URL}/hari-ini", headers=headers).status_code == 404

    disimpan = isi(client, headers, q1=2, q2=3, q3=4, q4=5, q5=1)
    res = client.get(f"{URL}/hari-ini", headers=headers)
    assert res.status_code == 200
    assert res.json() == disimpan  # hasil dihitung ulang dari jawaban tersimpan = hasil saat diisi


def test_lihat_hari_ini_hanya_hari_ini(client, auth_headers, monkeypatch, hari_ini_beku):
    headers = auth_headers()
    isi(client, headers)
    monkeypatch.setattr(waktu, "hari_ini", lambda: hari_ini_beku + timedelta(days=1))
    assert client.get(f"{URL}/hari-ini", headers=headers).status_code == 404


def test_mood_user_lain_tidak_terlihat_dan_tidak_tertimpa(client, db, auth_headers, hari_ini_beku):
    user_a, user_b = auth_headers(), auth_headers()
    a = isi(client, user_a, q1=1, q2=1, q3=1, q4=1, q5=1)

    assert client.get(f"{URL}/hari-ini", headers=user_b).status_code == 404
    b = isi(client, user_b, q1=5, q2=5, q3=5, q4=5, q5=5)
    assert b["id_questionnaire"] != a["id_questionnaire"]
    assert client.get(f"{URL}/hari-ini", headers=user_a).json() == a


@pytest.mark.parametrize("salah", [{"q1_focus": 0}, {"q5_readiness": 6}, {"q3_motivated": None}])
def test_jawaban_tidak_valid_422(client, db, auth_headers, salah):
    res = client.post(URL, json={**jawaban(), **salah}, headers=auth_headers())
    assert res.status_code == 422
    assert db.query(MoodQuestionnaire).count() == 0


def test_model_mood_tidak_tersedia_503_tanpa_menyimpan(client, db, auth_headers, monkeypatch, hari_ini_beku):
    def _gagal(answers):
        raise ai_service.AIServiceError("Model mood belum tersedia di server.")

    monkeypatch.setattr(ai_service, "assess_mood", _gagal)
    res = client.post(URL, json=jawaban(), headers=auth_headers())
    assert res.status_code == 503 and res.json()["detail"] == "Model mood belum tersedia di server."
    assert db.query(MoodQuestionnaire).count() == 0
