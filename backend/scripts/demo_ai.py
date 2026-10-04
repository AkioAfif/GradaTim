"""
demo_ai.py — Demo end-to-end fitur AI GradaTim (untuk laporan / bukti pekerjaan)

Alur:
    1. Goal Decomposition (FR-2): goal + deadline dipecah LLM jadi milestone & task harian
    2. Mood Capacity (FR-6): beberapa skenario jawaban kuesioner diprediksi kapasitasnya
    3. Rekomendasi task (FR-7, FR-8): task dipilih sesuai kapasitas mood, urgensi (jadwal
       paling dekat/terlambat didahulukan), dan dependensi (prasyarat harus selesai dulu)

Hasil dicetak ke console dan disimpan ke scripts/demo_output/ (Markdown + JSON).

Cara pakai (dari folder backend/, venv aktif):
    python scripts/demo_ai.py
    python scripts/demo_ai.py --goal "Lulus TOEFL 550" --deadline 2026-11-30 --menit 90
    python scripts/demo_ai.py --mood 2,2,3,1,2          # satu skenario mood saja
    python scripts/demo_ai.py --hari 5                  # simulasi hari ke-5 (task hari 1-4 dianggap selesai)
    python scripts/demo_ai.py --offline                 # tanpa API key (data contoh, BUKAN dari LLM)
"""

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.stdout.reconfigure(encoding="utf-8")

from app.core.config import settings  # noqa: E402
from app.schemas.ai_decomposition import GoalDecomposition, GoalDecompositionRequest  # noqa: E402
from app.schemas.mood import MoodAnswers  # noqa: E402
from app.services.ai_service import AIServiceError, assess_mood, decompose_goal, recommend_tasks  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / "demo_output"

DEFAULT_MOOD_SCENARIOS = {
    "Kurang tidur & cemas": [2, 1, 2, 1, 2],
    "Biasa saja": [3, 3, 4, 3, 3],
    "Sangat prima": [5, 4, 5, 5, 4],
}

# Hanya dipakai dengan --offline. Ditandai jelas di output agar tidak tertukar dengan hasil LLM.
OFFLINE_SAMPLE = {
    "goal_title": "Belajar Docker & CI/CD dalam 2 Minggu",
    "estimated_total_days": 12,
    "milestones": [
        {"milestone_title": "Dasar containerization", "order": 1, "tasks": [
            {"task_number": 1, "depends_on": [], "task_title": "Install Docker Desktop & verifikasi CLI", "day_number": 1, "estimated_minutes": 30, "effort_level": "low", "impact_level": "high"},
            {"task_number": 2, "depends_on": [1], "task_title": "Pelajari konsep image, container, dan volume", "day_number": 2, "estimated_minutes": 45, "effort_level": "medium", "impact_level": "high"},
            {"task_number": 3, "depends_on": [2], "task_title": "Buat Dockerfile untuk aplikasi FastAPI sederhana", "day_number": 3, "estimated_minutes": 60, "effort_level": "high", "impact_level": "high"},
        ]},
        {"milestone_title": "Multi-container dengan Compose", "order": 2, "tasks": [
            {"task_number": 4, "depends_on": [3], "task_title": "Baca dokumentasi docker-compose.yml", "day_number": 4, "estimated_minutes": 30, "effort_level": "low", "impact_level": "medium"},
            {"task_number": 5, "depends_on": [4], "task_title": "Jalankan FastAPI + PostgreSQL dengan Compose", "day_number": 5, "estimated_minutes": 60, "effort_level": "high", "impact_level": "high"},
            {"task_number": 6, "depends_on": [], "task_title": "Rapikan catatan perintah Docker yang sering dipakai", "day_number": 6, "estimated_minutes": 20, "effort_level": "low", "impact_level": "low"},
        ]},
        {"milestone_title": "Otomasi dengan GitHub Actions", "order": 3, "tasks": [
            {"task_number": 7, "depends_on": [5], "task_title": "Buat workflow lint & test sederhana", "day_number": 8, "estimated_minutes": 45, "effort_level": "medium", "impact_level": "high"},
            {"task_number": 8, "depends_on": [7], "task_title": "Tambahkan build image Docker di workflow", "day_number": 10, "estimated_minutes": 60, "effort_level": "high", "impact_level": "medium"},
            {"task_number": 9, "depends_on": [8], "task_title": "Review ulang seluruh pipeline & tulis ringkasan", "day_number": 12, "estimated_minutes": 30, "effort_level": "medium", "impact_level": "low"},
        ]},
    ],
}


def parse_args():
    parser = argparse.ArgumentParser(description="Demo AI GradaTim: goal decomposition + mood recommendation")
    parser.add_argument("--goal", default="Belajar Docker & CI/CD untuk project kuliah")
    parser.add_argument("--deskripsi", default="Saya baru paham dasar Python dan Git, belum pernah pakai Docker.")
    parser.add_argument("--deadline", type=date.fromisoformat, default=date.today() + timedelta(days=13),
                        help="Format YYYY-MM-DD (default: 2 minggu dari hari ini)")
    parser.add_argument("--menit", type=int, default=60, help="Waktu luang per hari dalam menit")
    parser.add_argument("--mood", help="5 angka 1-5 dipisah koma: fokus,tenang,motivasi,tidur,siap")
    parser.add_argument("--hari", type=int, default=1,
                        help="Simulasi hari ke-N sejak goal dibuat; task dengan hari < N dianggap selesai")
    parser.add_argument("--offline", action="store_true", help="Pakai data contoh, tanpa memanggil LLM")
    return parser.parse_args()


