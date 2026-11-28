"""Ekspor dataset model personalisasi ke CSV + cetak ringkasannya (docs/AI.md §2).

Jalankan dari folder backend (memakai DATABASE_URL di .env):
    .\\venv\\Scripts\\python.exe scripts\\ekspor_dataset.py
    .\\venv\\Scripts\\python.exe scripts\\ekspor_dataset.py --keluaran data.csv --sampai 2026-12-01T00:00

Arti tiap kolom: docs/KAMUS_DATA_DATASET.md. Untuk training, pakai baris yang kolom `label`-nya terisi.
"""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.stdout.reconfigure(encoding="utf-8")

import app.models  # noqa: E402,F401 — daftarkan semua tabel
from app.core import waktu  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services.dataset_service import KOLOM, baris_dataset, ringkasan  # noqa: E402


def tulis_csv(baris: list[dict], keluaran: Path) -> None:
    with keluaran.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=KOLOM)
        writer.writeheader()
        writer.writerows(baris)


def cetak_ringkasan(r: dict) -> None:
    print(f"Sesi berakhir        : {r['sesi_berakhir']}")
    print(f"  selesai / dilewati : {r['selesai']} / {r['dilewati']}")
    print(f"  belum dikonfirmasi : {r['belum_dikonfirmasi']}")
    print(f"Tingkat konfirmasi   : {r['tingkat_konfirmasi_persen']}%")
    print(f"Sesi eksplorasi      : {r['eksplorasi']} ({r['eksplorasi_persen']}%)")
    print(f"Sesi dipindah        : {r['dipindah']}")
    print(f"Tanpa snapshot fitur : {r['tanpa_snapshot']}")
    print(f"Sesi dengan mood     : {r['dengan_mood_persen']}%")
    print("Per user (terkonfirmasi / sesi berakhir):")
    for user, u in r["per_user"].items():
        print(f"  {user}: {u['terkonfirmasi']} / {u['sesi_berakhir']} ({u['tingkat_konfirmasi_persen']}%)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--keluaran", type=Path, default=Path("dataset_personalisasi.csv"))
    parser.add_argument("--sampai", type=datetime.fromisoformat, default=None,
                        help="hanya sesi yang berakhir paling lambat waktu ini (WIB); default sekarang")
    args = parser.parse_args()

    sampai = args.sampai or waktu.sekarang()
    with SessionLocal() as db:
        baris = baris_dataset(db, sampai)
    tulis_csv(baris, args.keluaran)
    print(f"{len(baris)} baris → {args.keluaran.resolve()} (sesi berakhir s.d. {sampai:%Y-%m-%d %H:%M})\n")
    cetak_ringkasan(ringkasan(baris))


if __name__ == "__main__":
    main()
