# Ringkasan Perubahan W6 — Backend (Akio)

## Branch & commit

- **Basis:** `542230@047bb86` (branch yang ter-checkout saat mulai, working tree bersih).
  Branch `542230` belum berisi `scheduler.py`, `test_scheduler.py`, dan `CATATAN_INTEGRASI.md` versi terbaru
  milik Argya, padahal brief W6 bergantung pada file-file itu. Karena `main` lokal (`48043cb`, merge PR #38)
  adalah turunan langsung dari `047bb86` dan hanya menambah file milik Argya, branch kerja di-*fast-forward*
  ke `main@48043cb` (lokal saja, tanpa fetch/pull/push, tanpa rewrite history).
- **Branch kerja:** `w6-backend-crud` (lokal, belum di-push).
- **Daftar commit** (`git log --oneline main..w6-backend-crud`):

```
<commit ini>  W6: ringkasan perubahan (docs/W6_RINGKASAN_PERUBAHAN.md)
e095392 W6 phase 9: ERD v2 documentation
bcece83 W6 phase 7: backend CI workflow
fee9977 W6 phase 6: tasks list + status update + tests
8e75a2e W6 phase 5: goals CRUD + decompose endpoint (single mapping point) + tests
5cfd42f W6 phase 4: CRUD agenda + conflict warning + tests
80c199a W6 phase 3: CRUD time-constraints (kegiatan rutin) + tests
9182699 W6 phase 2: test fixtures + auth API tests
0bcbc0a W6 phase 1: status constants, task default todo, deps & config fixes
```

Phase 8 (verifikasi migrasi) dan phase 10 (verifikasi akhir) tidak menghasilkan commit karena tidak ada yang
perlu diperbaiki.

## Issue yang dikerjakan

### 1. Perbaikan bug & fondasi

**Deskripsi singkat**

- `app/core/status.py` (baru): konstanta status yang disepakati (`todo`/`in_progress`/`done`,
  `terjadwal`/`selesai`/`dilewati`, `active`, tipe milestone `bulanan`/`mingguan`).
- **Bug:** default `Task.status` sebelumnya `"pending"` → sekarang `TASK_TODO` (`"todo"`). `JadwalTask.status`
  dan `Goal.status` memakai konstanta (nilai string sama). Hanya default di sisi Python — migrasi tidak punya
  `server_default` untuk kolom ini (sudah dicek), jadi **tanpa migrasi baru**.
- `JAM_AKTIF_MULAI` / `JAM_AKTIF_SELESAI` (D10) ditambahkan ke `Settings` (default 06:00–22:00) dan
  `.env.example`; string `"07:30"` terbukti terbaca sebagai `datetime.time` (tes).
- `app/core/waktu.py` (baru): `WIB` (offset tetap +7), `ke_wib_naif()`, `hari_ini()`, `akhir_hari()`.
- Komentar `alembic/env.py` diperbarui (7 → 10 tabel); `app/models/__init__.py` sudah mengimpor ke-10 model.
- `.gitignore` backend: ditambah `*.db`, `*.sqlite3`, `.coverage`, `htmlcov/`.
- **Bug (ditemukan di phase 2):** login dengan password > 72 byte menghasilkan **500 Internal Server Error**
  karena `bcrypt` ≥ 5 melempar `ValueError`. `verify_password()` sekarang mengembalikan `False` → 401.
- `pytest.ini` (baru): `SAWarning` SQLAlchemy dijadikan error agar bug ORM tidak lolos diam-diam.

**Kendala yang dihadapi**

- *Dependensi TestClient:* brief meminta `httpx`, tetapi Starlette 1.7 (terpasang lewat FastAPI terbaru)
  memakai **`httpx2`** dan menandai `httpx` sebagai deprecated. Yang ditambahkan ke `requirements.txt` adalah
  `httpx2` (sebelumnya hanya ikut terpasang secara kebetulan lewat `openai`). `fastapi.testclient` terbukti bisa
  dipakai.
- *Driver Postgres:* dugaan bug `postgresql://` → psycopg2 **tidak terjadi** di lingkungan ini:
  SQLAlchemy 2.1.4 sudah memilih psycopg 3 untuk `postgresql://`
  (`create_engine('postgresql://…').dialect.driver == 'psycopg'`). Sesuai brief, validator URL **tidak** dibuat;
  sebagai gantinya ada tes `test_url_postgresql_polos_memakai_driver_psycopg3` yang akan gagal jika SQLAlchemy
  turun ke 2.0. Catatan: skema `postgres://` tetap tidak didukung SQLAlchemy (`NoSuchModuleError`).
- Python lokal 3.14.7 (Dockerfile/CI memakai 3.11). Semua file `app/` dan `tests/` dicek bisa di-parse dengan
  grammar Python 3.11 (`ast.parse(..., feature_version=(3, 11))`).

**Bukti pengerjaan**

```
tests/test_config.py   8 passed
(full suite setelah phase 1) 75 passed
```

### 2. CRUD kegiatan rutin (time_constraint)

**Deskripsi singkat:** `GET/POST /api/v1/time-constraints`, `GET/PATCH/DELETE /api/v1/time-constraints/{id_constraint}`.
Hanya milik user login; baris user lain dijawab **404** (bukan 403). Helper bersama `app/api/common.py`:
`ambil_milik_user()` (milik sendiri atau 404) dan `validasi_gabungan()` (PATCH digabung dengan data tersimpan lalu
divalidasi ulang dengan schema Create → 422 jika tidak valid). Nama di-strip; `hari_dalam_minggu` 0–6; jam mulai ≠
jam selesai; jam selesai < jam mulai diterima (melewati tengah malam, konsisten dengan `scheduler.WeeklyWindow`);
jam ber-timezone ditolak. Daftar diurutkan `hari_dalam_minggu`, `waktu_mulai`.

**Kendala:** tidak ada.

**Bukti:** `tests/test_api_time_constraints.py 24 passed` (CRUD, urutan, 401, 422, lewat tengah malam, PATCH
jam sama → 422, isolasi user A/B, cascade hapus user).

### 3. CRUD agenda + peringatan bentrok (FR-5)

**Deskripsi singkat:** `GET/POST /api/v1/agenda`, `GET/PATCH/DELETE /api/v1/agenda/{id_agenda}`.
Input ber-timezone (mis. `2026-10-07T12:00:00Z`) disimpan sebagai WIB naive (`19:00`). Agenda wajib selesai
setelah mulai dan **di tanggal yang sama** (dicek setelah konversi ke WIB). `GET /agenda?mulai=&sampai=`
mengembalikan agenda yang beririsan dengan `[mulai 00:00, sampai+1 hari 00:00)`; `sampai < mulai` → 422.
Respons POST/PATCH berisi `peringatan_bentrok` (tidak memblokir penyimpanan): logika di
`app/services/kalender_service.py` memakai `scheduler.busy_blocks()` + `scheduler.find_conflicts()` tanpa mengubah
`scheduler.py` — kegiatan rutin user (termasuk yang melewati tengah malam dari hari sebelumnya) dan agenda lain
user di hari itu (agenda yang sedang di-PATCH tidak dihitung). GET selalu mengembalikan list kosong.
Konversi baris DB → objek scheduler (`rutin_ke_window`, `agenda_ke_busy_block`) hanya ada di modul ini.

**Kendala:** `jadwal_service.py` milik rekan belum ada di lokal, jadi helper konversi dibuat di
`kalender_service.py`.

**Bukti:** `tests/test_api_agenda.py 30 passed`, contoh pesan:
`"Bentrok dengan Kuliah (05/10 09:00-10:00, 60 menit)"`.

### 4. CRUD goal + endpoint dekomposisi AI (FR-1, FR-2)

**Deskripsi singkat:**

- `GET/POST /api/v1/goals`, `GET/PATCH/DELETE /api/v1/goals/{id_goal}`. Deadline (tanggal) wajib, tidak boleh di
  masa lalu (`"Deadline tidak boleh di masa lalu"`), disimpan sebagai 23:59 hari itu. `GET /goals/{id}`
  mengembalikan `GoalDetail`: milestone **datar** urut `urutan` (+ `id_parent_milestone`), masing-masing dengan task
  dan `prasyarat` (daftar `id_task`), dimuat dengan `selectinload`. `PATCH` belum menerima `status`.
- `POST /api/v1/goals/{id_goal}/decompose[?replace=true]`:
  404 (bukan milik user) → 422 (tanpa deadline / deadline lewat) → 409 `"Goal sudah didekomposisi"` (kecuali
  `replace=true`) → `menit_harian` (body override 15–720, atau dihitung D6 lewat
  `goal_service.hitung_menit_harian()` = `scheduler.average_daily_minutes(jam aktif, kegiatan rutin)`, dipotong ke
  720, < 15 → 422 tanpa memanggil AI) → `ai_service.decompose_goal(request, today=waktu.hari_ini())` →
  `AIServiceError` → **502** `"Gagal memproses goal dengan AI: …"` tanpa menulis apa pun → simpan → 201 `GoalDetail`.
- `goal_service.simpan_dekomposisi(db, goal, hasil, today)` adalah **satu-satunya** titik pemetaan output AI → DB
  (titik ganti D11): hapus milestone lama (cascade task, dependensi, jadwal) + simpan pohon baru dalam **satu
  transaksi**, rollback jika error. Pemetaan sesuai `CATATAN_INTEGRASI.md` §2; dependensi duplikat, menunjuk diri
  sendiri, atau nomor tak dikenal dibuang. Ada tes AST yang memastikan field output AI hanya dibaca di fungsi ini.

**Kendala:**

- SQLAlchemy 2.x tidak lagi meng-cascade objek ke session lewat *backref* — versi awal `simpan_dekomposisi`
  membuat task yang tidak ikut tersimpan (`SAWarning` lalu `NOT NULL constraint failed: task_dependency.id_task`).
  Diperbaiki dengan `db.add(task)` eksplisit; `pytest.ini` kini menggagalkan tes jika ada `SAWarning`.
- SQLite memakai ulang rowid yang sudah dihapus, sehingga tes "task lama hilang setelah replace" tidak bisa
  membandingkan `id_task`; tes memeriksa nama task lama dan integritas `task_dependency`.

**Bukti:** `tests/test_api_goals.py 41 passed` (CRUD, 401, 422, isolasi, pemetaan lengkap, `menit_harian`
720/terhitung/override/terlalu kecil, 409 + replace tanpa baris yatim, 502 tanpa baris tersimpan, replace yang gagal
tidak merusak pohon lama, cascade hapus goal/user, unit test `simpan_dekomposisi` + rollback).

### 5. Daftar task + ubah status (FR-10)

**Deskripsi singkat:** `GET /api/v1/tasks` (filter `id_goal`, `status` ∈ `todo|in_progress|done`; urut
`deadline` (NULL di akhir) lalu `id_task`), `GET /api/v1/tasks/{id_task}`, `PATCH /api/v1/tasks/{id_task}`
body `{"status": "todo" | "in_progress" | "done"}` → `TaskRead`. Kepemilikan lewat satu query join
task → milestone → goal → user. `jadwal_task` tidak disentuh.

**Kendala:** tidak ada.

**Bukti:** `tests/test_api_tasks.py 24 passed` (urutan, filter, status tidak valid → 422, task user lain → 404,
filter goal tidak dikenal → list kosong, `jadwal_task` tidak berubah, `Literal` status = konstanta).

### 6. CI backend (GitHub Actions)

**Deskripsi singkat:** `.github/workflows/backend.yml` (baru) — trigger push/PR ke `main` dengan filter path
`backend/**` dan file workflow itu sendiri; Python 3.11 + cache pip; langkah 1 `python -m pytest -q` (SQLite, tanpa
secret/`LLM_API_KEY`); langkah 2 service `postgres:16-alpine` lalu `alembic upgrade head` → `downgrade base` →
`upgrade head` → `alembic check`. `JWT_SECRET_KEY` dummy di env job. `workflows/main.yml` tidak disentuh.

**Kendala:** GitHub Actions tidak bisa dijalankan lokal. Validasi: YAML berhasil di-parse dengan PyYAML (dipasang
sementara di venv, tidak masuk requirements); perintah pytest dijalankan lokal dengan env yang sama (212 passed);
`actionlint` tidak terpasang → dilewati.

### 7. Dokumentasi ERD v2

**Deskripsi singkat:** `docs/ERD_v2.md` — diagram Mermaid 10 tabel (kolom, tipe, PK/FK/UK, kardinalitas), tabel
kolom per entitas (tipe, nullable, arti), nilai status dari `app/core/status.py`, dan bagian "Perubahan dari
ERD v1". Kolom dicocokkan dengan `Base.metadata` hasil introspeksi model.

## Daftar endpoint baru (method, path, kode respons)

Semua endpoint di bawah butuh `Authorization: Bearer <token>` (tanpa/invalid token → 401) dan hanya melihat data
milik user login (data user lain → 404).

| Method | Path | Sukses | Error |
| --- | --- | --- | --- |
| GET | `/api/v1/time-constraints` | 200 | 401 |
| POST | `/api/v1/time-constraints` | 201 | 401, 422 |
| GET | `/api/v1/time-constraints/{id_constraint}` | 200 | 401, 404 |
| PATCH | `/api/v1/time-constraints/{id_constraint}` | 200 | 401, 404, 422 |
| DELETE | `/api/v1/time-constraints/{id_constraint}` | 204 | 401, 404 |
| GET | `/api/v1/agenda?mulai=&sampai=` | 200 | 401, 422 |
| POST | `/api/v1/agenda` | 201 (+ `peringatan_bentrok`) | 401, 422 |
| GET | `/api/v1/agenda/{id_agenda}` | 200 | 401, 404 |
| PATCH | `/api/v1/agenda/{id_agenda}` | 200 (+ `peringatan_bentrok`) | 401, 404, 422 |
| DELETE | `/api/v1/agenda/{id_agenda}` | 204 | 401, 404 |
| GET | `/api/v1/goals` | 200 | 401 |
| POST | `/api/v1/goals` | 201 | 401, 422 |
| GET | `/api/v1/goals/{id_goal}` | 200 (`GoalDetail`) | 401, 404 |
| PATCH | `/api/v1/goals/{id_goal}` | 200 | 401, 404, 422 |
| DELETE | `/api/v1/goals/{id_goal}` | 204 | 401, 404 |
| POST | `/api/v1/goals/{id_goal}/decompose?replace=` | 201 (`GoalDetail`) | 401, 404, 409, 422, 502 |
| GET | `/api/v1/tasks?id_goal=&status=` | 200 | 401, 422 |
| GET | `/api/v1/tasks/{id_task}` | 200 | 401, 404 |
| PATCH | `/api/v1/tasks/{id_task}` | 200 | 401, 404, 422 |

## Hasil tes

- **Sebelum** (basis `48043cb`, sebelum perubahan apa pun): **67 lulus** (`test_ai_service.py` 20,
  `test_scheduler.py` 47), 0 gagal.
- **Sesudah:** **212 lulus**, 0 gagal, 0 skip (`python -m pytest -q` → `212 passed`):

| File | Jumlah tes | Status |
| --- | --- | --- |
| `tests/test_ai_service.py` (Argya, tidak diubah) | 20 | lulus |
| `tests/test_scheduler.py` (Argya, tidak diubah) | 47 | lulus |
| `tests/test_config.py` (baru) | 8 | lulus |
| `tests/test_api_auth.py` (baru) | 18 | lulus |
| `tests/test_api_time_constraints.py` (baru) | 24 | lulus |
| `tests/test_api_agenda.py` (baru) | 30 | lulus |
| `tests/test_api_goals.py` (baru) | 41 | lulus |
| `tests/test_api_tasks.py` (baru) | 24 | lulus |

  Tidak ada tes yang memanggil LLM (fixture autouse membuat `ai_service.decompose_goal` melempar error kecuali
  di-mock). Coverage tidak diukur karena `pytest-cov` tidak terpasang.
- **Migrasi SQLite** (`DATABASE_URL=sqlite:///./w6_migrate.db`): `upgrade head` → `downgrade base` →
  `upgrade head` → `alembic check` semuanya sukses; `alembic check`: **"No new upgrade operations detected."**
  File DB dihapus setelahnya.
- **Migrasi PostgreSQL: TIDAK dijalankan.** Docker CLI ada, tetapi daemon Docker Desktop tidak berjalan
  (`failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`). Sebagai pengganti
  sebagian, SQL migrasi dirender offline untuk dialek PostgreSQL (`alembic upgrade head --sql` dan
  `alembic downgrade bc925661c16c:base --sql`): sukses, 10 tabel + `alembic_version`. Round-trip & `alembic check`
  di Postgres sungguhan akan dijalankan oleh CI (`backend.yml`), atau manual:
  `docker compose up -d db` lalu empat perintah alembic dengan
  `DATABASE_URL=postgresql+psycopg://gradatim:gradatim@localhost:5432/gradatim`
  (cek dulu `alembic current` dan isi tabel `user` agar data lokal tidak ter-downgrade).
- **Smoke test live** (uvicorn port 8765, SQLite file `w6_smoke.db`, tanpa `/decompose`): register, login, `/me`,
  2 kegiatan rutin, agenda bentrok (respons berisi
  `"Bentrok dengan Kuliah (12/10 11:00-12:00, 60 menit)"`), buat/daftar/detail goal, daftar task, 401 tanpa token,
  dan `/openapi.json` memuat `/api/v1/time-constraints`, `/api/v1/agenda`, `/api/v1/goals`,
  `/api/v1/goals/{id_goal}/decompose`, `/api/v1/tasks` — semua lulus. Server dihentikan, DB dihapus.
- File milik tim lain: `git diff --stat main...HEAD` tidak menunjukkan satu pun file terproteksi; migrasi
  `bc925661c16c` tidak diubah dan tidak ada migrasi baru.

## Bug yang ditemukan di file milik tim lain (TIDAK diubah)

- **`workflows/main.yml`** (CI frontend)
  - Gejala: file berada di `workflows/` di root repo, bukan `.github/workflows/`, sehingga **tidak pernah
    dijalankan** GitHub Actions. Jika dipindah pun, `npm install` dan `cache: 'npm'` berjalan di root repo yang tidak
    punya `package.json`/lockfile (aplikasi ada di `frontend/`) → akan gagal.
  - Saran: pindahkan ke `.github/workflows/frontend.yml`, set `defaults.run.working-directory: frontend`,
    `cache-dependency-path: frontend/package-lock.json`, filter `paths: ["frontend/**"]`.
- **`backend/app/services/ai_service.py`** — `decompose_goal()` memakai `today or date.today()` (tanggal zona waktu
  server). Di container Docker (UTC), antara 00:00–07:00 WIB hasilnya tanggal kemarin. Endpoint backend tidak
  terdampak karena selalu mengirim `today=waktu.hari_ini()`, tetapi pemanggil lain (mis. skrip demo) bisa terkena.
  Saran: default ke `app.core.waktu.hari_ini()`.
- **`backend/ai_model/CATATAN_INTEGRASI.md`** — §1, §1b, dan tabel §2 masih menyebut kolom effort/impact dan
  tabel dependensi sebagai "usulan / belum ada", padahal sudah ada di ERD v2 (`2fd29bd`). Saran: perbarui catatan.

## Pertanyaan terbuka untuk tim

- Default status milestone (`"pending"`) dan daftar nilai status goal (selain `active`) belum disepakati.
  Karena itu `PATCH /goals` belum menerima `status`, dan `milestone.status` belum masuk konstanta.
- `task.status = done`: diisi manual oleh user (seperti sekarang lewat `PATCH /tasks/{id}`) atau otomatis saat
  semua sesi `jadwal_task` berstatus `selesai`?
- `JAM_AKTIF_MULAI` / `JAM_AKTIF_SELESAI` ditambahkan lokal karena belum ada di `main` → potensi konflik merge
  kecil dengan branch rekan; pertahankan satu salinan.
- Aturan "agenda di hari yang sama" membuat agenda tidak bisa berakhir tepat 24:00 (harus 23:59). Perlu
  pengecualian untuk `00:00` hari berikutnya?
- `requirements.txt` tidak mem-pin versi. Lingkungan ini memakai FastAPI 0.143, Starlette 1.7, SQLAlchemy 2.1.4,
  bcrypt 5.0 — tiga hal di atas (httpx2, driver psycopg default, ValueError bcrypt) bergantung pada versi.
  Usul: minimal `sqlalchemy>=2.1`, atau pin semua versi.
- Basis branch: brief meminta branch dari yang ter-checkout (`542230`), tetapi pekerjaan butuh `scheduler.py`
  dari `main`; branch kerja di-*fast-forward* ke `main@48043cb` (lihat bagian Branch). Pastikan saat membuat PR
  basisnya `main`.
- Endpoint `/decompose` menahan session DB selama panggilan LLM (bisa sampai puluhan detik dengan retry) dan dua
  request bersamaan untuk goal yang sama bisa sama-sama lolos cek 409. Belum jadi masalah untuk skala sekarang;
  bisa ditangani nanti (lock baris goal / status "sedang diproses").
- Python lokal 3.14 vs Docker/CI 3.11 — sebaiknya tim memakai versi yang sama untuk venv lokal.

## Belum dikerjakan (rencana W7)

- Endpoint `jadwal_task` (generate jadwal via scheduler, tandai selesai/dilewati, re-plan menyimpan sesi lama
  sebagai `dilewati`).
- Endpoint kuesioner mood (`assess_mood` → `mood_questionnaire.hasil_akhir`).
- Penyesuaian `simpan_dekomposisi` setelah output AI menjadi bulanan → mingguan → task (D11).
- Verifikasi migrasi di PostgreSQL lokal (Docker) — tertunda karena daemon Docker tidak berjalan saat sesi ini.