def flatten_tasks(decomposition: GoalDecomposition) -> list[dict]:
    return [
        {**task.model_dump(), "milestone": milestone.milestone_title}
        for milestone in decomposition.milestones
        for task in milestone.tasks
    ]


def task_table(tasks: list[dict], with_milestone: bool = True) -> list[str]:
    header = "| # | Hari | Task | Menit | Effort | Impact | Butuh |" + (" Milestone |" if with_milestone else "")
    sep = "| ---: | ---: | --- | ---: | --- | --- | --- |" + (" --- |" if with_milestone else "")
    rows = [header, sep]
    for t in tasks:
        needs = ", ".join(f"#{d}" for d in t["depends_on"]) or "-"
        row = (f"| {t['task_number']} | {t['day_number']} | {t['task_title']} | {t['estimated_minutes']} "
               f"| {t['effort_level']} | {t['impact_level']} | {needs} |")
        rows.append(row + (f" {t['milestone']} |" if with_milestone else ""))
    return rows


def main():
    args = parse_args()
    started = datetime.now()
    md: list[str] = [f"# Demo AI GradaTim — {started:%d %B %Y, %H:%M}", ""]

    # ---------------- 1. GOAL DECOMPOSITION ----------------
    request = GoalDecompositionRequest(
        judul_goal=args.goal, deskripsi=args.deskripsi, deadline=args.deadline, menit_harian=args.menit,
    )
    md += ["## 1. Goal Decomposition (FR-2)", "",
           f"- **Goal:** {request.judul_goal}",
           f"- **Deskripsi:** {request.deskripsi}",
           f"- **Hari ini:** {date.today().isoformat()} · **Deadline:** {request.deadline.isoformat()}",
           f"- **Waktu luang:** {request.menit_harian} menit/hari"]

    if args.offline:
        decomposition = GoalDecomposition.model_validate(OFFLINE_SAMPLE)
        md.append("- **Sumber:** ⚠️ MODE OFFLINE — data contoh buatan tangan, **bukan** hasil LLM")
    else:
        print(f"Memanggil {settings.LLM_MODEL} untuk memecah goal... (bisa 10-60 detik)")
        t0 = datetime.now()
        try:
            decomposition = decompose_goal(request)
        except AIServiceError as e:
            cause = f" ({e.__cause__})" if e.__cause__ else ""
            sys.exit(f"\n[GAGAL] {e}{cause}\nCek LLM_API_KEY / LLM_MODEL di backend/.env, atau pakai --offline.")
        elapsed = (datetime.now() - t0).total_seconds()
        md.append(f"- **Sumber:** LLM `{settings.LLM_MODEL}` · waktu respons {elapsed:.1f} detik")

    all_tasks = flatten_tasks(decomposition)
    md += ["", f"Hasil: **{len(decomposition.milestones)} milestone**, **{len(all_tasks)} task**, "
               f"estimasi {decomposition.estimated_total_days} hari.", ""]
    for m in decomposition.milestones:
        md += [f"### Milestone {m.order}: {m.milestone_title}", ""]
        md += task_table([{**t.model_dump(), "milestone": m.milestone_title} for t in m.tasks], with_milestone=False)
        md.append("")

    # ---------------- 2 & 3. MOOD → REKOMENDASI ----------------
    if args.mood:
        scenarios = {"Input manual": [int(x) for x in args.mood.split(",")]}
    else:
        scenarios = DEFAULT_MOOD_SCENARIOS

    for t in all_tasks:
        t["status"] = "done" if t["day_number"] < args.hari else "pending"
    n_done = sum(t["status"] == "done" for t in all_tasks)
    md += ["## 2. Mood Capacity & Rekomendasi Task (FR-6, FR-7, FR-8)", "",
           f"Simulasi **hari ke-{args.hari}**: {n_done} task (hari < {args.hari}) dianggap sudah selesai, "
           f"{len(all_tasks) - n_done} task tersisa sebagai kandidat.",
           "Pertanyaan kuesioner (skala 1-5): fokus, tenang, motivasi, cukup tidur, siap menghadapi tugas.",
           "Skor task = kecocokan dengan mood (effort vs impact) + urgensi (jadwal hari ini/terlambat paling tinggi). "
           "Task hanya dipilih jika semua prasyaratnya (kolom *Butuh*) sudah selesai atau ikut terpilih lebih dulu.", ""]

    for name, answers in scenarios.items():
        mood = MoodAnswers(**dict(zip(MoodAnswers.model_fields, answers)))
        assessment = assess_mood(mood)
        recommended = recommend_tasks(all_tasks, assessment, today_day=args.hari)
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
    json_path = OUTPUT_DIR / f"{stem}_decomposition.json"
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    json_path.write_text(decomposition.model_dump_json(indent=2), encoding="utf-8")

    print("\n".join(md))
    print(f"\nTersimpan:\n  {md_path}\n  {json_path}")


if __name__ == "__main__":
    main()
