"""Unit tests untuk app/services/ai_service.py (OpenAI di-mock, tanpa API key)"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from openai import OpenAIError

from ai_model.mood_predictor import MODEL_PATH
from app.schemas.ai_decomposition import GoalDecomposition, GoalDecompositionRequest
from app.schemas.mood import MoodAnswers
from app.services import ai_service
from app.services.ai_service import AIServiceError, assess_mood, decompose_goal, recommend_tasks

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
