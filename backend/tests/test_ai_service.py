"""Unit tests untuk app/services/ai_service.py (OpenAI di-mock, tanpa API key)"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from openai import OpenAIError

from ai_model.mood_predictor import MODEL_PATH
from app.core import waktu
from app.schemas.ai_decomposition import GoalDecomposition, GoalDecompositionRequest, GoalPlan
from app.schemas.mood import MoodAnswers
from app.services import ai_service
from app.services.ai_service import AIServiceError, assess_mood, decompose_goal, recommend_tasks, rencanakan_goal

TODAY = date(2026, 10, 1)


def _task(title, day, minutes=30, effort="medium", impact="medium", number=0, deps=()):
    return {"task_number": number, "depends_on": list(deps), "task_title": title, "day_number": day,
            "estimated_minutes": minutes, "effort_level": effort, "impact_level": impact}


def _fake_client(parsed):
    client = MagicMock()
    message = SimpleNamespace(parsed=parsed)
    client.chat.completions.parse.return_value = SimpleNamespace(choices=[SimpleNamespace(message=message)])
    return client


def _request(deadline=date(2026, 10, 14), **kwargs):
    return GoalDecompositionRequest(judul_goal="Belajar Docker", deadline=deadline, **kwargs)


# ------------------------------------------------------------
# GOAL DECOMPOSITION
# ------------------------------------------------------------

def test_decompose_goal_normalizes_llm_output():
    raw = GoalDecomposition.model_validate({
        "goal_title": "Belajar Docker",
        "estimated_total_days": 99,
        "milestones": [
            {"milestone_title": "Lanjutan", "order": 5, "tasks": [_task("Compose", 30, minutes=999)]},
            {"milestone_title": "Kosong", "order": 2, "tasks": []},
            {"milestone_title": "Dasar", "order": 3, "tasks": [_task("Dockerfile", 2), _task("Install", 0, minutes=1)]},
        ],
    })

    result = decompose_goal(_request(), today=TODAY, client=_fake_client(raw))

    assert [m.milestone_title for m in result.milestones] == ["Dasar", "Lanjutan"]
    assert [m.order for m in result.milestones] == [1, 2]
    dasar, lanjutan = result.milestones
    assert [t.task_title for t in dasar.tasks] == ["Install", "Dockerfile"]  # diurutkan per hari
    assert dasar.tasks[0].day_number == 1
    assert dasar.tasks[0].estimated_minutes == ai_service.MIN_TASK_MINUTES
    assert lanjutan.tasks[0].day_number == 14  # di-clamp ke deadline (1-14 Okt)
    assert lanjutan.tasks[0].estimated_minutes == ai_service.MAX_TASK_MINUTES
    assert result.estimated_total_days == 14


def test_decompose_goal_normalizes_dependencies():
    raw = GoalDecomposition.model_validate({
        "goal_title": "x", "estimated_total_days": 3,
        "milestones": [{"milestone_title": "m", "order": 1, "tasks": [
            _task("Install", 1, number=10),
            _task("Konsep", 2, number=20, deps=[10, 99]),       # 99 tidak ada → dibuang
            _task("Praktik", 3, number=30, deps=[20, 30, 10]),  # diri sendiri → dibuang
            _task("Salah arah", 1, number=40, deps=[30]),       # prasyarat di hari lebih belakang → dibuang
        ]}],
    })
    tasks = decompose_goal(_request(), today=TODAY, client=_fake_client(raw)).milestones[0].tasks

    by_title = {t.task_title: t for t in tasks}
    assert [t.task_number for t in tasks] == [1, 2, 3, 4]  # dinomori ulang 1..N sesuai urutan
    assert by_title["Konsep"].depends_on == [by_title["Install"].task_number]
    assert by_title["Praktik"].depends_on == sorted([by_title["Install"].task_number, by_title["Konsep"].task_number])
    assert by_title["Salah arah"].depends_on == []


def test_decompose_goal_duplicate_task_numbers_drop_dependencies():
    raw = GoalDecomposition.model_validate({
        "goal_title": "x", "estimated_total_days": 2,
        "milestones": [{"milestone_title": "m", "order": 1, "tasks": [
            _task("A", 1, number=1), _task("B", 2, number=1, deps=[1]),
        ]}],
    })
    tasks = decompose_goal(_request(), today=TODAY, client=_fake_client(raw)).milestones[0].tasks
    assert [t.task_number for t in tasks] == [1, 2]
    assert tasks[1].depends_on == []


def test_decompose_goal_prompt_includes_constraints():
    raw = GoalDecomposition.model_validate({
        "goal_title": "x", "estimated_total_days": 1,
        "milestones": [{"milestone_title": "m", "order": 1, "tasks": [_task("t", 1)]}],
    })
    client = _fake_client(raw)

    decompose_goal(_request(menit_harian=90), today=TODAY, client=client)

    kwargs = client.chat.completions.parse.call_args.kwargs
    assert kwargs["response_format"] is GoalDecomposition
    user_prompt = kwargs["messages"][1]["content"]
    assert "14 hari tersedia" in user_prompt
    assert "90 menit per hari" in user_prompt


def test_decompose_goal_deadline_today_is_one_day():
    raw = GoalDecomposition.model_validate({
        "goal_title": "x", "estimated_total_days": 3,
        "milestones": [{"milestone_title": "m", "order": 1, "tasks": [_task("t", 3)]}],
    })
    result = decompose_goal(_request(deadline=TODAY), today=TODAY, client=_fake_client(raw))
    assert result.milestones[0].tasks[0].day_number == 1


def test_decompose_goal_default_today_pakai_tanggal_wib(monkeypatch):
    raw = GoalDecomposition.model_validate({
        "goal_title": "x", "estimated_total_days": 1,
        "milestones": [{"milestone_title": "m", "order": 1, "tasks": [_task("t", 1)]}],
    })
    monkeypatch.setattr(waktu, "hari_ini", lambda: TODAY)
    client = _fake_client(raw)
    decompose_goal(_request(), client=client)

    user_prompt = client.chat.completions.parse.call_args.kwargs["messages"][1]["content"]
    assert f"Tanggal hari ini: {TODAY.isoformat()}" in user_prompt


def test_decompose_goal_rejects_past_deadline():
    client = _fake_client(None)
    with pytest.raises(AIServiceError, match="Deadline"):
        decompose_goal(_request(deadline=date(2026, 9, 30)), today=TODAY, client=client)
    client.chat.completions.parse.assert_not_called()


def test_decompose_goal_refusal_raises():
    with pytest.raises(AIServiceError):
        decompose_goal(_request(), today=TODAY, client=_fake_client(None))


def test_decompose_goal_all_milestones_empty_raises():
    raw = GoalDecomposition.model_validate({
        "goal_title": "x", "estimated_total_days": 1,
        "milestones": [{"milestone_title": "m", "order": 1, "tasks": []}],
    })
    with pytest.raises(AIServiceError, match="tidak menghasilkan task"):
        decompose_goal(_request(), today=TODAY, client=_fake_client(raw))


def test_decompose_goal_wraps_api_error():
    client = MagicMock()
    client.chat.completions.parse.side_effect = OpenAIError("boom")
    with pytest.raises(AIServiceError, match="tidak tersedia"):
        decompose_goal(_request(), today=TODAY, client=client)


def test_decompose_goal_without_api_key(monkeypatch):
    monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", None)
    with pytest.raises(AIServiceError, match="LLM_API_KEY"):
        decompose_goal(_request(), today=TODAY)


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
