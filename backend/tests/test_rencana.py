"""Unit tests untuk app/services/rencana.py (kerangka minggu & bulan kalender, D4/D11)"""

from datetime import date, timedelta

import pytest

from app.services.rencana import daftar_minggu, kerangka_rencana


def d(month, day, year=2026):
    return date(year, month, day)


def rentang(minggu):
    return [(m.minggu_ke, m.mulai, m.akhir) for m in minggu]


def test_minggu_pertama_mulai_hari_ini_sampai_minggu():
    minggu = daftar_minggu(d(10, 21), d(11, 8))  # Rabu → Minggu dua pekan kemudian
    assert rentang(minggu) == [
        (1, d(10, 21), d(10, 25)),
        (2, d(10, 26), d(11, 1)),
        (3, d(11, 2), d(11, 8)),
    ]
    assert [m.jumlah_hari for m in minggu] == [5, 7, 7]


def test_minggu_terakhir_dipotong_di_deadline():
    minggu = daftar_minggu(d(10, 19), d(10, 28))  # Senin → Rabu pekan depan
    assert rentang(minggu) == [(1, d(10, 19), d(10, 25)), (2, d(10, 26), d(10, 28))]


def test_deadline_hari_ini_satu_minggu_satu_hari():
    assert rentang(daftar_minggu(d(10, 25), d(10, 25))) == [(1, d(10, 25), d(10, 25))]


def test_dibuat_hari_minggu_minggu_pertama_satu_hari():
    minggu = daftar_minggu(d(10, 25), d(10, 27))  # Minggu → Selasa
    assert rentang(minggu) == [(1, d(10, 25), d(10, 25)), (2, d(10, 26), d(10, 27))]


def test_deadline_lewat_ditolak():
    with pytest.raises(ValueError):
        daftar_minggu(d(10, 21), d(10, 20))


def test_minggu_tersambung_tanpa_celah():
    minggu = daftar_minggu(d(10, 21), d(12, 31))
    assert minggu[0].mulai == d(10, 21) and minggu[-1].akhir == d(12, 31)
    for a, b in zip(minggu, minggu[1:]):
        assert b.mulai == a.akhir + timedelta(days=1) and b.mulai.weekday() == 0


def test_kerangka_contoh_toefl():
    bulan = kerangka_rencana(d(10, 21), d(12, 31))
    assert [(b.bulan_ke, b.nama) for b in bulan] == [(1, "Oktober 2026"), (2, "November 2026"), (3, "Desember 2026")]
    # 26 Okt–1 Nov: 6 hari di Oktober → Oktober; 30 Nov–6 Des: 6 hari di Desember → Desember
    assert [[m.minggu_ke for m in b.minggu] for b in bulan] == [[1, 2], [3, 4, 5, 6], [7, 8, 9, 10, 11]]
    assert bulan[2].minggu[0].mulai == d(11, 30)
    assert bulan[2].minggu[-1].akhir == d(12, 31)  # minggu terakhir Kamis 31 Des


def test_minggu_lintas_bulan_ikut_hari_terbanyak():
    # Senin 28 Sep–Minggu 4 Okt: 3 hari September, 4 hari Oktober → Oktober
    bulan = kerangka_rencana(d(9, 28), d(10, 4))
    assert [b.nama for b in bulan] == ["Oktober 2026"]


def test_minggu_terpotong_dihitung_dari_hari_yang_benar_benar_ada():
    # 28–30 Sep saja (deadline Rabu): seluruh harinya di September walau Kamis minggu itu 1 Okt
    assert [b.nama for b in kerangka_rencana(d(9, 28), d(9, 30))] == ["September 2026"]


def test_seri_kurang_dari_4_hari_masuk_bulan_berikutnya():
    # Sabtu 31 Okt + Minggu 1 Nov: 1–1, 2 hari → November (tidak ada "Oktober" berisi 1 hari)
    bulan = kerangka_rencana(d(10, 31), d(11, 8))
    assert [(b.nama, [m.minggu_ke for m in b.minggu]) for b in bulan] == [("November 2026", [1, 2])]


@pytest.mark.parametrize("mulai, deadline, nama", [
    (d(3, 30), d(4, 2), "Maret 2026"),      # Sen 30 Mar–Kam 2 Apr: 2–2, 4 hari → bulan sebelumnya
    (d(9, 28), d(10, 3), "September 2026"),  # Sen 28 Sep–Sab 3 Okt: 3–3, 6 hari → bulan sebelumnya
])
def test_seri_4_hari_atau_lebih_masuk_bulan_sebelumnya(mulai, deadline, nama):
    assert [b.nama for b in kerangka_rencana(mulai, deadline)] == [nama]


def test_lintas_tahun():
    bulan = kerangka_rencana(d(12, 28), d(1, 10, 2027))
    # 28 Des 2026–3 Jan 2027: 4 hari Desember → Desember 2026
    assert [(b.nama, [m.minggu_ke for m in b.minggu]) for b in bulan] == [
        ("Desember 2026", [1]), ("Januari 2027", [2])
    ]


def test_bulan_pendek_tetap_ditampilkan():
    # dibuat Rabu 28 Okt: Oktober hanya 4 hari (28–31) + 1 Nov → 4 vs 1 → Oktober
    bulan = kerangka_rencana(d(10, 28), d(11, 15))
    assert bulan[0].nama == "Oktober 2026" and bulan[0].minggu[0].jumlah_hari == 5
