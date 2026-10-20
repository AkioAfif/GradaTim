"""
demo_ai.py — Demo end-to-end fitur AI GradaTim (untuk laporan / bukti pekerjaan)

Alur:
    1. Rencana goal (FR-2, D4, D11): goal + deadline dipecah LLM jadi target bulanan → mingguan,
       plus task konkret untuk minggu ke-1 (kerangka tanggal dihitung sistem)
    2. Mood Capacity (FR-6): beberapa skenario jawaban kuesioner diprediksi kapasitasnya
    3. Rekomendasi task (FR-7, FR-8): task minggu ke-1 dipilih sesuai kapasitas mood, urgensi, dan
       dependensi (prasyarat harus selesai dulu)

Hasil dicetak ke console dan disimpan ke scripts/demo_output/ (Markdown + JSON rencana; JSON-nya bisa
dipakai scripts/demo_jadwal.py).

Cara pakai (dari folder backend/, venv aktif):
    python scripts/demo_ai.py
    python scripts/demo_ai.py --goal "Lulus TOEFL 550" --deskripsi "Skor sekarang 450" --deadline 2026-12-31 --menit 90
    python scripts/demo_ai.py --mood 2,2,3,1,2          # satu skenario mood saja
    python scripts/demo_ai.py --offline                 # tanpa API key (data contoh, BUKAN dari LLM)
"""

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.stdout.reconfigure(encoding="utf-8")

from demo_rencana import rencana_md  # noqa: E402  (scripts/ ada di sys.path saat skrip dijalankan)

from app.core import waktu  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.schemas.ai_decomposition import (  # noqa: E402
    GoalDecompositionRequest,
    PlannedTask,
    RencanaGoal,
    TargetBulan,
    TargetMinggu,
)
from app.schemas.mood import MoodAnswers  # noqa: E402
from app.services.ai_service import AIServiceError, assess_mood, recommend_tasks, rencanakan_goal  # noqa: E402
from app.services.rencana import kerangka_rencana  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / "demo_output"

DEFAULT_MOOD_SCENARIOS = {
    "Kurang tidur & cemas": [2, 1, 2, 1, 2],
    "Biasa saja": [3, 3, 4, 3, 3],
    "Sangat prima": [5, 4, 5, 5, 4],
}

# Hanya dipakai dengan --offline. Ditandai jelas di output agar tidak tertukar dengan hasil LLM.
OFFLINE_TASKS = [
    {"task_number": 1, "depends_on": [], "task_title": "Install Docker Desktop & verifikasi CLI", "estimated_minutes": 30, "effort_level": "low", "impact_level": "high"},
    {"task_number": 2, "depends_on": [1], "task_title": "Pelajari konsep image, container, dan volume", "estimated_minutes": 45, "effort_level": "medium", "impact_level": "high"},
    {"task_number": 3, "depends_on": [2], "task_title": "Buat Dockerfile untuk aplikasi FastAPI sederhana", "estimated_minutes": 60, "effort_level": "high", "impact_level": "high"},
    {"task_number": 4, "depends_on": [3], "task_title": "Baca dokumentasi docker-compose.yml", "estimated_minutes": 30, "effort_level": "low", "impact_level": "medium"},
    {"task_number": 5, "depends_on": [4], "task_title": "Jalankan FastAPI + PostgreSQL dengan Compose", "estimated_minutes": 60, "effort_level": "high", "impact_level": "high"},
    {"task_number": 6, "depends_on": [], "task_title": "Rapikan catatan perintah Docker yang sering dipakai", "estimated_minutes": 20, "effort_level": "low", "impact_level": "low"},
]


def parse_args():
    hari_ini = waktu.hari_ini()
    parser = argparse.ArgumentParser(description="Demo AI GradaTim: rencana goal + rekomendasi mood")
    parser.add_argument("--goal", default="Belajar Docker & CI/CD untuk project kuliah")
    parser.add_argument("--deskripsi", default="Saya baru paham dasar Python dan Git, belum pernah pakai Docker.")
    parser.add_argument("--deadline", type=date.fromisoformat, default=hari_ini + timedelta(days=45),
                        help="Format YYYY-MM-DD (default: 45 hari dari hari ini)")
    parser.add_argument("--menit", type=int, default=60, help="Waktu luang per hari dalam menit")
    parser.add_argument("--mood", help="5 angka 1-5 dipisah koma: fokus,tenang,motivasi,tidur,siap")
    parser.add_argument("--offline", action="store_true", help="Pakai data contoh, tanpa memanggil LLM")
    return parser.parse_args()


def rencana_offline(hari_ini: date, deadline: date) -> RencanaGoal:
    """Kerangka kalender asli + judul generik + task contoh buatan tangan."""
    return RencanaGoal(
        bulan=[
            TargetBulan(bulan_ke=b.bulan_ke, tahun=b.tahun, bulan=b.bulan, judul=f"Target {b.nama}", deskripsi="(contoh)",
                        minggu=[TargetMinggu(minggu_ke=m.minggu_ke, mulai=m.mulai, akhir=m.akhir,
                                             judul=f"Target minggu ke-{m.minggu_ke}", deskripsi="(contoh)")
                                for m in b.minggu])
            for b in kerangka_rencana(hari_ini, deadline)
        ],
        task_minggu_ini=[PlannedTask.model_validate(t) for t in OFFLINE_TASKS],
    )


