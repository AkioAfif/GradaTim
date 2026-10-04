# Keputusan Desain: Penjadwalan & Alokasi Waktu

> **Dicatat:** 4 Oktober 2026 · **Oleh:** Argya (hasil diskusi saat merancang penjadwal otomatis FR-4, FR-5, FR-11)
> **Status:** D1–D9 keputusan Argya sebagai pengembang AI/backend; D10–D12 hasil diskusi grup. Desain tabel database (💡) **perlu dikonfirmasi** oleh Akio (model DB & frontend). Riwayat perubahan di [§9](#9-riwayat-perubahan).
>
> Dokumen ini hidup: tambahkan keputusan baru di bawah, jangan hapus yang lama — ubah statusnya saja.

**Legenda status:** ✅ Disepakati · 💡 Usulan (belum diputuskan) · ⏳ Ditunda (dikerjakan nanti) · ❓ Pertanyaan terbuka

---

## 1. Gambaran alur

1. User mengisi **kegiatan rutin** (kuliah, gym, dll.) yang otomatis muncul setiap minggu, dan bila perlu **agenda** sekali-jalan — lihat [§3](#3-kegiatan-rutin-mingguan).
2. **Jam luang tidak diinput terpisah** (D10): dihitung otomatis = jam aktif harian − kegiatan rutin − agenda. Ini yang memenuhi FR-3.
3. User membuat **goal besar**; AI memecahnya secara **hierarkis**, dan task dirinci **per minggu** sesuai progres — lihat [§4](#4-hierarki-goal).
4. Penjadwal menempatkan task ke **kalender internal GradaTim** pada slot luang yang tidak bentrok (FR-4, FR-5), **merata dalam seminggu**, tanpa memenuhi seluruh jam luang.
5. Setiap hari, kuesioner mood menentukan berapa task yang direkomendasikan hari itu (FR-6, FR-7).
6. Task yang terlewat / ditunda dijadwalkan ulang (FR-11) — konsekuensinya lihat [§6](#6-konsekuensi-skip-task).

## 2. Ringkasan keputusan

| # | Topik | Keputusan | Status |
| :--- | :--- | :--- | :--- |
| D1 | Kalender | Kalender **internal** GradaTim, tidak sinkron Google Calendar | ✅ |
| D2 | Pemecahan task | Satu task **boleh dipecah** ke beberapa sesi/slot (yang penting task selesai) | ✅ |
| D3 | Kegiatan rutin | Kegiatan rutin mingguan jadi **baseline otomatis** di kalender setiap minggu | ✅ (desain teknis 💡) |
| D4 | Hierarki goal | Goal besar → **goal bulanan** → **goal mingguan** → task harian yang fleksibel | ✅ (desain teknis 💡) |
| D5 | Kepadatan jadwal | **Jangan** penuhi seluruh jam luang; task dibagi **merata dalam seminggu** | ✅ |
| D6 | `menit_harian` | Dihitung **otomatis** dari jam luang (lihat D10), bukan input manual terpisah | ✅ |
| D7 | Mood vs jadwal | Task dalam seminggu fleksibel per hari; task yang tidak terambil karena mood **tidak hilang**, digeser ke hari lain di minggu itu | ✅ (interpretasi, lihat §5) |
| D8 | Skip task | Dua konsekuensi: beban hari berikutnya naik **atau** goal besar mundur | ⏳ |
| D9 | Agenda lain (FR-5) | Agenda sekali-jalan per minggu (selain rutin) bisa diinput manual oleh user | ✅ (desain teknis 💡) |
| D10 | Input jam luang | **Tidak ada input jam luang terpisah** (hindari data redundan & kurangi fitur). Jam luang = jam aktif harian − kegiatan rutin − agenda | ✅ grup (jam aktif 💡) |
| D11 | Rincian task | Task **dirinci per minggu** sesuai progres, bukan semua minggu di awal | ✅ grup |
| D12 | Skip task | **User memilih** konsekuensinya setiap kali skip (kejar ketertinggalan atau goal mundur) | ✅ grup (fitur tetap ⏳) |

## 3. Kegiatan rutin mingguan

**Keputusan (D3, D9):** Selain diinput manual oleh user di awal minggu, kegiatan rutin seperti **kuliah** atau **gym** disimpan sekali dan **otomatis muncul setiap minggu** sebagai baseline. Penjadwal tidak boleh menaruh task di jam kegiatan rutin maupun agenda lain (FR-5).

Ini sekaligus menutup celah FR-5: ERD saat ini belum punya tabel untuk "agenda lain".

**Keputusan (D10, diskusi grup):** user **tidak** mengisi jam luang terpisah — prinsipnya hindari data redundan dan kurangi fitur yang tidak perlu. Jam luang dihitung:

```
jam luang = jam aktif harian − kegiatan rutin − agenda − sesi task yang sudah terjadwal
```

💡 **Usulan teknis** (perlu dibahas dengan Akio):
- **Tabel `time_constraint` dipakai ulang sebagai tabel kegiatan rutin** — kolomnya sudah sama persis (`id_user`, `hari_dalam_minggu`, `waktu_mulai`, `waktu_selesai`), cukup tambah kolom `nama`. Tidak perlu tabel `kegiatan_rutin` baru. Nama tabel boleh dipertahankan atau diganti (mis. `kegiatan_rutin`) selama migrasi awal belum di-merge.
- Tabel `agenda`: `id_user`, `nama`, `waktu_mulai`, `waktu_selesai` (tanggal spesifik, sekali jalan — untuk input manual mingguan).
- Penjadwal memperlakukan keduanya sebagai **jam sibuk**.
- **Jam aktif harian**: 💡 untuk sekarang konstanta default (mis. 06:00–22:00 setiap hari) tanpa input user, sesuai prinsip kurangi fitur. Bisa dijadikan pengaturan user nanti jika dibutuhkan.

Dampak ke kode: `scheduler.free_slots()` tidak berubah — parameter `availability` diisi jam aktif, `routines` diisi kegiatan rutin.

## 4. Hierarki goal

**Keputusan (D4):**

```
Goal besar (mis. "Lulus TOEFL 550 dalam 3 bulan")
 └─ Goal bulanan   (mis. "Bulan 1: kuasai grammar dasar")
     └─ Goal mingguan (mis. "Minggu 2: tenses & subject-verb agreement")
         └─ Task kecil  — dijadwalkan fleksibel di dalam minggunya, menyesuaikan kondisi harian (mood)
```

**Dampak ke implementasi yang sudah ada:**
- ERD sekarang hanya `goal → milestone → task`. Butuh satu level tambahan. 💡 Opsi: `milestone` dipakai untuk goal bulanan + tabel baru untuk goal mingguan, atau `milestone` dibuat bertingkat (kolom `id_parent_milestone` + `tipe` bulanan/mingguan).
- AI decomposer (`app/services/ai_service.py`) sekarang menghasilkan `milestones → tasks` dengan `day_number`. Perlu diubah ke `bulan → minggu → task`, dan task cukup ditandai **minggu ke berapa**, bukan hari ke berapa.

**Keputusan (D11, diskusi grup):** task **dirinci per minggu sesuai progres**, tidak semua di awal.

Alur yang diusulkan 💡:
1. Saat goal dibuat: AI memecah goal → **target bulanan → target mingguan** (judul & tujuan saja), lalu merinci **task untuk minggu pertama**.
2. Setiap awal minggu: AI merinci task minggu itu berdasarkan target mingguan **dan progres minggu sebelumnya** (task yang belum selesai, yang di-skip, dsb.).
3. Penjadwal (`schedule_tasks`) menempatkan task minggu itu ke slot luang minggu itu.

Konsekuensi teknis: butuh pemicu "awal minggu" (mis. saat user pertama membuka aplikasi di minggu baru, atau job terjadwal), dan satu pemanggilan AI per goal aktif per minggu — masih aman untuk kuota Gemini free tier.

## 5. Kepadatan jadwal & hubungan dengan mood

**Keputusan (D5):** Penjadwal **tidak** mengisi seluruh jam luang (prinsip anti-overwhelm di spesifikasi bagian 6). Task goal mingguan **dibagi merata** ke hari-hari dalam minggu itu.

**Keputusan (D7):** Unit perencanaan adalah **minggu**; pembagian per hari bersifat fleksibel. Jika hari ini mood LOW dan hanya 2 dari 4 task terjadwal yang direkomendasikan, sisanya **tidak hilang** — digeser ke hari lain di minggu yang sama (re-planning, FR-11).

💡 **Usulan teknis:** batas beban harian = (total menit task minggu ini ÷ jumlah hari luang di minggu itu), dengan toleransi kecil, dan tidak melebihi jam luang hari itu.

## 6. Konsekuensi skip task

**Keputusan (D8) — ⏳ ditunda, dikerjakan setelah penjadwal dasar selesai.**

Jika user melewatkan (skip) task hari ini, ada dua kemungkinan konsekuensi:
1. **Kejar ketertinggalan** — task dibagikan ke hari-hari berikutnya, sehingga beban harian berikutnya **bertambah**.
2. **Goal mundur** — beban harian tetap, tetapi target selesai **goal besar ikut mundur**.

**Keputusan (D12, diskusi grup):** **user memilih** konsekuensinya setiap kali skip.

❓ **Pertanyaan terbuka (tersisa):** bagaimana jika goal punya deadline keras (mis. tanggal ujian) yang tidak bisa mundur — apakah opsi "goal mundur" disembunyikan untuk goal seperti itu?

## 7. Asumsi teknis penjadwal

Berlaku untuk implementasi `app/services/scheduler.py` kecuali diubah:

- Potongan sesi minimal **15 menit**; sisa slot lebih kecil dari itu dilewati.
- Task **tidak dipecah hanya untuk mengisi batas harian**; dipecah hanya jika slot habis (mis. terpotong kegiatan rutin) atau task lebih besar dari batas harian.
- Batas harian minimal **sebesar task terbesar** — kalau task sedikit, lebih baik ada hari kosong daripada setiap task dipotong-potong.
- Task tidak dijadwalkan sebelum **semua prasyaratnya** (`depends_on`) selesai dijadwalkan.
- Slot yang sudah terisi task dari **goal lain** milik user yang sama dianggap sibuk, dan bebannya ikut dihitung dalam batas harian (`existing_load`).
- Task yang tidak muat sebelum deadline **dilaporkan terpisah**, tidak diam-diam dijadwalkan melewati deadline.
- Zona waktu lokal (WIB), tanpa konversi zona waktu.
- Karena task boleh dipecah (D2), satu task bisa punya beberapa sesi → 💡 butuh tabel `jadwal_task` (`id_task`, `waktu_mulai`, `waktu_selesai`, `status`). Tabel `task` saat ini hanya punya satu kolom `deadline`.

### Status implementasi (`backend/app/services/scheduler.py`)

| Fungsi | Memenuhi | Keputusan |
| :--- | :--- | :--- |
| `free_slots()` | slot luang = jam aktif − rutin − agenda − sesi lain | D3, D9, D10 |
| `average_daily_minutes()` | pengganti input manual `menit_harian` (belum dihubungkan ke decomposer) | D6 |
| `schedule_tasks()` | penjadwalan otomatis, merata, boleh dipecah, urut dependensi | FR-4, D2, D5 |
| `busy_blocks()`, `find_conflicts()`, `validate_schedule()` | deteksi bentrok, termasuk saat sesi dipindah manual | FR-5 |
| `replan()` | jadwal ulang sesi terlewat & task yang ditunda karena mood, dalam minggu yang sama | FR-11, D7 |

Demo: `python scripts/demo_jadwal.py` (dari folder `backend/`) — kalender 2 minggu + skenario re-planning, tanpa memanggil LLM.

### Keterbatasan yang diketahui

- **Sesi selalu ditaruh di slot paling awal dalam sehari** (mis. tepat setelah kuliah selesai, atau jam 08:00 di akhir pekan). Belum ada preferensi waktu (pagi/sore/malam). ❓ Perlu fitur preferensi jam belajar?
- **Batas harian dinaikkan untuk semua hari sekaligus** jika ada task yang tidak muat. Pada data demo efeknya sudah kecil (hanya 1 hari bertambah), tetapi dengan banyak task berantai masih bisa membuat beban menumpuk di awal minggu.
- **Jam aktif harian** masih konstanta di kode/demo (mis. 08:00–21:00), belum ada sumber resminya (D10).
- Hasil AI decomposer masih memakai `day_number` (hari ke-N) sebagai batas paling awal; setelah decomposer diubah ke target mingguan (D4, D11), cukup "awal minggu".

## 8. Perlu dibahas dengan tim

Untuk Akio (sebaiknya **sebelum** migrasi Alembic awal di branch `542230` di-merge, agar cukup satu migrasi):
- `time_constraint` dipakai ulang untuk kegiatan rutin (+ kolom `nama`); tabel `agenda`, `jadwal_task` (§3, §7)
- Level target bulanan & mingguan (§4) — sekarang sudah diputuskan, bisa mulai didesain
- Kolom effort/impact & tabel dependensi task (lihat `backend/ai_model/CATATAN_INTEGRASI.md`)

Untuk Annora (PM/UX):
- Pertanyaan terbuka tersisa di §6 (goal dengan deadline keras)
- Alur UI input kegiatan rutin & agenda mingguan; UI pilihan konsekuensi saat skip task

## 9. Riwayat perubahan

| Tanggal | Perubahan |
| :--- | :--- |
| 4 Okt 2026 | Dokumen dibuat (D1–D9) |
| 4 Okt 2026 | Hasil diskusi grup: D10 (tanpa input jam luang terpisah), D11 (task dirinci per minggu), D12 (user memilih konsekuensi skip). `time_constraint` diusulkan dipakai ulang untuk kegiatan rutin. |
| 4 Okt 2026 | Penjadwal FR-4, FR-5, FR-11 selesai diimplementasi (§7: status, keterbatasan). Aturan baru: task tidak dipecah hanya demi batas harian; batas harian minimal sebesar task terbesar. |
