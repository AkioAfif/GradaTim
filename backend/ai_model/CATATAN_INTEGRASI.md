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

## 2. Pemetaan rencana AI → tabel (D4, D11)

`POST /api/v1/goals/{id_goal}/decompose` memanggil `ai_service.rencanakan_goal()`. Tanggal tidak berasal dari AI:
kerangka minggu (Senin–Minggu, minggu ke-1 mulai hari ini) dan bulan kalender dihitung `app/services/rencana.py`,
AI hanya mengisi judul/tujuan tiap target dan task **minggu ke-1**. Hasilnya (`RencanaGoal`) disimpan
`goal_service.simpan_dekomposisi()`; field task output AI hanya dibaca di `goal_service.tambah_task_ai()`
(dipakai juga nanti saat merinci minggu berikutnya).

| Rencana (`RencanaGoal`) | Kolom DB |
| --- | --- |
| `goal_title` (output AI) | *(tidak dipakai — judul pakai input user `goal.judul_goal`)* |
| `bulan[]` | `milestone` dengan `tipe = "bulanan"`, `id_parent_milestone = NULL` |
| `bulan[].bulan_ke` / `judul` / `deskripsi` | `milestone.urutan` / `judul_milestone` / `deskripsi` (kosong → `NULL`) |
| `bulan[].minggu[-1].akhir` | `milestone.deadline` (23:59) |
| `bulan[].minggu[]` | `milestone` dengan `tipe = "mingguan"`, `id_parent_milestone` = milestone bulanannya |
| `minggu[].minggu_ke` | `milestone.urutan` — nomor minggu sepanjang goal (1, 2, ...), bukan per bulan |
| `minggu[].akhir` | `milestone.deadline` (23:59 hari Minggu, atau deadline goal untuk minggu terakhir) |
| `task_minggu_ini[]` | `task` di bawah milestone mingguan ke-1, `task.deadline` = deadline milestone itu |
| `task_title` / `estimated_minutes` | `task.nama_task` / `task.durasi_estimasi` |
| `effort_level` / `impact_level` | `task.tingkat_effort` / `task.tingkat_impact` |
| `task_number` + `depends_on` | baris `task_dependency` (nomor tak dikenal, diri sendiri, dan duplikat dibuang) |

`GET /api/v1/goals/{id_goal}` mengembalikan milestone datar dalam **urutan pohon** (Bulan 1, minggu-minggunya,
Bulan 2, ...); frontend menyusun pohonnya dari `id_parent_milestone`.

Waktu jadwal sebenarnya berasal dari penjadwal (`POST /api/v1/jadwal/goal/{id_goal}`, FR-4) yang menyimpan sesi
ke `jadwal_task`.

## 3. Mood questionnaire

- `QuestionnaireAnswer.nomor_questionnaire` 1–5 = urutan `[fokus, tenang, motivasi, tidur, siap]`
  (sama dengan field `MoodAnswers.q1_focus` … `q5_readiness`).
- `MoodQuestionnaire.hasil_akhir` = `MoodAssessment.capacity_index` (0 = LOW, 1 = MEDIUM, 2 = HIGH).
- `POST /api/v1/mood` (`app/api/v1/mood.py`): satu hasil per user per tanggal WIB — mengisi ulang di hari yang
  sama **menimpa** hasil lama. `GET /api/v1/mood/hari-ini` menghitung ulang hasil dari jawaban tersimpan.
- Respons keduanya berisi `rekomendasi` (`app/services/mood_service.py`): task yang punya sesi `terjadwal`
  hari ini dibagi menjadi `direkomendasikan` dan `disarankan_ditunda` lewat `recommend_tasks()`.
  Pemetaan ke input `recommend_tasks()`:

  | Input `recommend_tasks()` | Sumber DB |
  | --- | --- |
  | `task_number` | `task.id_task` |
  | `effort_level` / `impact_level` | `task.tingkat_effort` / `tingkat_impact` (kosong → `medium`) |
  | `day_number` (urgensi) | `task.deadline` relatif hari ini (hari ini = hari ke-1) |
  | `depends_on` | `task_dependency`, hanya prasyarat yang belum selesai |

  Prasyarat dianggap selesai jika `task.status = done` **atau** semua sesinya (selain `dilewati`) `selesai`
  — sementara, selama `task.status` belum otomatis `done`.
- **Alur D7 (task tidak hilang):** rekomendasi tidak mengubah jadwal. Setelah user setuju, frontend mengirim
  `id_task` dari `disarankan_ditunda` ke `POST /api/v1/jadwal/susun-ulang` sebagai `{"ditunda": [...]}`;
  sesinya dipindah mulai besok di minggu yang sama. Contoh lengkap: `tests/test_alur_mood_jadwal.py`.

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
- **Belum dikerjakan (D11):** merinci task minggu ke-2 dst. sesuai progres, dan penjadwal yang hanya mengambil
  task dari minggu yang sudah tiba. Lihat `docs/KEPUTUSAN_DESAIN_PENJADWALAN.md`.
- Tanggal "hari ini" untuk AI decomposer selalu tanggal WIB (`app.core.waktu.hari_ini()`), bukan tanggal server.
- LLM default sekarang **Google Gemini** (free tier), via OpenAI-compatible API. Diatur lewat
  `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` di `.env` (menggantikan `OPENAI_API_KEY`).
  Bagian 8 di `docs/PROJECT_SPECIFICATIONS.md` masih menyebut `OPENAI_API_KEY` — perlu disesuaikan.
  Variabel lama di `.env` tidak bikin error (config memakai `extra="ignore"`).
