"""Tes API kegiatan rutin mingguan: /api/v1/time-constraints."""

import pytest
from sqlalchemy import func, select

from app.models.time_constraint import TimeConstraint
from app.models.user import User

URL = "/api/v1/time-constraints"


def _rutin(**override):
    data = {"nama": "Kuliah", "hari_dalam_minggu": 0, "waktu_mulai": "08:00", "waktu_selesai": "10:00"}
    data.update(override)
    return data


def _buat(client, headers, **override):
    r = client.post(URL, json=_rutin(**override), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ---------- happy path ----------

def test_crud_lengkap(client, auth_headers):
    h = auth_headers()

    dibuat = _buat(client, h, nama="  Kuliah Kalkulus  ")
    assert dibuat["nama"] == "Kuliah Kalkulus"  # whitespace di-strip
    assert dibuat["hari_dalam_minggu"] == 0
    assert dibuat["waktu_mulai"] == "08:00:00"
    assert dibuat["waktu_selesai"] == "10:00:00"
    id_c = dibuat["id_constraint"]

    r = client.get(f"{URL}/{id_c}", headers=h)
    assert r.status_code == 200
    assert r.json() == dibuat

    r = client.get(URL, headers=h)
    assert r.status_code == 200
    assert [c["id_constraint"] for c in r.json()] == [id_c]

    r = client.patch(f"{URL}/{id_c}", json={"nama": "Gym", "waktu_selesai": "11:30"}, headers=h)
    assert r.status_code == 200
    assert r.json()["nama"] == "Gym"
    assert r.json()["waktu_mulai"] == "08:00:00"  # field yang tidak dikirim tidak berubah
    assert r.json()["waktu_selesai"] == "11:30:00"

    r = client.delete(f"{URL}/{id_c}", headers=h)
    assert r.status_code == 204
    assert r.content == b""
    assert client.get(f"{URL}/{id_c}", headers=h).status_code == 404
    assert client.get(URL, headers=h).json() == []


def test_list_urut_hari_lalu_jam_mulai(client, auth_headers):
    h = auth_headers()
    _buat(client, h, nama="Rabu siang", hari_dalam_minggu=2, waktu_mulai="13:00", waktu_selesai="14:00")
    _buat(client, h, nama="Senin siang", hari_dalam_minggu=0, waktu_mulai="13:00", waktu_selesai="14:00")
    _buat(client, h, nama="Rabu pagi", hari_dalam_minggu=2, waktu_mulai="07:00", waktu_selesai="08:00")
    _buat(client, h, nama="Senin pagi", hari_dalam_minggu=0, waktu_mulai="06:30", waktu_selesai="07:00")

    nama = [c["nama"] for c in client.get(URL, headers=h).json()]
    assert nama == ["Senin pagi", "Senin siang", "Rabu pagi", "Rabu siang"]


def test_melewati_tengah_malam_diterima(client, auth_headers):
    dibuat = _buat(client, auth_headers(), nama="Shift malam", waktu_mulai="22:00", waktu_selesai="01:00")
    assert dibuat["waktu_mulai"] == "22:00:00"
    assert dibuat["waktu_selesai"] == "01:00:00"


# ---------- 401 ----------

@pytest.mark.parametrize("method, path", [
    ("get", URL), ("post", URL), ("get", f"{URL}/1"), ("patch", f"{URL}/1"), ("delete", f"{URL}/1"),
])
def test_tanpa_token_401(client, method, path):
    kwargs = {"json": _rutin()} if method in ("post", "patch") else {}
    assert getattr(client, method)(path, **kwargs).status_code == 401


# ---------- 422 ----------

@pytest.mark.parametrize("override", [
    {"hari_dalam_minggu": 7},
    {"hari_dalam_minggu": -1},
    {"waktu_mulai": "09:00", "waktu_selesai": "09:00"},
    {"nama": ""},
    {"nama": "   "},
    {"nama": "x" * 101},
    {"waktu_mulai": "08:00:00+07:00"},
    {"waktu_mulai": "25:00"},
])
def test_input_tidak_valid_422(client, auth_headers, override):
    r = client.post(URL, json=_rutin(**override), headers=auth_headers())
    assert r.status_code == 422


def test_jam_sama_pesan_bahasa_indonesia(client, auth_headers):
    r = client.post(URL, json=_rutin(waktu_mulai="09:00", waktu_selesai="09:00"), headers=auth_headers())
    assert "Jam mulai dan jam selesai tidak boleh sama" in r.text


def test_patch_yang_membuat_jam_sama_422_dan_data_tidak_berubah(client, auth_headers):
    h = auth_headers()
    dibuat = _buat(client, h, waktu_mulai="08:00", waktu_selesai="10:00")
    r = client.patch(f"{URL}/{dibuat['id_constraint']}", json={"waktu_selesai": "08:00"}, headers=h)
    assert r.status_code == 422
    assert client.get(f"{URL}/{dibuat['id_constraint']}", headers=h).json() == dibuat


@pytest.mark.parametrize("body", [{"hari_dalam_minggu": 9}, {"nama": None}, {"nama": "  "}])
def test_patch_tidak_valid_422(client, auth_headers, body):
    h = auth_headers()
    dibuat = _buat(client, h)
    assert client.patch(f"{URL}/{dibuat['id_constraint']}", json=body, headers=h).status_code == 422


def test_id_tidak_ada_404(client, auth_headers):
    h = auth_headers()
    assert client.get(f"{URL}/999", headers=h).status_code == 404
    assert client.patch(f"{URL}/999", json={"nama": "X"}, headers=h).status_code == 404
    assert client.delete(f"{URL}/999", headers=h).status_code == 404


# ---------- isolasi antar user ----------

def test_user_lain_tidak_bisa_akses_404(client, auth_headers):
    a, b = auth_headers(), auth_headers()
    milik_a = _buat(client, a)
    path = f"{URL}/{milik_a['id_constraint']}"

    assert client.get(path, headers=b).status_code == 404
    assert client.patch(path, json={"nama": "Dibajak"}, headers=b).status_code == 404
    assert client.delete(path, headers=b).status_code == 404
    assert client.get(URL, headers=b).json() == []

    # milik A tetap utuh
    assert client.get(path, headers=a).json() == milik_a


def test_hapus_user_ikut_menghapus_kegiatan_rutin(client, db, auth_headers):
    h = auth_headers(email="rutin@contoh.com")
    _buat(client, h)
    _buat(client, h, hari_dalam_minggu=3)
    assert db.scalar(select(func.count()).select_from(TimeConstraint)) == 2

    db.delete(db.scalar(select(User).where(User.email == "rutin@contoh.com")))
    db.commit()
    assert db.scalar(select(func.count()).select_from(TimeConstraint)) == 0
