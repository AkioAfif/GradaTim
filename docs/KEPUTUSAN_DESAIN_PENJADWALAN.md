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
| D4 | Hierarki goal | Goal besar → **goal bulanan** → **goal mingguan** → task harian yang fleksibel | ✅ diimplementasi |
| D5 | Kepadatan jadwal | **Jangan** penuhi seluruh jam luang; task dibagi **merata dalam seminggu** | ✅ |
| D6 | `menit_harian` | Dihitung **otomatis** dari jam luang (lihat D10), bukan input manual terpisah | ✅ diimplementasi |
| D7 | Mood vs jadwal | Task dalam seminggu fleksibel per hari; task yang tidak terambil karena mood **tidak hilang**, digeser ke hari lain di minggu itu | ✅ (interpretasi, lihat §5) |
| D8 | Skip task | Dua konsekuensi: beban hari berikutnya naik **atau** goal besar mundur | ⏳ |
| D9 | Agenda lain (FR-5) | Agenda sekali-jalan per minggu (selain rutin) bisa diinput manual oleh user | ✅ (desain teknis 💡) |
| D10 | Input jam luang | **Tidak ada input jam luang terpisah** (hindari data redundan & kurangi fitur). Jam luang = jam aktif harian − kegiatan rutin − agenda | ✅ grup (jam aktif 💡) |
| D11 | Rincian task | Task **dirinci per minggu** sesuai progres, bukan semua minggu di awal | ✅ diimplementasi (job Senin ⏳) |
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

**Implementasi (ERD v2):** `milestone` dibuat bertingkat — `tipe = "bulanan"` (tanpa induk) → `tipe = "mingguan"`
(`id_parent_milestone` = bulanannya) → `task`. Pemetaan lengkapnya ada di `backend/ai_model/CATATAN_INTEGRASI.md` §2.

**Keputusan (D11, diskusi grup):** task **dirinci per minggu sesuai progres**, tidak semua di awal.

**Aturan kerangka waktu** (diputuskan 19 Okt 2026, dihitung sistem di `app/services/rencana.py`, bukan oleh AI):
- **Minggu = minggu kalender Senin–Minggu.** Minggu ke-1 mulai hari goal direncanakan, jadi bisa pendek (mis. Kamis–Minggu);
  AI diberi tahu jumlah harinya. Minggu terakhir dipotong di deadline goal.
- **Bulan = bulan kalender.** Minggu yang melintasi dua bulan masuk ke bulan yang memuat **lebih banyak hari** minggu itu.
  Jika seri: minggu < 4 hari → bulan berikutnya, selain itu → bulan sebelumnya.
- AI hanya mengisi judul & tujuan tiap target serta task; tanggal, jumlah minggu, dan jumlah bulan selalu dari sistem.

**Alur:**
1. Saat goal direncanakan (`POST /goals/{id}/decompose`): AI mengisi **target bulanan → target mingguan** untuk seluruh
   durasi goal, lalu merinci **task untuk minggu ke-1** saja (`ai_service.rencanakan_goal`).
2. Minggu berikutnya dirinci lewat `POST /goals/{id}/rinci-minggu?minggu=ini|depan` (`ai_service.rinci_minggu`),
   berdasarkan target minggu itu **dan progres task minggu-minggu sebelumnya** (selesai / belum):
   - `minggu=ini` dipanggil frontend saat user membuka goal di minggu yang belum punya task;
   - `minggu=depan` = tombol "rinci minggu depan", hanya boleh **mulai hari Sabtu**;
   - idempotent: minggu yang sudah punya task dikembalikan apa adanya tanpa memanggil AI.
   Task lama yang belum selesai tetap ada (tidak dibuat ulang); batas menit minggu baru dikurangi menitnya.
3. Penjadwal (`POST /jadwal/goal/{id}`) hanya mengambil task milestone mingguan yang **minggunya sudah tiba**
   (`jadwal_service.minggu_sudah_tiba`); task minggu lalu yang belum selesai tetap ikut dikejar.

Satu pemanggilan AI per goal aktif per minggu — masih aman untuk kuota Gemini free tier.
⏳ Belakangan: job otomatis Senin 00:00 yang merinci minggu baru untuk semua goal aktif (sekarang dipicu frontend).

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
| `average_daily_minutes()` | pengganti input manual `menit_harian` (lewat `goal_service.hitung_menit_harian`) | D6 |
| `schedule_tasks()` | penjadwalan otomatis, merata, boleh dipecah, urut dependensi | FR-4, D2, D5 |
| `busy_blocks()`, `find_conflicts()`, `validate_schedule()` | deteksi bentrok, termasuk saat sesi dipindah manual | FR-5 |
| `replan()` | jadwal ulang sesi terlewat & task yang ditunda karena mood, dalam minggu yang sama | FR-11, D7 |

Demo: `python scripts/demo_jadwal.py` (dari folder `backend/`) — task minggu ke-1 di kalender satu minggu + skenario re-planning, tanpa memanggil LLM.

### Keterbatasan yang diketahui

- **Sesi selalu ditaruh di slot paling awal dalam sehari** (mis. tepat setelah kuliah selesai, atau jam 08:00 di akhir pekan). Belum ada preferensi waktu (pagi/sore/malam). ❓ Perlu fitur preferensi jam belajar?
- **Batas harian dinaikkan untuk semua hari sekaligus** jika ada task yang tidak muat. Pada data demo efeknya sudah kecil (hanya 1 hari bertambah), tetapi dengan banyak task berantai masih bisa membuat beban menumpuk di awal minggu.
- **Jam aktif harian** masih default di config (`JAM_AKTIF_MULAI/SELESAI`, 06:00–22:00), belum bisa diatur per user (D10).

## 8. Perlu dibahas dengan tim

Untuk Akio (sebaiknya **sebelum** migrasi Alembic awal di branch `542230` di-merge, agar cukup satu migrasi):
- `time_constraint` dipakai ulang untuk kegiatan rutin (+ kolom `nama`); tabel `agenda`, `jadwal_task` (§3, §7)
- ~~Level target bulanan & mingguan (§4)~~ — selesai (milestone bertingkat, ERD v2)
- Endpoint baru untuk frontend: `POST /goals/{id}/rinci-minggu?minggu=ini|depan` (§4)
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
| 20 Okt 2026 | D4 & D11 diimplementasi (§4): kerangka minggu/bulan kalender, rencana bulanan → mingguan, rincian task per minggu (`rinci-minggu`, minggu depan mulai Sabtu), penjadwal hanya mengambil minggu yang sudah tiba. |
