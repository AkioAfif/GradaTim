"""
demo_rencana.py — Coba rencana goal bulanan → mingguan (D4, D11) langsung ke LLM

Mencetak kerangka minggu & bulan kalender buatan sistem, lalu hasil AI: target bulanan, target mingguan,
dan task minggu ke-1. Hasil juga disimpan ke scripts/demo_output/ (Markdown + JSON).

Cara pakai (dari folder backend/, venv aktif, LLM_API_KEY di .env):
    python scripts/demo_rencana.py
    python scripts/demo_rencana.py --goal "Lulus TOEFL 550" --deadline 2026-12-31 --menit 90
    python scripts/demo_rencana.py --hari-ini 2026-10-31      # coba minggu pertama yang pendek
"""

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.stdout.reconfigure(encoding="utf-8")

from app.core import waktu  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.schemas.ai_decomposition import GoalDecompositionRequest  # noqa: E402
from app.services.ai_service import AIServiceError, _kerangka_teks, rencanakan_goal  # noqa: E402
from app.services.rencana import kerangka_rencana  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / "demo_output"


def parse_args():
    hari_ini = waktu.hari_ini()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--goal", default="Belajar Docker sampai bisa deploy aplikasi sendiri")
    parser.add_argument("--deskripsi", default="Pemula, belum pernah pakai container")
    parser.add_argument("--hari-ini", type=date.fromisoformat, default=hari_ini)
    parser.add_argument("--deadline", type=date.fromisoformat, default=hari_ini + timedelta(days=45))
    parser.add_argument("--menit", type=int, default=60, help="menit luang per hari")
    return parser.parse_args()


def main():
    args = parse_args()
    request = GoalDecompositionRequest(judul_goal=args.goal, deskripsi=args.deskripsi, deadline=args.deadline,
                                       menit_harian=args.menit)
    md = [f"# Demo rencana bulanan → mingguan — {datetime.now():%d %B %Y, %H:%M}", "",
          f"- **Goal:** {request.judul_goal}", f"- **Deskripsi:** {request.deskripsi}",
          f"- **Hari ini:** {args.hari_ini} · **Deadline:** {request.deadline} · **Waktu luang:** {args.menit} menit/hari",
          "", "## Kerangka (dihitung sistem)", "", "```", _kerangka_teks(kerangka_rencana(args.hari_ini, args.deadline)),
          "```", ""]

    print(f"Memanggil {settings.LLM_MODEL}... (bisa 10-60 detik)")
    t0 = datetime.now()
    try:
        rencana = rencanakan_goal(request, today=args.hari_ini)
    except AIServiceError as e:
        cause = f" ({e.__cause__})" if e.__cause__ else ""
        sys.exit(f"\n[GAGAL] {e}{cause}\nCek LLM_API_KEY / LLM_MODEL di backend/.env.")
    md += [f"## Hasil AI (`{settings.LLM_MODEL}`, {(datetime.now() - t0).total_seconds():.1f} detik)", ""]

    for b in rencana.bulan:
        md += [f"### Bulan {b.bulan_ke}: {b.judul}", f"_{b.deskripsi}_", ""]
        for m in b.minggu:
            md.append(f"- **Minggu {m.minggu_ke}** ({m.mulai:%d/%m}–{m.akhir:%d/%m}): {m.judul} — {m.deskripsi}")
        md.append("")

    total = sum(t.estimated_minutes for t in rencana.task_minggu_ini)
    md += [f"## Task minggu ke-1 ({len(rencana.task_minggu_ini)} task, total {total} menit)", "",
           "| # | Task | Menit | Effort | Impact | Butuh |", "| ---: | --- | ---: | --- | --- | --- |"]
    for t in rencana.task_minggu_ini:
        butuh = ", ".join(f"#{d}" for d in t.depends_on) or "-"
        md.append(f"| {t.task_number} | {t.task_title} | {t.estimated_minutes} | {t.effort_level} "
                  f"| {t.impact_level} | {butuh} |")

    OUTPUT_DIR.mkdir(exist_ok=True)
    stem = f"rencana_{datetime.now():%Y%m%d_%H%M%S}"
    (OUTPUT_DIR / f"{stem}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (OUTPUT_DIR / f"{stem}.json").write_text(rencana.model_dump_json(indent=2), encoding="utf-8")
    print("\n".join(md))
    print(f"\nTersimpan: {OUTPUT_DIR / stem}.md / .json")


if __name__ == "__main__":
    main()
