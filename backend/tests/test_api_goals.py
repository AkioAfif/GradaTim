"""Tes API goal: CRUD + dekomposisi AI (FR-1, FR-2). LLM selalu di-mock."""

import ast
import pathlib
from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.models.goal import Goal
from app.models.jadwal_task import JadwalTask
from app.models.milestone import Milestone
from app.models.task import Task
from app.models.task_dependency import TaskDependency
from app.models.user import User
from app.schemas.ai_decomposition import GoalDecomposition
from app.services import ai_service, goal_service, scheduler

URL = "/api/v1/goals"
URL_RUTIN = "/api/v1/time-constraints"
HARI_INI = date(2026, 10, 5)


@pytest.fixture(autouse=True)
def _hari_ini(hari_ini_beku):
    assert hari_ini_beku == HARI_INI


def _hasil_ai() -> GoalDecomposition:
    """2 milestone, 5 task, dependensi campuran (termasuk duplikat, diri sendiri, dan nomor tak dikenal)."""
    return GoalDecomposition.model_validate({
        "goal_title": "Judul dari AI (tidak dipakai)",
        "estimated_total_days": 6,
        "milestones": [
            {"milestone_title": "Persiapan", "order": 1, "tasks": [
                {"task_number": 1, "depends_on": [], "task_title": "Install Docker", "day_number": 1,
                 "estimated_minutes": 30, "effort_level": "low", "impact_level": "high"},
                {"task_number": 2, "depends_on": [1], "task_title": "Baca dokumentasi", "day_number": 2,
                 "estimated_minutes": 60, "effort_level": "medium", "impact_level": "medium"},
                {"task_number": 3, "depends_on": [1, 1, 3, 99], "task_title": "Tulis Dockerfile", "day_number": 2,
                 "estimated_minutes": 45, "effort_level": "high", "impact_level": "low"},
            ]},
            {"milestone_title": "Eksekusi", "order": 2, "tasks": [
                {"task_number": 4, "depends_on": [2, 3], "task_title": "Deploy container", "day_number": 4,
                 "estimated_minutes": 90, "effort_level": "high", "impact_level": "high"},
                {"task_number": 5, "depends_on": [], "task_title": "Tulis catatan", "day_number": 6,
                 "estimated_minutes": 20, "effort_level": "low", "impact_level": "low"},
            ]},
        ],
    })


def _hasil_ai_kecil() -> GoalDecomposition:
    return GoalDecomposition.model_validate({
        "goal_title": "x", "estimated_total_days": 2,
        "milestones": [{"milestone_title": "Ulang", "order": 1, "tasks": [
            {"task_number": 1, "depends_on": [], "task_title": "Langkah A", "day_number": 1,
             "estimated_minutes": 30, "effort_level": "low", "impact_level": "low"},
            {"task_number": 2, "depends_on": [1], "task_title": "Langkah B", "day_number": 2,
             "estimated_minutes": 30, "effort_level": "low", "impact_level": "low"},
        ]}],
    })


class MockAI:
    def __init__(self):
        self.hasil = _hasil_ai()
        self.error: Exception | None = None
        self.panggilan: list[tuple] = []  # (request, today)

    def __call__(self, request, today=None, client=None):
        self.panggilan.append((request, today))
        if self.error is not None:
            raise self.error
        return self.hasil.model_copy(deep=True)


@pytest.fixture
def ai(monkeypatch) -> MockAI:
    mock = MockAI()
    monkeypatch.setattr(ai_service, "decompose_goal", mock)
    return mock


def _goal(**override):
    data = {"judul_goal": "Belajar Docker", "deskripsi": "Sampai bisa deploy", "deadline": "2026-10-31"}
    data.update(override)
    return data


