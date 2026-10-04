# Panduan Uji Coba Fitur AI & Penjadwal GradaTim

> Panduan langkah demi langkah untuk mencoba sendiri semua fitur AI dan penjadwal yang sudah dibuat,
> supaya paham perilakunya dengan data nyata. Semua perintah untuk **Windows PowerShell**.
>
> Fitur ini **belum** punya endpoint API, database, maupun tampilan web — semuanya dicoba lewat
> skrip dan Python langsung.

| Fitur | FR | Cara mencoba |
| :--- | :--- | :--- |
| Goal Decomposition (Gemini) | FR-2 | [Langkah 4](#4-goal-decomposition--rekomendasi-mood) |
| Prediksi kapasitas mood & rekomendasi task | FR-6, FR-7, FR-8 | [Langkah 4](#4-goal-decomposition--rekomendasi-mood), [Langkah 6A](#a-mood--rekomendasi-task) |
| Penjadwalan otomatis | FR-4 | [Langkah 5](#5-penjadwal-otomatis), [Langkah 6B](#b-penjadwal-dengan-jadwalmu-sendiri) |
| Deteksi bentrok | FR-5 | [Langkah 6C](#c-cek-bentrok-saat-memindah-jadwal) |
| Re-planning task terlewat / ditunda | FR-11 | [Langkah 5](#5-penjadwal-otomatis), [Langkah 6D](#d-re-planning) |

---

## 1. Persiapan (sekali saja)

Butuh **Python 3.11+** (`python --version`). Semua perintah dijalankan dari folder **`backend`**:

```powershell
cd "D:\...\GradaTim\backend"
git pull
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r ai_model\requirements-train.txt
```

`requirements-train.txt` sudah termasuk semua isi `requirements.txt` + library untuk training model.
Kalau folder `venv` sudah ada, cukup jalankan baris `pip install` (untuk mengambil library baru).

> 💡 Panduan ini selalu memakai `.\venv\Scripts\python.exe` supaya tidak perlu mengaktifkan venv.
> Kalau lebih suka mengaktifkan dulu (`.\venv\Scripts\Activate`), ganti `.\venv\Scripts\python.exe` dengan `python`.

## 2. API key Gemini (gratis)

1. Buka https://aistudio.google.com/apikey, login akun Google, klik **Create API key**.
2. Salin template konfigurasi lalu isi key-nya:
   ```powershell
   copy .env.example .env
   notepad .env
   ```
3. Isi baris `LLM_API_KEY=...` dengan key-mu, simpan. `.env` tidak ikut ter-commit (sudah di-`.gitignore`).

Hanya Langkah 4 yang butuh API key. Langkah lain jalan tanpa internet.

## 3. Unit test — cek semuanya sehat

```powershell
.\venv\Scripts\python.exe -m pytest -v
```

Hasil yang diharapkan: semua `PASSED` (67 tes). Nama tesnya sengaja deskriptif — membaca daftar ini
saja sudah memberi gambaran aturan yang dijamin, mis. `test_replan_deferred_by_mood_moves_to_tomorrow`.

## 4. Goal Decomposition + rekomendasi mood

```powershell
.\venv\Scripts\python.exe scripts\demo_ai.py
```

Yang terjadi: goal contoh ("Belajar Docker & CI/CD") dipecah Gemini jadi milestone & task, lalu
3 skenario mood (kurang prima / biasa / prima) masing-masing diberi rekomendasi task.
Hasil tersimpan di `scripts\demo_output\demo_<waktu>.md` + `..._decomposition.json`.

**Coba variasi ini** dan perhatikan bedanya:

```powershell
# goal-mu sendiri
.\venv\Scripts\python.exe scripts\demo_ai.py --goal "Lulus TOEFL 550" --deskripsi "Skor sekarang 480" --deadline 2026-12-15 --menit 90

# deadline sangat mepet: apa yang AI lakukan kalau waktunya tidak masuk akal?
.\venv\Scripts\python.exe scripts\demo_ai.py --goal "Bikin website portofolio" --deadline 2026-10-07 --menit 30

# mood-mu hari ini (fokus, tenang, motivasi, tidur, siap — masing-masing 1-5)
.\venv\Scripts\python.exe scripts\demo_ai.py --mood 3,2,4,2,3

# simulasi hari ke-5: task hari 1-4 dianggap selesai
.\venv\Scripts\python.exe scripts\demo_ai.py --hari 5

# tanpa API key / internet: data contoh (BUKAN hasil AI)
.\venv\Scripts\python.exe scripts\demo_ai.py --offline
```

Hal yang menarik diamati:
- Apakah pecahan task dari AI masuk akal untuk goal-mu? Apakah durasinya realistis?
- Kolom **Butuh** (dependensi): apakah AI membuat rantai lurus (tiap task butuh task sebelumnya)?
- Rekomendasi mood LOW vs HIGH: apakah jumlah dan jenis task-nya berbeda?
- Jalankan goal yang sama 2 kali — hasil AI tidak selalu sama.

## 5. Penjadwal otomatis

```powershell
.\venv\Scripts\python.exe scripts\demo_jadwal.py
```

Memakai hasil dekomposisi **terbaru** dari Langkah 4 (tanpa memanggil AI lagi), lalu:
1. menjadwalkan task ke kalender 2 minggu di sekitar contoh jadwal kuliah, gym, dan rapat;
2. memastikan tidak ada bentrok;
3. mensimulasikan Rabu pagi: task Selasa terlewat dan mood user LOW → jadwal disusun ulang.

Hasil tersimpan di `scripts\demo_output\jadwal_<waktu>.md` — paling enak dibuka di VS Code
dengan **Markdown Preview** (`Ctrl+Shift+V`) supaya tabelnya rapi.

Opsi:
```powershell
# pakai hasil dekomposisi tertentu & tanggal mulai tertentu
.\venv\Scripts\python.exe scripts\demo_jadwal.py --json scripts\demo_output\demo_20260925_061008_decomposition.json --mulai 2026-10-05
```

Jadwal kuliah/gym contohnya ada di bagian atas `scripts\demo_jadwal.py` (`JAM_AKTIF`,
`KEGIATAN_RUTIN`) — silakan ganti dengan jadwalmu sendiri, **asal jangan di-commit**.

## 6. Bereksperimen langsung di Python

Untuk mencoba skenario sendiri tanpa mengubah skrip, buka Python interaktif dari folder `backend`:

```powershell
.\venv\Scripts\python.exe
```

Lalu tempel (paste) blok-blok kode di bawah. Ketik `exit()` untuk keluar.

### A. Mood & rekomendasi task

```python
from app.schemas.mood import MoodAnswers
from app.services.ai_service import assess_mood, recommend_tasks

hasil = assess_mood(MoodAnswers(q1_focus=2, q2_calm=3, q3_motivated=2, q4_sleep=1, q5_readiness=3))
print(hasil.capacity_level, hasil.max_tasks, hasil.confidence)
print(hasil.recommendation_message)

tasks = [
    {"task_number": 1, "task_title": "Install Docker", "day_number": 1, "effort_level": "medium", "impact_level": "high", "depends_on": []},
    {"task_number": 2, "task_title": "Hello-world", "day_number": 2, "effort_level": "low", "impact_level": "high", "depends_on": [1]},
    {"task_number": 3, "task_title": "Baca artikel CI/CD", "day_number": 1, "effort_level": "low", "impact_level": "low", "depends_on": []},
]
for t in recommend_tasks(tasks, hasil, today_day=1):
    print("-", t["task_title"])
```

Coba ubah jawaban mood (1-5), `effort_level`/`impact_level`, atau hapus `depends_on` task 2 —
lihat bagaimana urutan rekomendasi berubah.

### B. Penjadwal dengan jadwalmu sendiri

```python
from datetime import datetime, time
from app.services.scheduler import (
    Interval, TaskToSchedule, WeeklyWindow,
    busy_blocks, find_conflicts, free_slots, replan, schedule_tasks,
)

SEN, SEL, RAB, KAM, JUM, SAB, MIN = range(7)
jam_aktif = [WeeklyWindow(hari, time(8), time(21)) for hari in range(7)]
rutin = [
    WeeklyWindow(SEN, time(8), time(15), label="Kuliah"),
    WeeklyWindow(SEL, time(8), time(15), label="Kuliah"),
    WeeklyWindow(RAB, time(16), time(18), label="Gym"),
]
mulai, akhir = datetime(2026, 10, 5), datetime(2026, 10, 12)   # Senin s/d Senin berikutnya

slots = free_slots(jam_aktif, mulai, akhir, rutin)
tasks = [
    TaskToSchedule(1, 60),                      # task #1, 60 menit
    TaskToSchedule(2, 90, depends_on=(1,)),     # task #2, 90 menit, butuh task #1
    TaskToSchedule(3, 45),
]
jadwal = schedule_tasks(tasks, slots)
for s in jadwal.sessions:
    print(f"Task #{s.task_number}: {s.interval.start:%a %d/%m %H:%M} - {s.interval.end:%H:%M}")
print("Tidak muat:", jadwal.unscheduled)
print("Batas harian:", jadwal.daily_cap_minutes, "menit")
```

Eksperimen yang disarankan:
- Tambah banyak task (mis. 10 task × 60 menit) — bagaimana pembagiannya per hari?
- Perbesar satu task jadi 300 menit — task itu akan dipecah ke beberapa sesi.
- Persempit `jam_aktif` atau tambah kegiatan rutin sampai task **tidak muat** — lihat `unscheduled`.

### C. Cek bentrok saat memindah jadwal

Lanjutan dari blok B:

```python
blok = busy_blocks(mulai, akhir, rutin, sessions=jadwal.sessions)
coba = Interval(datetime(2026, 10, 5, 14), datetime(2026, 10, 5, 16))   # Senin 14:00-16:00
for c in find_conflicts(coba, blok):
    print(c.message)
```

Ubah jam di `coba` — jika tidak ada output, berarti aman (tidak bentrok).

### D. Re-planning

Lanjutan dari blok B. Misalkan sekarang Rabu pagi dan belum ada task yang dikerjakan:

```python
sekarang = datetime(2026, 10, 7, 7)
baru = replan(jadwal.sessions, slots, sekarang, depends_on={2: (1,)})
for s in baru.sessions:
    print(f"Task #{s.task_number}: {s.interval.start:%a %d/%m %H:%M} - {s.interval.end:%H:%M}")
print("Dipindah:", baru.rescheduled, "| Tidak muat:", baru.unscheduled)
```

Coba juga:
- Tandai sesi Senin sudah dikerjakan: ganti `jadwal.sessions` dengan
  `[Session(s.task_number, s.interval, done=(s.interval.start.day == 5)) for s in jadwal.sessions]`
  (tambahkan `Session` ke import di blok B).
- Tunda task karena mood: tambahkan `deferred=[2]` ke `replan(...)` — task #2 yang terjadwal hari Rabu
  (hari "sekarang") digeser ke Kamis atau sesudahnya. `deferred` hanya berlaku untuk task yang
  terjadwal **hari ini**; task yang sudah lewat otomatis dipindah tanpa perlu `deferred`.
- Set `sekarang` ke Minggu malam — task yang tidak muat lagi masuk `unscheduled` (nanti user memilih konsekuensinya, keputusan D12).

## 7. Kendala umum

| Gejala | Penyebab & solusi |
| :--- | :--- |
| `The term '.\venv\Scripts\python.exe' is not recognized` | Belum berada di folder `backend`. Jalankan `cd backend` dulu. |
| `Activate ... cannot be loaded because running scripts is disabled` | Kebijakan PowerShell. Pakai `.\venv\Scripts\python.exe` langsung (tidak perlu Activate), atau sekali saja: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. |
| `ModuleNotFoundError` | Library belum terpasang di venv: ulangi `pip install` di Langkah 1. |
| `[GAGAL] LLM_API_KEY belum diset` | `.env` belum ada / key belum diisi (Langkah 2). |
| `Error code: 503 ... high demand` | Server Gemini sedang penuh. Tunggu beberapa menit, atau ganti `LLM_MODEL` di `.env` (mis. `gemini-3.5-flash-lite`). |
| `Error code: 429` | Kuota gratis habis. Tunggu (biasanya reset harian) atau pakai model lain. |
| `Belum ada hasil dekomposisi` saat `demo_jadwal.py` | Jalankan Langkah 4 dulu, atau pakai `--json` ke file yang sudah ada. |
| Tabel di file `.md` berantakan | Buka dengan Markdown Preview di VS Code (`Ctrl+Shift+V`). |

## Referensi

- Keputusan desain penjadwalan: `docs/KEPUTUSAN_DESAIN_PENJADWALAN.md`
- Catatan integrasi AI ↔ database: `backend/ai_model/CATATAN_INTEGRASI.md`
- Kode: `backend/app/services/ai_service.py`, `backend/app/services/scheduler.py`, `backend/ai_model/mood_predictor.py`
