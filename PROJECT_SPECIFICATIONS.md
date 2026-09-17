# 📘 GradaTim - Technical Specification & Development Blueprint

> **Proyek:** Senior Project (Jaringan Komputer, Komputasi Awan, dan AI)
> **Departemen:** Teknik Elektro dan Teknologi Informasi, Universitas Gadjah Mada
> **Tim:** Kelompok Sukses IP nya 4 di semester 5

---

## 📑 Daftar Isi
1. [Ringkasan Proyek & Premis Utama](#1-ringkasan-proyek--premis-utama)
2. [Matriks Peran & Tanggung Jawab Tim](#2-matriks-peran--tanggung-jawab-tim)
3. [Arsitektur Sistem & Tech Stack](#3-arsitektur-sistem--tech-stack)
4. [Persyaratan Fungsional (Functional Requirements)](#4-persyaratan-fungsional-functional-requirements)
5. [Skema Data & Kontrak JSON AI](#5-skema-data--kontrak-json-ai)
6. [Pedoman UI/UX (Anti-Overwhelm Design System)](#6-pedoman-uiux-anti-overwhelm-design-system)
7. [Aturan Main SDLC & Alur Git (Scrumban)](#7-aturan-main-sdlc--alur-git-scrumban)
8. [Petunjuk Pengembangan Lokal (Local Setup)](#8-petunjuk-pengembangan-lokal-local-setup)

---

## 1. Ringkasan Proyek & Premis Utama

**GradaTim** adalah platform manajemen target (*goal management platform*) berbasis AI yang dirancang untuk mengatasi *goal overwhelm* dan *procrastination* pada pengguna. 

* **Permasalahan:** Pengguna seringkali memiliki target jangka panjang yang besar, tetapi bingung memecahnya menjadi langkah harian yang realistis, sehingga memicu rasa cemas dan beban kognitif tinggi (*cognitive overload*).
* **Solusi GradaTim:** 
  1. **AI Goal Decomposition:** Mengubah target abstrak menjadi *milestones* dan *actionable daily tasks* secara otomatis via LLM.
  2. **Today Action List & Focus Mode:** Antarmuka bersih yang membatasi tampilan tugas harian agar pengguna tidak kelelahan melihat tumpukan daftar tugas.
  3. **Visual Progress Tracking:** Memberikan umpan balik visual terkait pencapaian tanpa efek *burnout*.

---

## 2. Matriks Peran & Tanggung Jawab Tim

| Anggota Tim | Peran Utama | Area Fokus Pengerjaan |
| :--- | :--- | :--- |
| **Annora Farah Aprilla Setyawan** | Project Manager, UI/UX Designer, AI Engineer | Tata kelola Scrumban Board, perancangan Sistem Desain UI/UX (Figma), perumusan prompt engineering & alur dekomposisi AI. |
| **Akio Afifian Ahsan** | UI/UX Designer, Software Engineer, Cloud Engineer | Wireframing & prototipe interaktif (Figma), setup & slicing aplikasi Frontend, integrasi container lokal/cloud. |
| **Muhammad Affandi Argya Bagaskara** | Cloud Engineer, AI Engineer, Software Engineer | Manajemen basis data PostgreSQL & Docker Compose, integrasi API Backend, otomatisasi ekstraksi JSON LLM. |

---

## 3. Arsitektur Sistem & Tech Stack

```
[ Frontend (Web App) ]  <--->  [ Backend API Engine ]  <--->  [ LLM Service / OpenAI API ]
 (Next.js / React)                  (Node.js / Python)             (Goal Decomposition)
         ^                                  ^
         |                                  |
         +----------------------------------+
                        |
            [ Database: PostgreSQL ]
                (Docker Container)
```

* **Frontend:** Framework Web Modern (React / Next.js) + Tailwind CSS (Styling).
* **Backend:** REST API (Node.js / Express atau Python / FastAPI).
* **Database:** PostgreSQL disajikan melalui Docker Compose.
* **AI Engine:** Integration Client dengan Structured JSON Output Prompting.
* **DevOps / Environment:** Docker & Docker Compose untuk pengkapsulan dependensi lokal.

---

## 4. Persyaratan Fungsional (Functional Requirements)

* **FR-1: User Management & Profile:** Autentikasi pengguna dasar dan preferensi waktu luang harian.
* **FR-2: AI Goal Decomposition (Core Feature):**
  * Input: Target Utama (*Goal Title*), Tenggat Waktu (*Deadline*), dan Alokasi Waktu Harian.
  * Output: Rincian *Milestones* dan daftar tugas harian berskala mikro (*Actionable Tasks*).
* **FR-3: Today Action List (Anti-Overwhelm View):** Tampilan khusus yang hanya menampilkan maksimal 3–5 tugas fokus untuk hari berjalan.
* **FR-4: Interactive Milestone Tracker:** Kemampuan menandai tugas selesai yang secara otomatis memperbarui persentase *progress bar* target utama.
* **FR-5: Schedule & Constraint Manager:** Penyesuaian jadwal ulang otomatis jika tugas harian terlewati (*overdue adjustment*).

---

## 5. Skema Data & Kontrak JSON AI

### A. Kontrak Output AI (JSON Schema for Goal Decomposition)
Setiap panggilan API AI untuk *Goal Decomposition* **WAJIB** mengembalikan struktur JSON murni sebagai berikut agar mudah di-*parse* oleh Backend:

```json
{
  "goal_title": "Belajar Docker & CI/CD dalam 2 Minggu",
  "estimated_total_days": 14,
  "milestones": [
    {
      "milestone_title": "Dasar Containerization",
      "order": 1,
      "tasks": [
        {
          "task_title": "Install Docker Desktop & Verifikasi CLI",
          "day_number": 1,
          "estimated_minutes": 30
        },
        {
          "task_title": "Membuat Dockerfile Sederhana untuk Node.js",
          "day_number": 2,
          "estimated_minutes": 45
        }
      ]
    }
  ]
}
```

### B. Entitas Utama Basis Data (PostgreSQL)
1. `users` (`id`, `email`, `name`, `created_at`)
2. `goals` (`id`, `user_id`, `title`, `description`, `target_date`, `status`, `created_at`)
3. `milestones` (`id`, `goal_id`, `title`, `order_index`, `is_completed`)
4. `tasks` (`id`, `milestone_id`, `title`, `day_number`, `estimated_minutes`, `status`, `parent_task_id`)

---

## 6. Pedoman UI/UX (Anti-Overwhelm Design System)

Untuk memastikan pengalaman pengguna tetap menenangan:
1. **Warna:** Gunakan warna dominan netral/soft (Muted Slate, Cool Gray, Soft Blue/Teal). Hindari warna merah menyala berlebihan untuk *overdue tasks*.
2. **Layout Density:** *White space* yang cukup. Hindari menumpuk seluruh *backlog* dalam satu layar utama.
3. **Typography:** Gunakan font Sans-Serif yang bersih (*Inter* / *Plus Jakarta Sans*) dengan ukuran yang dapat dibedakan secara hirarkis.

---

## 7. Aturan Main SDLC & Alur Git (Scrumban)

### A. Scrumban Board Setup
Alur kerja kartu issue di GitHub Projects dibagi menjadi 5 kolom:
1. `Backlog`: Daftar seluruh fitur & ide yang belum diprioritaskan.
2. `Ready`: Issue yang sudah jelas spesifikasinya dan siap dikerjakan.
3. `In Progress`: Pengerjaan aktif (**WIP Limit: Maksimal 2 task per anggota**.
4. `In Review`: Pull Request (PR) sedang ditinjau oleh anggota tim lain.
5. `Done`: Telah di-merge dan diverifikasi.

### B. Konvensi Branching Git
* `main`: Branch produksi/stabil. Tidak boleh langsung dipush.
* `develop`: Branch integrasi fitur.
* `feature/<issue-id>-<deskripsi-singkat>`: Branch pengerjaan individual.
  * Contoh: `feature/#3-setup-docker-db`, `feature/#2-hifi-dashboard`

---

## 8. Petunjuk Pengembangan Lokal (Local Setup)

### Prerequisites
* Git
* Docker & Docker Compose
* Node.js (v18+) / Python (3.10+)

### Quick Start
1. **Clone Repositori:**
   ```bash
   git clone https://github.com/Username/GradaTim.git
   cd GradaTim
   ```

2. **Jalankan Database (Docker):**
   ```bash
   docker compose up -d postgres_db
   ```

3. **Verifikasi Container:**
   ```bash
   docker ps
   ```

---
*Dokumen ini bersifat dinamis dan dapat diperbarui seiring dengan perkembangan iterasi proyek GradaTim.*