"""Tes API rincian task per minggu (D11): POST /goals/{id}/rinci-minggu?minggu=ini|depan. LLM selalu di-mock.

Goal default (Senin 5 → Sabtu 31 Okt): minggu 1 = 5–11, 2 = 12–18, 3 = 19–25, 4 = 26–31 Okt.
"""

from datetime import date

import pytest

from app.core import waktu
from app.core.status import TASK_DONE
from app.models.milestone import Milestone
from app.models.task import Task
from app.models.task_dependency import TaskDependency
from app.services import ai_service
from tests.test_api_goals import URL, MockAI, _akhir, _buat, _hitung, _task

SABTU = date(2026, 10, 10)


class MockRinci:
    def __init__(self):
        self.tasks = [_task(1, "Tulis compose.yml", 45, "medium", "high"), _task(2, "Jalankan compose", 30, deps=[1])]
        self.error: Exception | None = None
        self.panggilan: list[tuple] = []  # (request, today)

    def __call__(self, request, today=None, client=None):
        self.panggilan.append((request, today))
        if self.error is not None:
            raise self.error
        return [t.model_copy(deep=True) for t in self.tasks]


@pytest.fixture
def rinci(monkeypatch) -> MockRinci:
    mock = MockRinci()
    monkeypatch.setattr(ai_service, "rinci_minggu", mock)
    return mock


@pytest.fixture
def goal(client, auth_headers, monkeypatch, hari_ini_beku):
    """Goal yang sudah direncanakan AI pada Senin 5 Okt (task hanya di minggu ke-1)."""
    monkeypatch.setattr(ai_service, "rencanakan_goal", MockAI())
    h = auth_headers()
    g = _buat(client, h)
    assert client.post(f"{URL}/{g['id_goal']}/decompose", headers=h).status_code == 201
    return g["id_goal"], h


def _hari_ini(monkeypatch, d: date):
    monkeypatch.setattr(waktu, "hari_ini", lambda: d)


def _rinci(client, id_goal, h, minggu=None, json=None):
    params = {"minggu": minggu} if minggu else {}
    return client.post(f"{URL}/{id_goal}/rinci-minggu", params=params, json=json, headers=h)


def test_rinci_minggu_depan_hari_sabtu_menyimpan_task_dan_mengirim_progres(client, db, goal, rinci, monkeypatch):
    id_goal, h = goal
    selesai = db.query(Task).order_by(Task.id_task).first()
    selesai.status = TASK_DONE
    db.commit()
    _hari_ini(monkeypatch, SABTU)

    r = _rinci(client, id_goal, h, "depan")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["baru"] is True
    m = body["milestone"]
    assert (m["tipe"], m["judul_milestone"], m["urutan"], m["deadline"]) == (
        "mingguan", "Minggu 2", 2, _akhir(date(2026, 10, 18)))
    assert [(t["nama_task"], t["durasi_estimasi"], t["deadline"], t["status"]) for t in m["tasks"]] == [
        ("Tulis compose.yml", 45, _akhir(date(2026, 10, 18)), "todo"),
        ("Jalankan compose", 30, _akhir(date(2026, 10, 18)), "todo"),
    ]
    assert m["tasks"][1]["prasyarat"] == [m["tasks"][0]["id_task"]]

    # tersimpan di DB & ikut muncul di detail goal
    detail = client.get(f"{URL}/{id_goal}", headers=h).json()
    assert [len(x["tasks"]) for x in detail["milestones"]] == [0, 5, 2, 0, 0]

    request, today = rinci.panggilan[0]
    assert today == SABTU
    assert (request.judul_goal, request.deskripsi_goal, request.deadline_goal) == (
        "Belajar Docker", "Sampai bisa deploy", date(2026, 10, 31))
    t = request.target
    assert (t.minggu_ke, t.mulai, t.akhir, t.judul) == (2, date(2026, 10, 12), date(2026, 10, 18), "Minggu 2")
    assert (request.target_berikutnya.minggu_ke, request.target_berikutnya.judul) == (3, "Minggu 3")
    assert [(p.minggu_ke, p.judul, p.menit, p.selesai) for p in request.progres] == [
        (1, "Install Docker", 30, True), (1, "Baca dokumentasi", 60, False), (1, "Tulis Dockerfile", 45, False),
        (1, "Deploy container", 90, False), (1, "Tulis catatan", 20, False),
    ]
    assert request.menit_harian == 720  # tanpa kegiatan rutin: dihitung D6, dipotong 720


def test_rinci_minggu_idempotent_tanpa_memanggil_ai_lagi(client, db, goal, rinci, monkeypatch):
    id_goal, h = goal
    _hari_ini(monkeypatch, SABTU)
    pertama = _rinci(client, id_goal, h, "depan").json()

    kedua = _rinci(client, id_goal, h, "depan")

    assert kedua.status_code == 200
    assert kedua.json() == {**pertama, "baru": False}
    assert len(rinci.panggilan) == 1
    assert _hitung(db, Task) == 7


