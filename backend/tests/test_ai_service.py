"""Unit tests untuk app/services/ai_service.py (OpenAI di-mock, tanpa API key)"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from openai import OpenAIError

from ai_model.mood_predictor import MODEL_PATH
from app.core import waktu
from app.schemas.ai_decomposition import (
    GoalDecompositionRequest,
    GoalPlan,
    ProgresTask,
    RincianMingguRequest,
    TargetMinggu,
    WeekTasks,
)
from app.schemas.mood import MoodAnswers
from app.services import ai_service
from app.services.ai_service import AIServiceError, assess_mood, recommend_tasks, rencanakan_goal, rinci_minggu


def _fake_client(parsed):
    client = MagicMock()
    message = SimpleNamespace(parsed=parsed)
    client.chat.completions.parse.return_value = SimpleNamespace(choices=[SimpleNamespace(message=message)])
    return client


# ------------------------------------------------------------
# RENCANA BULANAN → MINGGUAN (D4, D11)
# ------------------------------------------------------------

RABU = date(2026, 10, 21)


def _ptask(title, number, minutes=30, deps=()):
    return {"task_number": number, "depends_on": list(deps), "task_title": title, "estimated_minutes": minutes,
            "effort_level": "medium", "impact_level": "high"}


def _target(number, title, description="Hasil"):
    return {"number": number, "title": title, "description": description}


def _plan(months=None, weeks=None, tasks=None):
    return GoalPlan.model_validate({
        "goal_title": "Belajar Docker",
        "months": months if months is not None else [_target(1, "Dasar Docker"), _target(2, "Docker lanjutan")],
        "weeks": weeks if weeks is not None else [_target(n, f"Minggu {n}") for n in range(1, 5)],
        "first_week_tasks": tasks if tasks is not None else [_ptask("Install Docker", 1)],
    })


def _rencana_request(deadline=date(2026, 11, 10), **kwargs):  # Rabu 21 Okt → Selasa 10 Nov: 4 minggu, 2 bulan
    return GoalDecompositionRequest(judul_goal="Belajar Docker", deadline=deadline, **kwargs)


def _prompt(client):
    return client.chat.completions.parse.call_args.kwargs["messages"][1]["content"]


def test_rencanakan_goal_menempel_judul_ke_kerangka():
    hasil = rencanakan_goal(_rencana_request(), today=RABU, client=_fake_client(_plan()))

    assert [(b.bulan_ke, b.tahun, b.bulan, b.judul) for b in hasil.bulan] == [
        (1, 2026, 10, "Dasar Docker"), (2, 2026, 11, "Docker lanjutan")
    ]
    oktober, november = hasil.bulan
    assert [(m.minggu_ke, m.mulai, m.akhir, m.judul) for m in oktober.minggu] == [
        (1, date(2026, 10, 21), date(2026, 10, 25), "Minggu 1"),
        (2, date(2026, 10, 26), date(2026, 11, 1), "Minggu 2"),
    ]
    assert [(m.minggu_ke, m.akhir) for m in november.minggu] == [(3, date(2026, 11, 8)), (4, date(2026, 11, 10))]
    assert [t.task_title for t in hasil.task_minggu_ini] == ["Install Docker"]


def test_rencanakan_goal_prompt_berisi_kerangka_dan_batas_menit():
    client = _fake_client(_plan())
    rencanakan_goal(_rencana_request(menit_harian=60), today=RABU, client=client)

    prompt = _prompt(client)
    assert "Bulan 1 — Oktober 2026" in prompt and "Bulan 2 — November 2026" in prompt
    assert "Minggu 1: 21 Okt 2026 – 25 Okt 2026 (5 hari)" in prompt
    assert "Minggu 4: 9 Nov 2026 – 10 Nov 2026 (2 hari)" in prompt
    assert "Minggu ke-1 hanya 5 hari" in prompt
    assert "tidak boleh melebihi 300 menit" in prompt  # 60 menit × 5 hari
    assert client.chat.completions.parse.call_args.kwargs["response_format"] is GoalPlan


def test_rencanakan_goal_tanpa_menit_harian_tidak_ada_batas():
    client = _fake_client(_plan())
    rencanakan_goal(_rencana_request(), today=RABU, client=client)
    assert "menit per hari" not in _prompt(client)


def test_rencanakan_goal_target_hilang_diberi_judul_cadangan_dan_nomor_asing_dibuang():
    plan = _plan(
        months=[_target(2, "  "), _target(9, "Bulan asing")],
        weeks=[_target(1, "Pertama"), _target(1, "Duplikat"), _target(3, " Ketiga "), _target(7, "Asing")],
    )
    hasil = rencanakan_goal(_rencana_request(), today=RABU, client=_fake_client(plan))

    assert [b.judul for b in hasil.bulan] == ["Target Oktober 2026", "Target November 2026"]
    assert [(m.judul, m.deskripsi) for b in hasil.bulan for m in b.minggu] == [
        ("Pertama", "Hasil"), ("Target minggu ke-2", ""), ("Ketiga", "Hasil"), ("Target minggu ke-4", "")
    ]


def test_rencanakan_goal_normalisasi_task():
    tasks = [
        _ptask("Compose", 30, minutes=999, deps=[10, 30, 99]),  # diri sendiri & nomor asing dibuang
        _ptask("Install", 10, minutes=1),
        _ptask("Image", 20, deps=[30, 10]),  # menunjuk task yang lebih belakang → dibuang
    ]
    hasil = rencanakan_goal(_rencana_request(), today=RABU, client=_fake_client(_plan(tasks=tasks)))

    assert [(t.task_number, t.task_title, t.depends_on) for t in hasil.task_minggu_ini] == [
        (1, "Install", []), (2, "Image", [1]), (3, "Compose", [1])
    ]
    assert hasil.task_minggu_ini[0].estimated_minutes == ai_service.MIN_TASK_MINUTES
    assert hasil.task_minggu_ini[2].estimated_minutes == ai_service.MAX_TASK_MINUTES


def test_rencanakan_goal_nomor_task_duplikat_dependensi_dibuang():
    tasks = [_ptask("A", 1), _ptask("B", 1, deps=[1])]
    hasil = rencanakan_goal(_rencana_request(), today=RABU, client=_fake_client(_plan(tasks=tasks)))
    assert [(t.task_number, t.depends_on) for t in hasil.task_minggu_ini] == [(1, []), (2, [])]


def test_rencanakan_goal_tanpa_task_error():
    with pytest.raises(AIServiceError, match="tidak menghasilkan task"):
        rencanakan_goal(_rencana_request(), today=RABU, client=_fake_client(_plan(tasks=[])))


def test_rencanakan_goal_deadline_hari_ini_satu_minggu():
    plan = _plan(months=[_target(1, "Kilat")], weeks=[_target(1, "Hari ini")])
    hasil = rencanakan_goal(_rencana_request(deadline=RABU), today=RABU, client=_fake_client(plan))
    assert [[(m.mulai, m.akhir) for m in b.minggu] for b in hasil.bulan] == [[(RABU, RABU)]]


def test_rencanakan_goal_deadline_lewat_tanpa_memanggil_ai():
    client = _fake_client(None)
    with pytest.raises(AIServiceError, match="Deadline"):
        rencanakan_goal(_rencana_request(deadline=date(2026, 10, 20)), today=RABU, client=client)
    client.chat.completions.parse.assert_not_called()


def test_rencanakan_goal_default_today_pakai_tanggal_wib(monkeypatch):
    monkeypatch.setattr(waktu, "hari_ini", lambda: RABU)
    client = _fake_client(_plan())
    rencanakan_goal(_rencana_request(), client=client)
    assert "Tanggal hari ini: 2026-10-21" in _prompt(client)


def test_rencanakan_goal_refusal_dan_error_api():
    with pytest.raises(AIServiceError, match="tidak bisa memproses"):
        rencanakan_goal(_rencana_request(), today=RABU, client=_fake_client(None))
    client = MagicMock()
    client.chat.completions.parse.side_effect = OpenAIError("boom")
    with pytest.raises(AIServiceError, match="tidak tersedia"):
        rencanakan_goal(_rencana_request(), today=RABU, client=client)



def test_rencanakan_goal_tanpa_api_key(monkeypatch):
    monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", None)
    with pytest.raises(AIServiceError, match="LLM_API_KEY"):
        rencanakan_goal(_rencana_request(), today=RABU)

# ------------------------------------------------------------
# RINCIAN TASK PER MINGGU (D11)
# ------------------------------------------------------------

MINGGU_2 = TargetMinggu(minggu_ke=2, mulai=date(2026, 10, 26), akhir=date(2026, 11, 1),
                        judul="Kuasai docker compose", deskripsi="Bisa menjalankan app + database")
MINGGU_3 = TargetMinggu(minggu_ke=3, mulai=date(2026, 11, 2), akhir=date(2026, 11, 8),
                        judul="Deploy ke server", deskripsi="")


def _rincian(**kwargs):
    data = {"judul_goal": "Belajar Docker", "deadline_goal": date(2026, 11, 10), "target": MINGGU_2,
            "target_berikutnya": MINGGU_3, **kwargs}
    return RincianMingguRequest(**data)


def _week(tasks):
    return WeekTasks.model_validate({"tasks": tasks})


def test_rinci_minggu_prompt_berisi_target_progres_dan_konteks():
    client = _fake_client(_week([_ptask("Tulis compose.yml", 1)]))
    progres = [ProgresTask(minggu_ke=1, judul="Install Docker", menit=30, selesai=True),
               ProgresTask(minggu_ke=1, judul="Buat Dockerfile", menit=60, selesai=False)]

    hasil = rinci_minggu(_rincian(progres=progres), today=date(2026, 10, 24), client=client)  # Sabtu sebelumnya

    assert [t.task_title for t in hasil] == ["Tulis compose.yml"]
    prompt = _prompt(client)
    assert "Target minggu ke-2 (26 Okt 2026 – 1 Nov 2026): Kuasai docker compose" in prompt
    assert "Hasil yang ingin dicapai: Bisa menjalankan app + database" in prompt
    assert "Sisa waktu minggu ini: 7 hari" in prompt  # minggu depan dirinci lebih awal: seminggu penuh
    assert "Target minggu berikutnya (JANGAN dikerjakan sekarang): Deploy ke server" in prompt
    assert "- [x] Minggu 1: Install Docker (30 menit)" in prompt
    assert "- [ ] Minggu 1: Buat Dockerfile (60 menit)" in prompt
    assert "Selesai 1 dari 2 task." in prompt
    assert "menit per hari" not in prompt
    kwargs = client.chat.completions.parse.call_args.kwargs
    assert kwargs["response_format"] is WeekTasks
    assert kwargs["messages"][0]["content"] == ai_service.WEEK_SYSTEM_PROMPT


def test_rinci_minggu_minggu_berjalan_hanya_sisa_hari_dan_batas_menit_dikurangi_task_lama():
    client = _fake_client(_week([_ptask("A", 1)]))
    progres = [ProgresTask(minggu_ke=1, judul="Buat Dockerfile", menit=60, selesai=False),
               ProgresTask(minggu_ke=1, judul="Tanpa estimasi", selesai=False)]

    rinci_minggu(_rincian(progres=progres, menit_harian=60), today=date(2026, 10, 29), client=client)  # Kamis

    prompt = _prompt(client)
    assert "Sisa waktu minggu ini: 4 hari (29 Okt 2026 – 1 Nov 2026)" in prompt
    assert "tidak boleh melebihi 180 menit" in prompt  # 60 × 4 hari − 60 menit task lama


def test_rinci_minggu_tanpa_progres_dan_tanpa_task_lama():
    client = _fake_client(_week([_ptask("A", 1)]))
    rinci_minggu(_rincian(menit_harian=30), today=date(2026, 10, 26), client=client)
    prompt = _prompt(client)
    assert "(belum ada task sebelumnya)" in prompt
    assert "tidak boleh melebihi 210 menit" in prompt


def test_rinci_minggu_waktu_habis_oleh_task_lama():
    client = _fake_client(_week([_ptask("A", 1)]))
    progres = [ProgresTask(minggu_ke=1, judul="Besar", menit=240, selesai=False)]
    rinci_minggu(_rincian(progres=progres, menit_harian=60), today=date(2026, 10, 30), client=client)  # 3 hari
    assert "buat 1 task ringan saja" in _prompt(client)


def test_rinci_minggu_normalisasi_task():
    tasks = [_ptask("B", 5, minutes=500, deps=[3, 5]), _ptask("A", 3, minutes=1, deps=[5])]
    hasil = rinci_minggu(_rincian(), today=date(2026, 10, 26), client=_fake_client(_week(tasks)))
    assert [(t.task_number, t.task_title, t.depends_on, t.estimated_minutes) for t in hasil] == [
        (1, "A", [], ai_service.MIN_TASK_MINUTES), (2, "B", [1], ai_service.MAX_TASK_MINUTES)
    ]


def test_rinci_minggu_tanpa_task_error():
    with pytest.raises(AIServiceError, match="tidak menghasilkan task"):
        rinci_minggu(_rincian(), today=date(2026, 10, 26), client=_fake_client(_week([])))


def test_rinci_minggu_minggu_lewat_tanpa_memanggil_ai():
    client = _fake_client(None)
    with pytest.raises(AIServiceError, match="sudah lewat"):
        rinci_minggu(_rincian(), today=date(2026, 11, 2), client=client)
    client.chat.completions.parse.assert_not_called()


def test_rinci_minggu_default_today_dan_error_api(monkeypatch):
    monkeypatch.setattr(waktu, "hari_ini", lambda: date(2026, 10, 31))
    client = _fake_client(_week([_ptask("A", 1)]))
    rinci_minggu(_rincian(), client=client)
    assert "Sisa waktu minggu ini: 2 hari" in _prompt(client)

    client = MagicMock()
    client.chat.completions.parse.side_effect = OpenAIError("boom")
    with pytest.raises(AIServiceError, match="tidak tersedia"):
        rinci_minggu(_rincian(), today=date(2026, 10, 26), client=client)


# ------------------------------------------------------------
# MOOD CAPACITY
# ------------------------------------------------------------

def test_mood_answers_validation():
    with pytest.raises(ValueError):
        MoodAnswers(q1_focus=0, q2_calm=3, q3_motivated=3, q4_sleep=3, q5_readiness=6)


@pytest.mark.skipif(not MODEL_PATH.exists(), reason="Model belum ditraining (python ai_model/train_model.py)")
@pytest.mark.parametrize("score, expected", [(1, "LOW"), (3, "MEDIUM"), (5, "HIGH")])
def test_assess_mood(score, expected):
    answers = MoodAnswers(q1_focus=score, q2_calm=score, q3_motivated=score, q4_sleep=score, q5_readiness=score)
    result = assess_mood(answers)
    assert result.capacity_level == expected
    assert result.total_mood_score == score * 5
    assert abs(sum(result.probabilities.model_dump().values()) - 1) < 1e-3


def test_assess_mood_model_missing(monkeypatch):
    def missing(_answers):
        raise FileNotFoundError("no model")
    monkeypatch.setattr(ai_service, "predict_capacity", missing)
    answers = MoodAnswers(q1_focus=3, q2_calm=3, q3_motivated=3, q4_sleep=3, q5_readiness=3)
    with pytest.raises(AIServiceError, match="Model mood"):
        assess_mood(answers)


def test_recommend_tasks_low_capacity_prefers_light_high_impact():
    tasks = [
        {"id": "berat", "effort_level": "high", "impact_level": "high"},
        {"id": "ringan-penting", "effort_level": "low", "impact_level": "high"},
        {"id": "ringan-remeh", "effort_level": "low", "impact_level": "low"},
        {"id": "tanpa-label"},  # dianggap medium/medium
    ]
    low = SimpleNamespace(capacity_level="LOW", max_tasks=2)
    high = SimpleNamespace(capacity_level="HIGH", max_tasks=6)

    assert [t["id"] for t in recommend_tasks(tasks, low)] == ["ringan-penting", "berat"]
    assert recommend_tasks(tasks, high)[0]["id"] == "berat"
    assert len(recommend_tasks(tasks, high)) == 4


def _rec(number, day, effort="medium", impact="medium", deps=(), status="pending"):
    return {"task_number": number, "day_number": day, "effort_level": effort, "impact_level": impact,
            "depends_on": list(deps), "status": status}


def test_recommend_tasks_respects_dependencies():
    install = _rec(1, 1, effort="medium", impact="high")
    hello = _rec(2, 3, effort="low", impact="high", deps=[1])  # skor mood LOW lebih tinggi dari install
    low = SimpleNamespace(capacity_level="LOW", max_tasks=2)

    result = recommend_tasks([hello, install], low, today_day=1)

    assert [t["task_number"] for t in result] == [1, 2]  # prasyarat selalu duluan


def test_recommend_tasks_blocked_task_not_recommended():
    tasks = [_rec(1, 1, deps=[]), _rec(2, 2, deps=[1]), _rec(3, 3, deps=[2])]
    low = SimpleNamespace(capacity_level="LOW", max_tasks=1)
    assert [t["task_number"] for t in recommend_tasks(tasks, low)] == [1]


def test_recommend_tasks_skips_done_and_unlocks_dependents():
    tasks = [_rec(1, 1, status="done"), _rec(2, 2, deps=[1]), _rec(3, 9)]
    medium = SimpleNamespace(capacity_level="MEDIUM", max_tasks=4)
    assert [t["task_number"] for t in recommend_tasks(tasks, medium, today_day=2)] == [2, 3]


def test_recommend_tasks_urgency_beats_small_mood_difference():
    overdue = _rec(1, 1, effort="medium", impact="medium")
    later = _rec(2, 10, effort="low", impact="high")  # lebih cocok untuk mood LOW, tapi masih jauh
    low = SimpleNamespace(capacity_level="LOW", max_tasks=1)
    assert recommend_tasks([later, overdue], low, today_day=3)[0]["task_number"] == 1