def task_table(tasks: list[dict]) -> list[str]:
    rows = ["| # | Task | Menit | Effort | Impact | Butuh |", "| ---: | --- | ---: | --- | --- | --- |"]
    for t in tasks:
        needs = ", ".join(f"#{d}" for d in t["depends_on"]) or "-"
        rows.append(f"| {t['task_number']} | {t['task_title']} | {t['estimated_minutes']} "
                    f"| {t['effort_level']} | {t['impact_level']} | {needs} |")
    return rows


def main():
    args = parse_args()
    started = datetime.now()
    hari_ini = waktu.hari_ini()
    md: list[str] = [f"# Demo AI GradaTim — {started:%d %B %Y, %H:%M}", ""]

    # ---------------- 1. RENCANA GOAL ----------------
    request = GoalDecompositionRequest(
        judul_goal=args.goal, deskripsi=args.deskripsi, deadline=args.deadline, menit_harian=args.menit,
    )
    md += ["## 1. Rencana goal bulanan → mingguan (FR-2, D4, D11)", "",
           f"- **Goal:** {request.judul_goal}",
           f"- **Deskripsi:** {request.deskripsi}",
           f"- **Hari ini:** {hari_ini.isoformat()} · **Deadline:** {request.deadline.isoformat()}",
           f"- **Waktu luang:** {request.menit_harian} menit/hari"]

    if args.offline:
        rencana = rencana_offline(hari_ini, args.deadline)
        md.append("- **Sumber:** ⚠️ MODE OFFLINE — data contoh buatan tangan, **bukan** hasil LLM")
    else:
        print(f"Memanggil {settings.LLM_MODEL} untuk menyusun rencana... (bisa 10-60 detik)")
        t0 = datetime.now()
        try:
            rencana = rencanakan_goal(request, today=hari_ini)
        except AIServiceError as e:
            cause = f" ({e.__cause__})" if e.__cause__ else ""
            sys.exit(f"\n[GAGAL] {e}{cause}\nCek LLM_API_KEY / LLM_MODEL di backend/.env, atau pakai --offline.")
        elapsed = (datetime.now() - t0).total_seconds()
        md.append(f"- **Sumber:** LLM `{settings.LLM_MODEL}` · waktu respons {elapsed:.1f} detik")

    jumlah_minggu = sum(len(b.minggu) for b in rencana.bulan)
    md += ["", f"Hasil: **{len(rencana.bulan)} target bulanan**, **{jumlah_minggu} target mingguan**, "
               f"**{len(rencana.task_minggu_ini)} task** untuk minggu ke-1.", ""]
    md += rencana_md(rencana)
    md.append("")

    # ---------------- 2 & 3. MOOD → REKOMENDASI ----------------
    scenarios = {"Input manual": [int(x) for x in args.mood.split(",")]} if args.mood else DEFAULT_MOOD_SCENARIOS
    akhir_minggu = rencana.bulan[0].minggu[0].akhir
    # sama seperti mood_service: urgensi dari deadline task (= akhir minggu ke-1), hari ini = hari ke-1
    all_tasks = [{**t.model_dump(), "day_number": (akhir_minggu - hari_ini).days + 1} for t in rencana.task_minggu_ini]
    md += ["## 2. Mood Capacity & Rekomendasi Task (FR-6, FR-7, FR-8)", "",
           f"Kandidat: {len(all_tasks)} task minggu ke-1 (deadline {akhir_minggu:%d/%m}).",
           "Pertanyaan kuesioner (skala 1-5): fokus, tenang, motivasi, cukup tidur, siap menghadapi tugas.",
           "Skor task = kecocokan dengan mood (effort vs impact) + urgensi (deadline paling dekat paling tinggi). "
           "Task hanya dipilih jika semua prasyaratnya (kolom *Butuh*) sudah selesai atau ikut terpilih lebih dulu.", ""]

    for name, answers in scenarios.items():
        mood = MoodAnswers(**dict(zip(MoodAnswers.model_fields, answers)))
        assessment = assess_mood(mood)
        recommended = recommend_tasks(all_tasks, assessment, today_day=1)
        p = assessment.probabilities
        md += [f"### Skenario: {name} — jawaban {answers}", "",
               f"- **Kapasitas:** {assessment.capacity_level} (confidence {assessment.confidence:.0%}; "
               f"LOW {p.LOW:.0%} · MEDIUM {p.MEDIUM:.0%} · HIGH {p.HIGH:.0%})",
               f"- **Total skor mood:** {assessment.total_mood_score}/25 · **maks task:** {assessment.max_tasks}",
               f"- **Pesan ke user:** \"{assessment.recommendation_message}\"",
               f"- **Rekomendasi ({len(recommended)} task, urut prioritas):**", ""]
        md += task_table(recommended)
        md.append("")

    # ---------------- SIMPAN ----------------
    OUTPUT_DIR.mkdir(exist_ok=True)
    stem = f"demo_{started:%Y%m%d_%H%M%S}" + ("_offline" if args.offline else "")
    md_path = OUTPUT_DIR / f"{stem}.md"
    json_path = OUTPUT_DIR / f"{stem}_rencana.json"
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    json_path.write_text(rencana.model_dump_json(indent=2), encoding="utf-8")

    print("\n".join(md))
    print(f"\nTersimpan:\n  {md_path}\n  {json_path}")


if __name__ == "__main__":
    main()