def test_rinci_minggu_ini_yang_sudah_ada_task_tidak_memanggil_ai(client, goal, rinci):
    id_goal, h = goal  # Senin 5 Okt: minggu ke-1 sudah berisi task dari /decompose
    r = _rinci(client, id_goal, h)
    assert r.status_code == 200
    assert r.json()["baru"] is False
    assert r.json()["milestone"]["judul_milestone"] == "Minggu 1"
    assert len(r.json()["milestone"]["tasks"]) == 5
    assert rinci.panggilan == []


def test_rinci_minggu_ini_saat_minggunya_tiba(client, goal, rinci, monkeypatch):
    id_goal, h = goal
    rabu = date(2026, 10, 21)
    _hari_ini(monkeypatch, rabu)

    r = _rinci(client, id_goal, h, "ini", json={"menit_harian": 60})

    assert r.status_code == 200 and r.json()["baru"] is True
    assert r.json()["milestone"]["judul_milestone"] == "Minggu 3"
    request, today = rinci.panggilan[0]
    assert today == rabu and request.menit_harian == 60
    assert request.target.minggu_ke == 3
    assert request.target_berikutnya.minggu_ke == 4
    # progres: minggu 1 (5 task) — minggu 2 terlewat tanpa dirinci, jadi tidak punya task
    assert [p.minggu_ke for p in request.progres] == [1] * 5


def test_minggu_terakhir_tanpa_target_berikutnya(client, goal, rinci, monkeypatch):
    id_goal, h = goal
    _hari_ini(monkeypatch, date(2026, 10, 24))  # Sabtu → minggu depan = minggu ke-4 (26–31 Okt), terakhir

    assert _rinci(client, id_goal, h, "depan").status_code == 200

    request, _ = rinci.panggilan[0]
    assert (request.target.minggu_ke, request.target.akhir) == (4, date(2026, 10, 31))
    assert request.target_berikutnya is None


@pytest.mark.parametrize("hari", [date(2026, 10, 5), date(2026, 10, 9)])  # Senin, Jumat
def test_minggu_depan_sebelum_sabtu_409(client, goal, rinci, monkeypatch, hari):
    id_goal, h = goal
    _hari_ini(monkeypatch, hari)
    r = _rinci(client, id_goal, h, "depan")
    assert r.status_code == 409
    assert r.json()["detail"] == "Task minggu depan baru bisa dirinci mulai hari Sabtu"
    assert rinci.panggilan == []


def test_minggu_depan_hari_minggu_boleh(client, goal, rinci, monkeypatch):
    id_goal, h = goal
    _hari_ini(monkeypatch, date(2026, 10, 11))
    r = _rinci(client, id_goal, h, "depan")
    assert r.status_code == 200 and r.json()["milestone"]["judul_milestone"] == "Minggu 2"


def test_tidak_ada_target_404(client, auth_headers, goal, rinci, monkeypatch):
    id_goal, h = goal
    _hari_ini(monkeypatch, date(2026, 10, 31))  # Sabtu minggu terakhir: minggu depan di luar deadline
    r = _rinci(client, id_goal, h, "depan")
    assert r.status_code == 404
    assert r.json()["detail"] == "Goal tidak punya target untuk minggu depan"

    belum = _buat(client, h)  # goal belum direncanakan AI
    assert _rinci(client, belum["id_goal"], h).status_code == 404
    assert rinci.panggilan == []


def test_parameter_minggu_tidak_valid_422(client, goal, rinci):
    id_goal, h = goal
    assert _rinci(client, id_goal, h, "lusa").status_code == 422


@pytest.mark.parametrize("menit", [14, 721])
def test_menit_harian_di_luar_rentang_422(client, goal, rinci, monkeypatch, menit):
    id_goal, h = goal
    _hari_ini(monkeypatch, SABTU)
    assert _rinci(client, id_goal, h, "depan", json={"menit_harian": menit}).status_code == 422
    assert rinci.panggilan == []


def test_ai_error_502_dan_tidak_ada_yang_tersimpan(client, db, goal, rinci, monkeypatch):
    id_goal, h = goal
    _hari_ini(monkeypatch, SABTU)
    rinci.error = ai_service.AIServiceError("Layanan AI sedang tidak tersedia. Coba lagi sebentar lagi.")

    r = _rinci(client, id_goal, h, "depan")

    assert r.status_code == 502
    assert r.json()["detail"] == "Gagal merinci minggu dengan AI: Layanan AI sedang tidak tersedia. Coba lagi sebentar lagi."
    assert (_hitung(db, Milestone), _hitung(db, Task), _hitung(db, TaskDependency)) == (5, 5, 4)
