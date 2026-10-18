# Catatan Integrasi AI ↔ Database

> Catatan dari Argya tentang bagaimana output fitur AI disimpan ke database.
> Struktur tabel lengkap ada di `docs/ERD_v2.md` (pemilik `app/models/`: Akio).

## 1. Effort & impact task — sudah ada (ERD v2)

`task.tingkat_effort` dan `task.tingkat_impact` (nullable, `"low" | "medium" | "high"`) diisi dari
`effort_level` / `impact_level` output AI decomposer. Dipakai `filter_tasks_by_capacity()` (FR-7) dan
tampilan Effort vs Impact (FR-9). Task manual tanpa nilai dianggap `medium` oleh `recommend_tasks()`.

## 1b. Dependensi antar task — sudah ada (ERD v2)

`task_number` dan `depends_on` output AI disimpan sebagai baris tabel `task_dependency`
(`id_task`, `id_task_prasyarat`). `task.id_parent_task` tetap untuk hierarki **sub-task**, bukan prasyarat.
Penjadwal membaca tabel ini lewat `jadwal_service.prasyarat_task()`.

## 2. Pemetaan output AI → tabel

Pemetaan hanya ada di **satu tempat**: `app/services/goal_service.simpan_dekomposisi()`
(dipanggil `POST /api/v1/goals/{id_goal}/decompose`). Kalau bentuk output AI berubah, cukup fungsi itu yang diganti.

| Output AI (`GoalDecomposition`) | Kolom DB |
| --- | --- |
| `goal_title` | *(tidak dipakai — judul pakai input user `goal.judul_goal`)* |
| `milestones[].milestone_title` | `milestone.judul_milestone` |
| `milestones[].order` | `milestone.urutan` |
| — | `milestone.tipe` = `NULL`, `milestone.id_parent_milestone` = `NULL` *(datar dulu, lihat poin 4)* |
| — | `milestone.deadline` = deadline task terakhir di milestone tersebut |
| `tasks[].task_title` | `task.nama_task` |
| `tasks[].estimated_minutes` | `task.durasi_estimasi` |
| `tasks[].day_number` | `task.deadline` = 23:59 pada hari ini + (`day_number` − 1) hari |
| `tasks[].effort_level` / `impact_level` | `task.tingkat_effort` / `task.tingkat_impact` |
| `tasks[].task_number` + `depends_on` | baris `task_dependency` (nomor tak dikenal, diri sendiri, dan duplikat dibuang) |

Waktu jadwal sebenarnya **bukan** dari `day_number`, tapi dari penjadwal (`POST /api/v1/jadwal/goal/{id_goal}`,
FR-4) yang menyimpan sesi ke `jadwal_task`.

## 3. Mood questionnaire

- `QuestionnaireAnswer.nomor_questionnaire` 1–5 = urutan `[fokus, tenang, motivasi, tidur, siap]`
  (sama dengan field `MoodAnswers.q1_focus` … `q5_readiness`).
- `MoodQuestionnaire.hasil_akhir` = `MoodAssessment.capacity_index` (0 = LOW, 1 = MEDIUM, 2 = HIGH).
- Endpoint kuesioner mood belum ada.

## 4. Hal teknis lain

- **File model `mood_model.pkl` sudah di-commit**, jadi backend & Docker langsung bisa memakainya.
  Untuk melatih ulang:
  ```bash
  pip install -r ai_model/requirements-train.txt
  python ai_model/train_model.py
  ```
  Versi `scikit-learn` saat training dan saat runtime sebaiknya sama (pickle tidak dijamin kompatibel antar versi).
- `menit_harian` untuk AI decomposer dihitung otomatis oleh `goal_service.hitung_menit_harian()`
  (= `scheduler.average_daily_minutes(jam_aktif, kegiatan_rutin)`, keputusan D6/D10), atau bisa di-override
  lewat body request `/decompose`.
- **Belum dikerjakan (D4/D11):** output AI bertingkat bulanan → mingguan → task, dipetakan ke
  `milestone.tipe` + `milestone.id_parent_milestone`. Lihat `docs/KEPUTUSAN_DESAIN_PENJADWALAN.md`.
- Tanggal "hari ini" untuk AI decomposer selalu tanggal WIB (`app.core.waktu.hari_ini()`), bukan tanggal server.
- LLM default sekarang **Google Gemini** (free tier), via OpenAI-compatible API. Diatur lewat
  `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` di `.env` (menggantikan `OPENAI_API_KEY`).
  Bagian 8 di `docs/PROJECT_SPECIFICATIONS.md` masih menyebut `OPENAI_API_KEY` — perlu disesuaikan.
  Variabel lama di `.env` tidak bikin error (config memakai `extra="ignore"`).
