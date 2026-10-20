"""
demo_rinci_minggu.py — Coba rincian task minggu berikutnya (D11) langsung ke LLM

Memakai rencana tersimpan dari demo_rencana.py / demo_ai.py (tanpa merencanakan ulang), menandai sebagian task
minggu ke-1 sebagai selesai, lalu meminta AI merinci task untuk minggu ke-2 (atau minggu lain) — sama seperti
yang dilakukan endpoint POST /api/v1/goals/{id}/rinci-minggu.

JSON rencana tidak menyimpan judul goal, jadi isi --goal / --deskripsi sama seperti saat membuat rencananya.

Cara pakai (dari folder backend/, venv aktif, LLM_API_KEY di .env):
    python scripts/demo_rinci_minggu.py --goal "Lulus TOEFL 550" --deskripsi "Skor sekarang 450"
    python scripts/demo_rinci_minggu.py --selesai 1,2,3 --menit 90         # task #1-#3 minggu ke-1 selesai
    python scripts/demo_rinci_minggu.py --selesai ""                       # belum ada yang selesai
    python scripts/demo_rinci_minggu.py --minggu 3 --hari-ini 2026-10-21   # minggu ke-3, dirinci hari Rabu
"""

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.stdout.reconfigure(encoding="utf-8")

from app.core.config import settings  # noqa: E402
from app.schemas.ai_decomposition import ProgresTask, RencanaGoal, RincianMingguRequest  # noqa: E402
from app.services.ai_service import AIServiceError, rinci_minggu  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / "demo_output"
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", type=Path, help="Rencana dari demo_rencana.py / demo_ai.py (default: yang terbaru)")
    parser.add_argument("--goal", default="Belajar Docker sampai bisa deploy aplikasi sendiri")
    parser.add_argument("--deskripsi", default="Pemula, belum pernah pakai container")
    parser.add_argument("--minggu", type=int, default=2, help="Minggu ke berapa yang dirinci (default 2)")
    parser.add_argument("--selesai", help="Nomor task minggu ke-1 yang sudah selesai, dipisah koma "
                                          "(default: separuh pertama)")
    parser.add_argument("--menit", type=int, help="Menit luang per hari (default: tanpa batas)")
    parser.add_argument("--hari-ini", type=date.fromisoformat,
                        help="Tanggal saat merinci (default: Sabtu sebelum minggu itu, seperti tombol 'minggu depan')")
    return parser.parse_args()


def rencana_terbaru() -> Path:
    semua = sorted(OUTPUT_DIR.glob("*rencana*.json"), key=lambda p: p.stat().st_mtime)
    if not semua:
        sys.exit("Belum ada rencana tersimpan. Jalankan dulu: python scripts/demo_rencana.py")
    return semua[-1]


def main():
    args = parse_args()
    path = args.json or rencana_terbaru()
    rencana = RencanaGoal.model_validate_json(path.read_text(encoding="utf-8"))
    semua_minggu = [m for b in rencana.bulan for m in b.minggu]
    nomor = {m.minggu_ke: m for m in semua_minggu}
    if args.minggu not in nomor or args.minggu < 2:
        sys.exit(f"Minggu ke-{args.minggu} tidak ada di rencana (pilih 2..{len(semua_minggu)}).")
    target = nomor[args.minggu]
    hari_ini = args.hari_ini or target.mulai - timedelta(days=2)

    tasks = rencana.task_minggu_ini
    if args.selesai is None:
        selesai = {t.task_number for t in tasks[: len(tasks) // 2]}
    else:
        selesai = {int(x) for x in args.selesai.split(",") if x.strip()}
    # demo: hanya minggu ke-1 yang punya task (minggu di antaranya dianggap belum dirinci)
    progres = [ProgresTask(minggu_ke=1, judul=t.task_title, menit=t.estimated_minutes, selesai=t.task_number in selesai)
               for t in tasks]

    request = RincianMingguRequest(
        judul_goal=args.goal,
        deskripsi_goal=args.deskripsi,
        deadline_goal=semua_minggu[-1].akhir,
        target=target,
        target_berikutnya=nomor.get(args.minggu + 1),
        progres=progres,
        menit_harian=args.menit,
    )

    md = [f"# Demo rincian minggu ke-{target.minggu_ke} — {datetime.now():%d %B %Y, %H:%M}", "",
          f"- **Goal:** {request.judul_goal} (sumber rencana: `{path.name}`)",
          f"- **Target minggu ke-{target.minggu_ke}** ({target.mulai:%d/%m}–{target.akhir:%d/%m}): "
          f"{target.judul} — {target.deskripsi}",
          f"- **Dirinci pada:** {HARI[hari_ini.weekday()]} {hari_ini:%d/%m/%Y} · **Waktu luang:** "
          f"{f'{args.menit} menit/hari' if args.menit else 'tidak dibatasi'}", "",
          "## Progres minggu ke-1 (input ke AI)", ""]
    md += [f"- [{'x' if p.selesai else ' '}] {p.judul} ({p.menit} menit)" for p in progres]
    md.append("")

    print(f"Memanggil {settings.LLM_MODEL}... (bisa 10-60 detik)")
    t0 = datetime.now()
    try:
        hasil = rinci_minggu(request, today=hari_ini)
    except AIServiceError as e:
        cause = f" ({e.__cause__})" if e.__cause__ else ""
        sys.exit(f"\n[GAGAL] {e}{cause}\nCek LLM_API_KEY / LLM_MODEL di backend/.env.")

    total = sum(t.estimated_minutes for t in hasil)
    md += [f"## Task minggu ke-{target.minggu_ke} dari AI (`{settings.LLM_MODEL}`, "
           f"{(datetime.now() - t0).total_seconds():.1f} detik) — {len(hasil)} task, total {total} menit", "",
           "| # | Task | Menit | Effort | Impact | Butuh |", "| ---: | --- | ---: | --- | --- | --- |"]
    for t in hasil:
        butuh = ", ".join(f"#{d}" for d in t.depends_on) or "-"
        md.append(f"| {t.task_number} | {t.task_title} | {t.estimated_minutes} | {t.effort_level} "
                  f"| {t.impact_level} | {butuh} |")

    OUTPUT_DIR.mkdir(exist_ok=True)
    md_path = OUTPUT_DIR / f"rinci_{datetime.now():%Y%m%d_%H%M%S}.md"
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    print(f"\nTersimpan: {md_path}")


if __name__ == "__main__":
    main()
