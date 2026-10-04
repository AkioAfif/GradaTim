# Catatan Integrasi AI ↔ Database

> Catatan dari Argya untuk didiskusikan bersama tim (terutama Akio, pemilik `app/models/`).
> Belum ada perubahan apa pun pada model/ERD — semua di bawah ini masih usulan.

## 1. [PERLU DISKUSI] Kolom effort & impact di tabel `task`

`filter_tasks_by_capacity()` (FR-7) dan tampilan Effort vs Impact (FR-9) butuh dua atribut per task,
tapi `app/models/task.py` belum punya kolomnya. Output AI decomposer **sudah** menghasilkan kedua nilai ini.

Usulan (nullable supaya task lama / task manual tetap valid):

```python
tingkat_effort: Mapped[Optional[str]] = mapped_column(String(10))  # "low" | "medium" | "high"
tingkat_impact: Mapped[Optional[str]] = mapped_column(String(10))  # "low" | "medium" | "high"
```

Selama kolom belum ada, `recommend_tasks()` menganggap semua task bernilai `medium`,
sehingga urutan rekomendasi mood belum bermakna.

## 1b. [PERLU DISKUSI] Dependensi antar task

AI sekarang juga menghasilkan `task_number` dan `depends_on` (task mana yang harus selesai dulu),
dipakai rekomendasi harian agar tidak menyarankan task yang prasyaratnya belum selesai.
`task.id_parent_task` yang ada sekarang adalah hierarki **sub-task**, bukan prasyarat, jadi
dependensi perlu tabel relasi sendiri (many-to-many), misalnya:

```python
class TaskDependency(Base):
    __tablename__ = "task_dependency"
    id_task: Mapped[int] = mapped_column(ForeignKey("task.id_task"), primary_key=True)
    id_task_prasyarat: Mapped[int] = mapped_column(ForeignKey("task.id_task"), primary_key=True)
```

## 2. Pemetaan output AI → tabel

| Output AI (`GoalDecomposition`) | Kolom DB |
| --- | --- |
| `goal_title` | *(tidak dipakai — judul pakai input user `goal.judul_goal`)* |
| `milestones[].milestone_title` | `milestone.judul_milestone` |
| `milestones[].order` | `milestone.urutan` |
| `tasks[].task_title` | `task.nama_task` |
| `tasks[].estimated_minutes` | `task.durasi_estimasi` |
| `tasks[].day_number` | `task.deadline` = hari ini + (`day_number` − 1) hari *(sementara, sebelum scheduler FR-4 ada)* |
| `tasks[].effort_level` / `impact_level` | kolom usulan di poin 1 |

`milestone.deadline` bisa diisi dari `day_number` terbesar di milestone tersebut.

## 3. Mood questionnaire

- `QuestionnaireAnswer.nomor_questionnaire` 1–5 = urutan `[fokus, tenang, motivasi, tidur, siap]`
  (sama dengan field `MoodAnswers.q1_focus` … `q5_readiness`).
- `MoodQuestionnaire.hasil_akhir` = `MoodAssessment.capacity_index` (0 = LOW, 1 = MEDIUM, 2 = HIGH).

## 4. Hal teknis lain

- **File model `mood_model.pkl` tidak di-commit.** Generate dengan:
  ```bash
  pip install -r ai_model/requirements-train.txt
  python ai_model/train_model.py
  ```
  Untuk Docker nanti perlu diputuskan: commit `.pkl`-nya, atau training saat build image.
  Versi `scikit-learn` saat training dan saat runtime sebaiknya sama (pickle tidak dijamin kompatibel antar versi).
- `menit_harian` di `GoalDecompositionRequest` untuk sementara diisi manual.
  Idealnya dihitung dari `time_constraint` user (total durasi `waktu_mulai`–`waktu_selesai` per hari).
- LLM default sekarang **Google Gemini** (free tier), via OpenAI-compatible API. Diatur lewat
  `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` di `.env` (menggantikan `OPENAI_API_KEY`).
  Bagian 8 di `docs/PROJECT_SPECIFICATIONS.md` masih menyebut `OPENAI_API_KEY` — perlu disesuaikan.
  Variabel lama di `.env` tidak bikin error (config memakai `extra="ignore"`).