def _buat(client, headers, **override):
    r = client.post(URL, json=_goal(**override), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _hitung(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def _akhir(hari_ke: int) -> str:
    return datetime.combine(HARI_INI + timedelta(days=hari_ke - 1), time(23, 59)).isoformat()


# ---------- CRUD ----------

def test_crud_goal(client, auth_headers):
    h = auth_headers()

    dibuat = _buat(client, h, judul_goal="  Belajar Docker  ")
    assert dibuat == {
        "id_goal": dibuat["id_goal"],
        "judul_goal": "Belajar Docker",
        "deskripsi": "Sampai bisa deploy",
        "deadline": "2026-10-31T23:59:00",
        "status": "active",
    }
    path = f"{URL}/{dibuat['id_goal']}"

    r = client.get(path, headers=h)
    assert r.status_code == 200
    assert r.json() == {**dibuat, "milestones": []}

    r = client.patch(path, json={"judul_goal": "Kuasai Docker", "deadline": "2026-11-15"}, headers=h)
    assert r.status_code == 200
    assert r.json()["judul_goal"] == "Kuasai Docker"
    assert r.json()["deadline"] == "2026-11-15T23:59:00"
    assert r.json()["deskripsi"] == "Sampai bisa deploy"

    r = client.patch(path, json={"deskripsi": None}, headers=h)
    assert r.status_code == 200 and r.json()["deskripsi"] is None

    assert client.delete(path, headers=h).status_code == 204
    assert client.get(path, headers=h).status_code == 404


def test_list_goal_terbaru_dulu(client, auth_headers):
    h = auth_headers()
    ids = [_buat(client, h, judul_goal=f"Goal {i}")["id_goal"] for i in range(3)]
    assert [g["id_goal"] for g in client.get(URL, headers=h).json()] == ids[::-1]


def test_deadline_hari_ini_diterima(client, auth_headers):
    assert _buat(client, auth_headers(), deadline="2026-10-05")["deadline"] == "2026-10-05T23:59:00"


@pytest.mark.parametrize("override", [
    {"deadline": "2026-10-04"},
    {"deadline": None},
    {"judul_goal": "ab"},
    {"judul_goal": "   abc   " * 40},
    {"deskripsi": "x" * 2001},
])
def test_create_tidak_valid_422(client, auth_headers, override):
    body = _goal(**override)
    assert client.post(URL, json=body, headers=auth_headers()).status_code == 422


def test_create_tanpa_deadline_422(client, auth_headers):
    assert client.post(URL, json={"judul_goal": "Belajar Docker"}, headers=auth_headers()).status_code == 422


def test_deadline_lampau_pesan_bahasa_indonesia(client, auth_headers):
    r = client.post(URL, json=_goal(deadline="2026-10-01"), headers=auth_headers())
    assert "Deadline tidak boleh di masa lalu" in r.text


@pytest.mark.parametrize("body", [
    {"deadline": "2026-10-01"}, {"deadline": None}, {"judul_goal": None}, {"judul_goal": "x"},
])
def test_patch_tidak_valid_422(client, auth_headers, body):
    h = auth_headers()
    dibuat = _buat(client, h)
    assert client.patch(f"{URL}/{dibuat['id_goal']}", json=body, headers=h).status_code == 422


def test_patch_status_diabaikan(client, auth_headers):
    h = auth_headers()
    dibuat = _buat(client, h)
    r = client.patch(f"{URL}/{dibuat['id_goal']}", json={"status": "selesai"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "active"


@pytest.mark.parametrize("method, path", [
    ("get", URL), ("post", URL), ("get", f"{URL}/1"), ("patch", f"{URL}/1"), ("delete", f"{URL}/1"),
    ("post", f"{URL}/1/decompose"),
])
def test_tanpa_token_401(client, method, path):
    kwargs = {"json": _goal()} if method in ("post", "patch") else {}
    assert getattr(client, method)(path, **kwargs).status_code == 401


def test_isolasi_antar_user_404(client, auth_headers, ai):
    a, b = auth_headers(), auth_headers()
    milik_a = _buat(client, a)
    path = f"{URL}/{milik_a['id_goal']}"

    assert client.get(path, headers=b).status_code == 404
    assert client.patch(path, json={"judul_goal": "Dibajak"}, headers=b).status_code == 404
    assert client.delete(path, headers=b).status_code == 404
    assert client.post(f"{path}/decompose", headers=b).status_code == 404
    assert client.get(URL, headers=b).json() == []
    assert ai.panggilan == []
    assert client.get(path, headers=a).json()["judul_goal"] == "Belajar Docker"


def test_id_tidak_ada_404(client, auth_headers):
    h = auth_headers()
    assert client.get(f"{URL}/999", headers=h).status_code == 404
    assert client.post(f"{URL}/999/decompose", headers=h).status_code == 404


# ---------- dekomposisi ----------

def test_decompose_menyimpan_pohon_dengan_benar(client, auth_headers, ai):
    h = auth_headers()
    goal = _buat(client, h)

    r = client.post(f"{URL}/{goal['id_goal']}/decompose", headers=h)
    assert r.status_code == 201, r.text
    body = r.json()

    assert body["judul_goal"] == "Belajar Docker"  # goal_title dari AI tidak dipakai
    assert [m["judul_milestone"] for m in body["milestones"]] == ["Persiapan", "Eksekusi"]
    assert [m["urutan"] for m in body["milestones"]] == [1, 2]
    for m in body["milestones"]:
        assert m["tipe"] is None
        assert m["id_parent_milestone"] is None
    assert body["milestones"][0]["deadline"] == _akhir(2)  # max deadline task di milestone
    assert body["milestones"][1]["deadline"] == _akhir(6)

    tasks = [t for m in body["milestones"] for t in m["tasks"]]
    per_nama = {t["nama_task"]: t for t in tasks}
    assert len(tasks) == 5
    assert all(t["status"] == "todo" for t in tasks)
    assert [(t["nama_task"], t["deadline"], t["durasi_estimasi"], t["tingkat_effort"], t["tingkat_impact"])
            for t in tasks] == [
        ("Install Docker", _akhir(1), 30, "low", "high"),
        ("Baca dokumentasi", _akhir(2), 60, "medium", "medium"),
        ("Tulis Dockerfile", _akhir(2), 45, "high", "low"),
        ("Deploy container", _akhir(4), 90, "high", "high"),
        ("Tulis catatan", _akhir(6), 20, "low", "low"),
    ]
    id_ = {nama: t["id_task"] for nama, t in per_nama.items()}
    assert per_nama["Install Docker"]["prasyarat"] == []
    assert per_nama["Baca dokumentasi"]["prasyarat"] == [id_["Install Docker"]]
    # duplikat, diri sendiri (3) dan nomor tak dikenal (99) dibuang
    assert per_nama["Tulis Dockerfile"]["prasyarat"] == [id_["Install Docker"]]
    assert per_nama["Deploy container"]["prasyarat"] == sorted([id_["Baca dokumentasi"], id_["Tulis Dockerfile"]])
    assert per_nama["Tulis catatan"]["prasyarat"] == []

    # GET detail mengembalikan pohon yang sama
    assert client.get(f"{URL}/{goal['id_goal']}", headers=h).json() == body

    # request ke AI
    request, today = ai.panggilan[0]
    assert today == HARI_INI
    assert request.judul_goal == "Belajar Docker"
    assert request.deskripsi == "Sampai bisa deploy"
    assert request.deadline == date(2026, 10, 31)


def test_menit_harian_tanpa_rutin_dipotong_720(client, auth_headers, ai):
    h = auth_headers()
    goal = _buat(client, h)
    assert client.post(f"{URL}/{goal['id_goal']}/decompose", headers=h).status_code == 201
    # jam aktif default 06:00-22:00 = 960 menit/hari → dipotong ke batas schema 720
    assert ai.panggilan[0][0].menit_harian == 720


def test_menit_harian_dihitung_dari_jam_aktif_dikurangi_rutin(client, auth_headers, ai):
    h = auth_headers()
    for hari in range(5):
        r = client.post(URL_RUTIN, json={"nama": "Kuliah", "hari_dalam_minggu": hari,
                                         "waktu_mulai": "08:00", "waktu_selesai": "15:00"}, headers=h)
        assert r.status_code == 201
    goal = _buat(client, h)
    assert client.post(f"{URL}/{goal['id_goal']}/decompose", headers=h).status_code == 201

    jam_aktif = [scheduler.WeeklyWindow(d, settings.JAM_AKTIF_MULAI, settings.JAM_AKTIF_SELESAI) for d in range(7)]
    rutin = [scheduler.WeeklyWindow(d, time(8), time(15), label="Kuliah") for d in range(5)]
    diharapkan = scheduler.average_daily_minutes(jam_aktif, rutin)
    assert 15 <= diharapkan < 720
    assert ai.panggilan[0][0].menit_harian == diharapkan


def test_menit_harian_dari_body_menang(client, auth_headers, ai):
    h = auth_headers()
    goal = _buat(client, h)
    r = client.post(f"{URL}/{goal['id_goal']}/decompose", json={"menit_harian": 90}, headers=h)
    assert r.status_code == 201
    assert ai.panggilan[0][0].menit_harian == 90


@pytest.mark.parametrize("menit", [14, 721])
def test_menit_harian_body_di_luar_rentang_422(client, auth_headers, ai, menit):
    h = auth_headers()
    goal = _buat(client, h)
    r = client.post(f"{URL}/{goal['id_goal']}/decompose", json={"menit_harian": menit}, headers=h)
    assert r.status_code == 422
    assert ai.panggilan == []


def test_waktu_luang_terlalu_sedikit_422_tanpa_memanggil_ai(client, auth_headers, ai, db):
    h = auth_headers()
    # sisa luang 10 menit/hari (21:50-22:00)
    for hari in range(7):
        client.post(URL_RUTIN, json={"nama": "Padat", "hari_dalam_minggu": hari,
                                     "waktu_mulai": "06:00", "waktu_selesai": "21:50"}, headers=h)
    goal = _buat(client, h)
    r = client.post(f"{URL}/{goal['id_goal']}/decompose", headers=h)
    assert r.status_code == 422
    assert r.json()["detail"] == "Waktu luang harian terlalu sedikit (< 15 menit)"
    assert ai.panggilan == []
    assert _hitung(db, Milestone) == 0


def test_decompose_kedua_409_lalu_replace_mengganti_pohon(client, auth_headers, ai, db):
    h = auth_headers()
    goal = _buat(client, h)
    path = f"{URL}/{goal['id_goal']}/decompose"
    pertama = client.post(path, headers=h).json()
    nama_lama = {t["nama_task"] for m in pertama["milestones"] for t in m["tasks"]}
    assert _hitung(db, TaskDependency) == 4

    r = client.post(path, headers=h)
    assert r.status_code == 409
    assert r.json()["detail"] == "Goal sudah didekomposisi"
    assert len(ai.panggilan) == 1  # AI tidak dipanggil untuk request yang ditolak

    ai.hasil = _hasil_ai_kecil()
    r = client.post(path, params={"replace": "true"}, headers=h)
    assert r.status_code == 201, r.text
    baru = r.json()
    assert [m["judul_milestone"] for m in baru["milestones"]] == ["Ulang"]
    tasks_baru = baru["milestones"][0]["tasks"]
    assert [t["nama_task"] for t in tasks_baru] == ["Langkah A", "Langkah B"]
    assert tasks_baru[1]["prasyarat"] == [tasks_baru[0]["id_task"]]

    # pohon lama hilang total, tidak ada baris yatim
    assert _hitung(db, Milestone) == 1
    assert _hitung(db, Task) == 2
    assert _hitung(db, TaskDependency) == 1
    # (id tidak bisa dibandingkan: SQLite memakai ulang rowid yang sudah dihapus)
    assert not nama_lama & set(db.scalars(select(Task.nama_task)))
    id_ada = set(db.scalars(select(Task.id_task)))
    for dep in db.scalars(select(TaskDependency)):
        assert {dep.id_task, dep.id_task_prasyarat} <= id_ada


def test_replace_juga_menghapus_jadwal_task_lama(client, auth_headers, ai, db):
    h = auth_headers()
    goal = _buat(client, h)
    path = f"{URL}/{goal['id_goal']}/decompose"
    client.post(path, headers=h)
    id_task = db.scalar(select(Task.id_task).limit(1))
    db.add(JadwalTask(id_task=id_task, waktu_mulai=datetime(2026, 10, 5, 9), waktu_selesai=datetime(2026, 10, 5, 10)))
    db.commit()

    ai.hasil = _hasil_ai_kecil()
    assert client.post(path, params={"replace": "true"}, headers=h).status_code == 201
    assert _hitung(db, JadwalTask) == 0


def test_ai_error_502_dan_tidak_ada_yang_tersimpan(client, auth_headers, ai, db):
    h = auth_headers()
    goal = _buat(client, h)
    ai.error = ai_service.AIServiceError("Layanan AI sedang tidak tersedia. Coba lagi sebentar lagi.")
    r = client.post(f"{URL}/{goal['id_goal']}/decompose", headers=h)
    assert r.status_code == 502
    assert r.json()["detail"] == (
        "Gagal memproses goal dengan AI: Layanan AI sedang tidak tersedia. Coba lagi sebentar lagi."
    )
    assert _hitung(db, Milestone) == 0
    assert _hitung(db, Task) == 0
    assert _hitung(db, TaskDependency) == 0


def test_ai_error_saat_replace_pohon_lama_tetap_utuh(client, auth_headers, ai, db):
    h = auth_headers()
    goal = _buat(client, h)
    path = f"{URL}/{goal['id_goal']}/decompose"
    client.post(path, headers=h)
    ai.error = ai_service.AIServiceError("gagal")
    assert client.post(path, params={"replace": "true"}, headers=h).status_code == 502
    assert _hitung(db, Milestone) == 2
    assert _hitung(db, Task) == 5
    assert _hitung(db, TaskDependency) == 4


def test_goal_tanpa_deadline_422(client, auth_headers, ai, db):
    h = auth_headers()
    goal = _buat(client, h)
    db.get(Goal, goal["id_goal"]).deadline = None
    db.commit()
    r = client.post(f"{URL}/{goal['id_goal']}/decompose", headers=h)
    assert r.status_code == 422
    assert r.json()["detail"] == "Goal belum punya deadline"
    assert ai.panggilan == []


def test_goal_deadline_sudah_lewat_422(client, auth_headers, ai, db):
    h = auth_headers()
    goal = _buat(client, h)
    db.get(Goal, goal["id_goal"]).deadline = datetime(2026, 10, 4, 23, 59)
    db.commit()
    r = client.post(f"{URL}/{goal['id_goal']}/decompose", headers=h)
    assert r.status_code == 422
    assert r.json()["detail"] == "Deadline tidak boleh di masa lalu"
    assert ai.panggilan == []


def test_hapus_goal_cascade_milestone_task_dependensi_jadwal(client, auth_headers, ai, db):
    h = auth_headers()
    goal = _buat(client, h)
    lain = _buat(client, h, judul_goal="Goal lain")
    client.post(f"{URL}/{goal['id_goal']}/decompose", headers=h)
    client.post(f"{URL}/{lain['id_goal']}/decompose", headers=h)
    id_task = db.scalar(select(Task.id_task).join(Milestone).where(Milestone.id_goal == goal["id_goal"]).limit(1))
    db.add(JadwalTask(id_task=id_task, waktu_mulai=datetime(2026, 10, 5, 9), waktu_selesai=datetime(2026, 10, 5, 10)))
    db.commit()
    assert (_hitung(db, Milestone), _hitung(db, Task), _hitung(db, TaskDependency)) == (4, 10, 8)

    assert client.delete(f"{URL}/{goal['id_goal']}", headers=h).status_code == 204
    db.expire_all()
    assert db.get(Goal, goal["id_goal"]) is None
    # hanya pohon goal lain yang tersisa
    assert (_hitung(db, Milestone), _hitung(db, Task), _hitung(db, TaskDependency)) == (2, 5, 4)
    assert _hitung(db, JadwalTask) == 0


def test_hapus_user_cascade_goal(client, auth_headers, ai, db):
    h = auth_headers(email="goal@contoh.com")
    goal = _buat(client, h)
    client.post(f"{URL}/{goal['id_goal']}/decompose", headers=h)
    db.delete(db.scalar(select(User).where(User.email == "goal@contoh.com")))
    db.commit()
    assert (_hitung(db, Goal), _hitung(db, Milestone), _hitung(db, Task), _hitung(db, TaskDependency)) == (0, 0, 0, 0)


# ---------- simpan_dekomposisi tanpa HTTP ----------

def test_simpan_dekomposisi_unit(db):
    user = User(nama="Unit", email="unit@contoh.com", password="x")
    goal = Goal(user=user, judul_goal="Goal unit", deadline=datetime(2026, 10, 31, 23, 59))
    db.add(goal)
    db.commit()

    today = date(2026, 1, 10)
    goal_service.simpan_dekomposisi(db, goal, _hasil_ai(), today)

    milestones = db.scalars(select(Milestone).order_by(Milestone.urutan)).all()
    assert [(m.judul_milestone, m.urutan, m.tipe, m.id_parent_milestone, m.deadline) for m in milestones] == [
        ("Persiapan", 1, None, None, datetime(2026, 1, 11, 23, 59)),
        ("Eksekusi", 2, None, None, datetime(2026, 1, 15, 23, 59)),
    ]
    tasks = {t.nama_task: t for t in db.scalars(select(Task))}
    assert tasks["Install Docker"].deadline == datetime(2026, 1, 10, 23, 59)
    assert tasks["Tulis catatan"].deadline == datetime(2026, 1, 15, 23, 59)
    assert {t.status for t in tasks.values()} == {"todo"}
    pasangan = {(d.id_task, d.id_task_prasyarat) for d in db.scalars(select(TaskDependency))}
    i = {nama: t.id_task for nama, t in tasks.items()}
    assert pasangan == {
        (i["Baca dokumentasi"], i["Install Docker"]),
        (i["Tulis Dockerfile"], i["Install Docker"]),
        (i["Deploy container"], i["Baca dokumentasi"]),
        (i["Deploy container"], i["Tulis Dockerfile"]),
    }
    assert db.get(Goal, goal.id_goal).judul_goal == "Goal unit"

    # dipanggil lagi = mengganti, bukan menambah
    goal_service.simpan_dekomposisi(db, goal, _hasil_ai_kecil(), today)
    assert (_hitung(db, Milestone), _hitung(db, Task), _hitung(db, TaskDependency)) == (1, 2, 1)


def test_simpan_dekomposisi_rollback_jika_gagal(db, monkeypatch):
    user = User(nama="Unit", email="unit2@contoh.com", password="x")
    goal = Goal(user=user, judul_goal="Goal unit", deadline=datetime(2026, 10, 31, 23, 59))
    db.add(goal)
    db.commit()
    goal_service.simpan_dekomposisi(db, goal, _hasil_ai_kecil(), HARI_INI)

    def _gagal(d):
        raise RuntimeError("boom")

    monkeypatch.setattr(goal_service.waktu, "akhir_hari", _gagal)
    with pytest.raises(RuntimeError):
        goal_service.simpan_dekomposisi(db, goal, _hasil_ai(), HARI_INI)
    # pohon lama tidak terhapus karena transaksi di-rollback
    assert (_hitung(db, Milestone), _hitung(db, Task), _hitung(db, TaskDependency)) == (1, 2, 1)


def test_hanya_goal_service_yang_membaca_field_output_ai():
    """D11: field output AI hanya boleh dibaca di goal_service.simpan_dekomposisi."""
    field_ai = {"milestone_title", "task_title", "day_number", "estimated_minutes",
                "effort_level", "impact_level", "depends_on", "task_number"}
    app_dir = pathlib.Path(__file__).resolve().parents[1] / "app"
    # file AI milik Argya mendefinisikan/menormalisasi kontrak itu sendiri
    dikecualikan = {"services/ai_service.py", "schemas/ai_decomposition.py", "services/scheduler.py"}
    pemakai = set()
    for path in app_dir.rglob("*.py"):
        rel = path.relative_to(app_dir).as_posix()
        if rel in dikecualikan:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Attribute) and node.attr in field_ai:
                pemakai.add(rel)
    assert pemakai == {"services/goal_service.py"}

    fungsi = {
        node.name
        for node in ast.walk(ast.parse((app_dir / "services/goal_service.py").read_text(encoding="utf-8")))
        if isinstance(node, ast.FunctionDef)
        and any(isinstance(n, ast.Attribute) and n.attr in field_ai for n in ast.walk(node))
    }
    assert fungsi == {"simpan_dekomposisi"}
