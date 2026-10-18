"""Tes API agenda: /api/v1/agenda (FR-5) termasuk peringatan bentrok."""

import pytest

URL = "/api/v1/agenda"
URL_RUTIN = "/api/v1/time-constraints"


def _agenda(**override):
    data = {"nama": "Rapat himpunan", "waktu_mulai": "2026-10-05T13:00:00", "waktu_selesai": "2026-10-05T15:00:00"}
    data.update(override)
    return data


def _buat(client, headers, **override):
    r = client.post(URL, json=_agenda(**override), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _buat_rutin(client, headers, **data):
    r = client.post(URL_RUTIN, json=data, headers=headers)
    assert r.status_code == 201, r.text


# ---------- happy path ----------

def test_crud_lengkap(client, auth_headers):
    h = auth_headers()

    dibuat = _buat(client, h, nama="  Seminar  ")
    assert dibuat["nama"] == "Seminar"
    assert dibuat["waktu_mulai"] == "2026-10-05T13:00:00"
    assert dibuat["waktu_selesai"] == "2026-10-05T15:00:00"
    assert dibuat["peringatan_bentrok"] == []
    id_a = dibuat["id_agenda"]

    r = client.get(f"{URL}/{id_a}", headers=h)
    assert r.status_code == 200
    assert r.json() == dibuat

    assert [a["id_agenda"] for a in client.get(URL, headers=h).json()] == [id_a]

    r = client.patch(f"{URL}/{id_a}", json={"waktu_selesai": "2026-10-05T16:30:00"}, headers=h)
    assert r.status_code == 200
    assert r.json()["waktu_mulai"] == "2026-10-05T13:00:00"
    assert r.json()["waktu_selesai"] == "2026-10-05T16:30:00"
    assert r.json()["nama"] == "Seminar"

    assert client.delete(f"{URL}/{id_a}", headers=h).status_code == 204
    assert client.get(f"{URL}/{id_a}", headers=h).status_code == 404
    assert client.get(URL, headers=h).json() == []


def test_list_urut_waktu_mulai(client, auth_headers):
    h = auth_headers()
    _buat(client, h, nama="C", waktu_mulai="2026-10-07T08:00:00", waktu_selesai="2026-10-07T09:00:00")
    _buat(client, h, nama="A", waktu_mulai="2026-10-05T08:00:00", waktu_selesai="2026-10-05T09:00:00")
    _buat(client, h, nama="B", waktu_mulai="2026-10-05T10:00:00", waktu_selesai="2026-10-05T11:00:00")
    assert [a["nama"] for a in client.get(URL, headers=h).json()] == ["A", "B", "C"]


def test_input_ber_timezone_disimpan_sebagai_wib_naive(client, auth_headers):
    h = auth_headers()
    dibuat = _buat(client, h, waktu_mulai="2026-10-07T12:00:00Z", waktu_selesai="2026-10-07T13:00:00Z")
    assert dibuat["waktu_mulai"] == "2026-10-07T19:00:00"
    assert dibuat["waktu_selesai"] == "2026-10-07T20:00:00"
    assert client.get(f"{URL}/{dibuat['id_agenda']}", headers=h).json()["waktu_mulai"] == "2026-10-07T19:00:00"


def test_hari_sama_dicek_setelah_konversi_ke_wib(client, auth_headers):
    # 16:30Z-17:30Z = 23:30-00:30 WIB → melewati tengah malam di WIB
    r = client.post(URL, json=_agenda(waktu_mulai="2026-10-07T16:30:00Z", waktu_selesai="2026-10-07T17:30:00Z"),
                    headers=auth_headers())
    assert r.status_code == 422
    assert "Agenda harus selesai di hari yang sama" in r.text


# ---------- 401 / 422 / 404 ----------

@pytest.mark.parametrize("method, path", [
    ("get", URL), ("post", URL), ("get", f"{URL}/1"), ("patch", f"{URL}/1"), ("delete", f"{URL}/1"),
])
def test_tanpa_token_401(client, method, path):
    kwargs = {"json": _agenda()} if method in ("post", "patch") else {}
    assert getattr(client, method)(path, **kwargs).status_code == 401


@pytest.mark.parametrize("override, pesan", [
    ({"waktu_selesai": "2026-10-05T13:00:00"}, "Waktu selesai harus setelah waktu mulai"),
    ({"waktu_selesai": "2026-10-05T12:00:00"}, "Waktu selesai harus setelah waktu mulai"),
    ({"waktu_mulai": "2026-10-05T22:00:00", "waktu_selesai": "2026-10-06T01:00:00"},
     "Agenda harus selesai di hari yang sama"),
    ({"nama": "   "}, None),
    ({"waktu_mulai": "bukan-tanggal"}, None),
])
def test_input_tidak_valid_422(client, auth_headers, override, pesan):
    r = client.post(URL, json=_agenda(**override), headers=auth_headers())
    assert r.status_code == 422
    if pesan:
        assert pesan in r.text


def test_patch_yang_membuat_rentang_tidak_valid_422(client, auth_headers):
    h = auth_headers()
    dibuat = _buat(client, h)
    path = f"{URL}/{dibuat['id_agenda']}"
    assert client.patch(path, json={"waktu_mulai": "2026-10-05T15:00:00"}, headers=h).status_code == 422
    assert client.patch(path, json={"waktu_selesai": "2026-10-06T10:00:00"}, headers=h).status_code == 422
    assert client.get(path, headers=h).json() == dibuat


def test_id_tidak_ada_404(client, auth_headers):
    h = auth_headers()
    assert client.get(f"{URL}/999", headers=h).status_code == 404
    assert client.patch(f"{URL}/999", json={"nama": "X"}, headers=h).status_code == 404
    assert client.delete(f"{URL}/999", headers=h).status_code == 404


# ---------- filter tanggal ----------

@pytest.fixture
def agenda_seminggu(client, auth_headers):
    h = auth_headers()
    _buat(client, h, nama="Senin malam", waktu_mulai="2026-10-05T23:00:00", waktu_selesai="2026-10-05T23:59:00")
    _buat(client, h, nama="Selasa awal", waktu_mulai="2026-10-06T00:00:00", waktu_selesai="2026-10-06T01:00:00")
    _buat(client, h, nama="Rabu", waktu_mulai="2026-10-07T10:00:00", waktu_selesai="2026-10-07T11:00:00")
    _buat(client, h, nama="Rabu malam", waktu_mulai="2026-10-07T23:00:00", waktu_selesai="2026-10-07T23:59:00")
    _buat(client, h, nama="Kamis awal", waktu_mulai="2026-10-08T00:00:00", waktu_selesai="2026-10-08T00:30:00")
    _buat(client, h, nama="Jumat", waktu_mulai="2026-10-09T08:00:00", waktu_selesai="2026-10-09T09:00:00")
    return h


def _nama(client, h, **params):
    r = client.get(URL, params=params, headers=h)
    assert r.status_code == 200, r.text
    return [a["nama"] for a in r.json()]


def test_filter_rentang_tanggal_inklusif(client, agenda_seminggu):
    # tepi rentang: agenda di hari `mulai` dan `sampai` ikut; 23:59 di hari sebelumnya dan 00:00 di
    # hari sesudahnya tidak ikut
    assert _nama(client, agenda_seminggu, mulai="2026-10-06", sampai="2026-10-07") == [
        "Selasa awal", "Rabu", "Rabu malam",
    ]


def test_filter_satu_hari(client, agenda_seminggu):
    assert _nama(client, agenda_seminggu, mulai="2026-10-07", sampai="2026-10-07") == ["Rabu", "Rabu malam"]


def test_filter_hanya_mulai_atau_hanya_sampai(client, agenda_seminggu):
    assert _nama(client, agenda_seminggu, mulai="2026-10-08") == ["Kamis awal", "Jumat"]
    assert _nama(client, agenda_seminggu, sampai="2026-10-05") == ["Senin malam"]


def test_filter_di_luar_rentang_kosong(client, agenda_seminggu):
    assert _nama(client, agenda_seminggu, mulai="2026-11-01", sampai="2026-11-30") == []


def test_filter_sampai_sebelum_mulai_422(client, auth_headers):
    r = client.get(URL, params={"mulai": "2026-10-07", "sampai": "2026-10-06"}, headers=auth_headers())
    assert r.status_code == 422
    assert "Tanggal sampai tidak boleh sebelum tanggal mulai" in r.text


# ---------- isolasi antar user ----------

def test_user_lain_tidak_bisa_akses_404(client, auth_headers):
    a, b = auth_headers(), auth_headers()
    milik_a = _buat(client, a)
    path = f"{URL}/{milik_a['id_agenda']}"

    assert client.get(path, headers=b).status_code == 404
    assert client.patch(path, json={"nama": "Dibajak"}, headers=b).status_code == 404
    assert client.delete(path, headers=b).status_code == 404
    assert client.get(URL, headers=b).json() == []
    assert client.get(path, headers=a).json() == milik_a


def test_agenda_user_lain_tidak_memicu_peringatan(client, auth_headers):
    a, b = auth_headers(), auth_headers()
    _buat(client, a, nama="Milik A")
    _buat_rutin(client, a, nama="Kuliah A", hari_dalam_minggu=0, waktu_mulai="13:00", waktu_selesai="15:00")
    assert _buat(client, b)["peringatan_bentrok"] == []


# ---------- peringatan bentrok (FR-5) ----------

def test_bentrok_dengan_kegiatan_rutin_di_hari_yang_sama(client, auth_headers):
    h = auth_headers()
    # 2026-10-05 adalah Senin → hari_dalam_minggu 0
    _buat_rutin(client, h, nama="Kuliah", hari_dalam_minggu=0, waktu_mulai="08:00", waktu_selesai="10:00")
    dibuat = _buat(client, h, waktu_mulai="2026-10-05T09:00:00", waktu_selesai="2026-10-05T11:00:00")
    assert dibuat["peringatan_bentrok"] == ["Bentrok dengan Kuliah (05/10 09:00-10:00, 60 menit)"]

    # tetap tersimpan; GET tidak mengembalikan peringatan
    r = client.get(f"{URL}/{dibuat['id_agenda']}", headers=h)
    assert r.status_code == 200
    assert r.json()["peringatan_bentrok"] == []


def test_rutin_di_hari_lain_tidak_bentrok(client, auth_headers):
    h = auth_headers()
    _buat_rutin(client, h, nama="Kuliah", hari_dalam_minggu=1, waktu_mulai="08:00", waktu_selesai="10:00")
    assert _buat(client, h, waktu_mulai="2026-10-05T09:00:00", waktu_selesai="2026-10-05T11:00:00")[
        "peringatan_bentrok"] == []


def test_rutin_lewat_tengah_malam_dari_hari_sebelumnya_bentrok(client, auth_headers):
    h = auth_headers()
    # Minggu 22:00 - Senin 01:00
    _buat_rutin(client, h, nama="Shift malam", hari_dalam_minggu=6, waktu_mulai="22:00", waktu_selesai="01:00")
    dibuat = _buat(client, h, waktu_mulai="2026-10-05T00:30:00", waktu_selesai="2026-10-05T02:00:00")
    assert dibuat["peringatan_bentrok"] == ["Bentrok dengan Shift malam (05/10 00:30-01:00, 30 menit)"]


def test_bentrok_dengan_agenda_lain(client, auth_headers):
    h = auth_headers()
    _buat(client, h, nama="Rapat", waktu_mulai="2026-10-06T10:00:00", waktu_selesai="2026-10-06T12:00:00")
    dibuat = _buat(client, h, nama="Dokter", waktu_mulai="2026-10-06T11:30:00", waktu_selesai="2026-10-06T12:30:00")
    assert dibuat["peringatan_bentrok"] == ["Bentrok dengan Rapat (06/10 11:30-12:00, 30 menit)"]


def test_bentrok_dengan_rutin_dan_agenda_sekaligus_urut_waktu(client, auth_headers):
    h = auth_headers()
    _buat_rutin(client, h, nama="Gym", hari_dalam_minggu=1, waktu_mulai="16:00", waktu_selesai="17:00")
    _buat(client, h, nama="Rapat", waktu_mulai="2026-10-06T15:00:00", waktu_selesai="2026-10-06T16:30:00")
    dibuat = _buat(client, h, nama="Les", waktu_mulai="2026-10-06T15:30:00", waktu_selesai="2026-10-06T17:00:00")
    assert dibuat["peringatan_bentrok"] == [
        "Bentrok dengan Rapat (06/10 15:30-16:30, 60 menit)",
        "Bentrok dengan Gym (06/10 16:00-17:00, 60 menit)",
    ]


def test_bersentuhan_di_ujung_tidak_bentrok(client, auth_headers):
    h = auth_headers()
    _buat_rutin(client, h, nama="Kuliah", hari_dalam_minggu=0, waktu_mulai="08:00", waktu_selesai="10:00")
    _buat(client, h, nama="Rapat", waktu_mulai="2026-10-05T12:00:00", waktu_selesai="2026-10-05T13:00:00")
    dibuat = _buat(client, h, waktu_mulai="2026-10-05T10:00:00", waktu_selesai="2026-10-05T12:00:00")
    assert dibuat["peringatan_bentrok"] == []


def test_patch_memberi_peringatan_dan_tidak_bentrok_dengan_diri_sendiri(client, auth_headers):
    h = auth_headers()
    _buat_rutin(client, h, nama="Kuliah", hari_dalam_minggu=2, waktu_mulai="08:00", waktu_selesai="10:00")
    dibuat = _buat(client, h, waktu_mulai="2026-10-07T13:00:00", waktu_selesai="2026-10-07T14:00:00")
    path = f"{URL}/{dibuat['id_agenda']}"

    # ganti nama saja → tidak dianggap bentrok dengan posisinya sendiri
    assert client.patch(path, json={"nama": "Rapat"}, headers=h).json()["peringatan_bentrok"] == []

    r = client.patch(path, json={"waktu_mulai": "2026-10-07T09:30:00"}, headers=h)
    assert r.status_code == 200
    assert r.json()["peringatan_bentrok"] == ["Bentrok dengan Kuliah (07/10 09:30-10:00, 30 menit)"]
