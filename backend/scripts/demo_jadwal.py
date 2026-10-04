"""
demo_jadwal.py — Demo penjadwal otomatis GradaTim (untuk laporan / bukti pekerjaan)

Alur:
    1. Ambil hasil Goal Decomposition yang sudah tersimpan (JSON dari demo_ai.py) — tanpa memanggil LLM
    2. Hitung slot luang = jam aktif − kegiatan rutin − agenda (keputusan D10)
    3. Jadwalkan task otomatis, merata per hari (FR-4)
    4. Validasi tidak ada bentrok (FR-5)
    5. Simulasi re-planning (FR-11): ada sesi terlewat + task ditunda karena mood LOW

Data jam aktif, kegiatan rutin, dan agenda di bawah adalah CONTOH untuk demo.
Hasil dicetak ke console dan disimpan ke scripts/demo_output/jadwal_<waktu>.md

Cara pakai (dari folder backend/, venv aktif):
    python scripts/demo_jadwal.py
    python scripts/demo_jadwal.py --json scripts/demo_output/demo_xxx_decomposition.json --mulai 2026-10-05
"""

import argparse
import math
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.stdout.reconfigure(encoding="utf-8")

from app.schemas.ai_decomposition import GoalDecomposition  # noqa: E402
from app.services.scheduler import (  # noqa: E402
    BusyBlock,
    Interval,
    Session,
    TaskToSchedule,
    WeeklyWindow,
    busy_blocks,
    free_slots,
    replan,
    schedule_tasks,
    validate_schedule,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "demo_output"
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
SEN, SEL, RAB, KAM, JUM, SAB, MIN = range(7)

# ---------------- DATA CONTOH ----------------
JAM_AKTIF = [WeeklyWindow(d, time(8), time(21)) for d in range(7)]
KEGIATAN_RUTIN = (
    [WeeklyWindow(d, time(8), time(15), label="Kuliah") for d in (SEN, SEL, RAB, KAM)]
    + [WeeklyWindow(JUM, time(8), time(11), label="Kuliah")]
    + [WeeklyWindow(d, time(16), time(17, 30), label="Gym") for d in (SEL, KAM)]
    + [WeeklyWindow(MIN, time(8), time(12), label="Quality time keluarga")]
)


def parse_args():
    latest = sorted(OUTPUT_DIR.glob("demo_*_decomposition.json"))
    today = date.today()
    next_monday = today + timedelta(days=(7 - today.weekday()) % 7 or 7)
    parser = argparse.ArgumentParser(description="Demo penjadwal otomatis GradaTim")
    parser.add_argument("--json", type=Path, default=latest[-1] if latest else None,
                        help="Hasil dekomposisi dari demo_ai.py (default: yang terbaru)")
    parser.add_argument("--mulai", type=date.fromisoformat, default=next_monday,
                        help="Tanggal mulai goal, sebaiknya hari Senin (default: Senin depan)")
    args = parser.parse_args()
    if args.json is None:
        sys.exit("Belum ada hasil dekomposisi. Jalankan dulu: python scripts/demo_ai.py")
    return args


def fmt_iv(i: Interval) -> str:
    return f"{HARI[i.start.weekday()]} {i.start:%d/%m %H:%M}–{i.end:%H:%M}"


def calendar_md(start: datetime, end: datetime, sessions, blocks, titles) -> list[str]:
    items = defaultdict(list)
    for b in blocks:
        if b.kind != "task":
            icon = "📚" if b.kind == "rutin" else "📌"
            items[b.interval.start.date()].append((b.interval, f"{icon} {b.label}"))
    for s in sessions:
        mark = "✅" if s.done else "🎯"
        items[s.interval.start.date()].append(
            (s.interval, f"{mark} **#{s.task_number} {titles[s.task_number]}** ({s.interval.minutes} mnt)"))

    lines = ["| Hari | Jam | Kegiatan |", "| --- | --- | --- |"]
    day = start.date()
    while day < end.date():
        entries = sorted(items.get(day, []), key=lambda e: e[0].start)
        label = f"{HARI[day.weekday()]} {day:%d/%m}"
        if not entries:
            lines.append(f"| {label} | | *(kosong)* |")
        for i, (iv, text) in enumerate(entries):
            lines.append(f"| {label if i == 0 else ''} | {iv.start:%H:%M}–{iv.end:%H:%M} | {text} |")
        day += timedelta(days=1)
    return lines


def load_md(sessions) -> list[str]:
    load = defaultdict(int)
    for s in sessions:
        load[s.interval.start.date()] += s.interval.minutes
    return [", ".join(f"{HARI[d.weekday()][:3]} {d:%d/%m}: {m} mnt" for d, m in sorted(load.items()))]


def main():
    args = parse_args()
    decomposition = GoalDecomposition.model_validate_json(args.json.read_text(encoding="utf-8"))
    tasks_raw = [t for m in decomposition.milestones for t in m.tasks]
    titles = {t.task_number: t.task_title for t in tasks_raw}

    start = datetime.combine(args.mulai, time.min)
    weeks = math.ceil(decomposition.estimated_total_days / 7)
    end = start + timedelta(days=7 * weeks)
    agenda = [BusyBlock(Interval(start + timedelta(days=RAB, hours=19), start + timedelta(days=RAB, hours=21)),
                        "agenda", "Rapat himpunan")]

    md = [f"# Demo Penjadwal GradaTim — {datetime.now():%d %B %Y, %H:%M}", "",
          f"- **Goal:** {decomposition.goal_title} ({len(tasks_raw)} task, sumber: `{args.json.name}`)",
          f"- **Periode:** {args.mulai:%d/%m/%Y} – {(end - timedelta(days=1)):%d/%m/%Y} ({weeks} minggu)",
          "- **Jam aktif (contoh):** 08:00–21:00 setiap hari",
          "- **Kegiatan rutin (contoh):** Kuliah Sen–Kam 08–15 & Jum 08–11 · Gym Sel & Kam 16:00–17:30 · "
          "Quality time keluarga Min 08–12",
          f"- **Agenda (contoh):** Rapat himpunan {fmt_iv(agenda[0].interval)}", ""]

    # ---------------- 1. JADWAL OTOMATIS (FR-4) ----------------
    blocks = busy_blocks(start, end, KEGIATAN_RUTIN, agenda)
    slots = free_slots(JAM_AKTIF, start, end, busy=[b.interval for b in blocks])
    tasks = [TaskToSchedule(t.task_number, t.estimated_minutes, tuple(t.depends_on),
                            earliest=start + timedelta(days=t.day_number - 1)) for t in tasks_raw]
    result = schedule_tasks(tasks, slots)
    conflicts = validate_schedule(result.sessions, blocks)

    md += ["## 1. Jadwal otomatis (FR-4) & cek bentrok (FR-5)", "",
           f"- Slot luang tersedia: **{sum(s.minutes for s in slots) // 60} jam**; "
           f"total task: **{sum(t.minutes for t in tasks)} menit**",
           f"- Batas beban harian (merata, D5): **{result.daily_cap_minutes} menit/hari**",
           f"- Task tidak muat: **{len(result.unscheduled)}** {result.unscheduled or ''}",
           f"- Bentrok dengan kuliah/gym/agenda/sesi lain: **{len(conflicts)}**", ""]
    md += calendar_md(start, end, result.sessions, blocks, titles)
    md += ["", "Beban per hari: " + load_md(result.sessions)[0], ""]

    # ---------------- 2. RE-PLANNING (FR-11) ----------------
    now = start + timedelta(days=RAB, hours=7)  # Rabu pagi minggu pertama
    before = result.sessions
    sessions = [Session(s.task_number, s.interval, done=s.interval.start.weekday() == SEN and s.interval.end <= now)
                for s in before]
    done_tasks = sorted({s.task_number for s in sessions if s.done})
    missed = sorted({s.task_number for s in sessions if not s.done and s.interval.end <= now})
    today_tasks = sorted({s.task_number for s in sessions if s.interval.start.date() == now.date()})
    depends_on = {t.task_number: tuple(t.depends_on) for t in tasks_raw}

    re = replan(sessions, slots, now, depends_on=depends_on, deferred=today_tasks)
    re_conflicts = validate_schedule(re.sessions, blocks)

    md += ["## 2. Re-planning (FR-11)", "",
           f"Skenario: sekarang **{HARI[now.weekday()]} {now:%d/%m %H:%M}**. "
           f"Task Senin {done_tasks} sudah dikerjakan, task Selasa {missed} **terlewat**, "
           f"dan pagi ini mood user **LOW** sehingga task hari ini {today_tasks} **ditunda** (D7).", "",
           f"- Task dijadwalkan ulang: **{re.rescheduled}**",
           f"- Tidak muat lagi (user memilih konsekuensi, D12): **{re.unscheduled or '-'}**",
           f"- Bentrok setelah re-planning: **{len(re_conflicts)}**", "",
           "| Task | Jadwal lama | Jadwal baru |", "| --- | --- | --- |"]
    for n in re.rescheduled + re.unscheduled:
        old = "<br>".join(fmt_iv(s.interval) for s in before if s.task_number == n)
        new = "<br>".join(fmt_iv(s.interval) for s in re.sessions if s.task_number == n) or "*(tidak muat)*"
        md.append(f"| #{n} {titles[n]} | {old} | {new} |")
    md += ["", "### Kalender setelah re-planning", ""]
    md += calendar_md(start, end, re.sessions, blocks, titles)
    md += ["", "Beban per hari: " + load_md(re.sessions)[0], ""]

    OUTPUT_DIR.mkdir(exist_ok=True)
    out = OUTPUT_DIR / f"jadwal_{datetime.now():%Y%m%d_%H%M%S}.md"
    out.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    print(f"\nTersimpan: {out}")


if __name__ == "__main__":
    main()
