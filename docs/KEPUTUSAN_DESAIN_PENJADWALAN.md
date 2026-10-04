# Keputusan Desain: Penjadwalan & Alokasi Waktu

> **Dicatat:** 4 Oktober 2026 · **Oleh:** Argya (hasil diskusi saat merancang penjadwal otomatis FR-4, FR-5, FR-11)
> **Status:** Keputusan Argya sebagai pengembang AI/backend — **perlu dikonfirmasi** oleh Annora (PM) dan Akio (model DB & frontend) sebelum dianggap final.
>
> Dokumen ini hidup: tambahkan keputusan baru di bawah, jangan hapus yang lama — ubah statusnya saja.

**Legenda status:** ✅ Disepakati · 💡 Usulan (belum diputuskan) · ⏳ Ditunda (dikerjakan nanti) · ❓ Pertanyaan terbuka

---

## 1. Gambaran alur

1. User mengisi **jam luang mingguan** (FR-3) — tersimpan di tabel `time_constraint` (hari, jam mulai, jam selesai; satu hari boleh beberapa rentang).
2. User mengisi **kegiatan rutin** (kuliah, gym, dll.) yang otomatis muncul setiap minggu — lihat [§3](#3-kegiatan-rutin-mingguan).
3. User membuat **goal besar**; AI memecahnya secara **hierarkis** — lihat [§4](#4-hierarki-goal).
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
| D6 | `menit_harian` | Dihitung **otomatis** dari `time_constraint`, bukan input manual terpisah | ✅ |
| D7 | Mood vs jadwal | Task dalam seminggu fleksibel per hari; task yang tidak terambil karena mood **tidak hilang**, digeser ke hari lain di minggu itu | ✅ (interpretasi, lihat §5) |
| D8 | Skip task | Dua konsekuensi: beban hari berikutnya naik **atau** goal besar mundur | ⏳ |
| D9 | Agenda lain (FR-5) | Agenda sekali-jalan per minggu (selain rutin) bisa diinput manual oleh user | ✅ (desain teknis 💡) |

## 3. Kegiatan rutin mingguan

**Keputusan (D3, D9):** Selain diinput manual oleh user di awal minggu, kegiatan rutin seperti **kuliah** atau **gym** disimpan sekali dan **otomatis muncul setiap minggu** sebagai baseline. Penjadwal tidak boleh menaruh task di jam kegiatan rutin maupun agenda lain (FR-5).

Ini sekaligus menutup celah FR-5: ERD saat ini belum punya tabel untuk "agenda lain".

💡 **Usulan teknis** (perlu dibahas dengan Akio):
- Tabel `kegiatan_rutin`: `id_user`, `nama`, `hari_dalam_minggu`, `waktu_mulai`, `waktu_selesai` (berulang tiap minggu).
- Tabel `agenda`: `id_user`, `nama`, `waktu_mulai`, `waktu_selesai` (tanggal spesifik, sekali jalan — untuk input manual mingguan).
- Penjadwal memperlakukan keduanya sebagai **jam sibuk**.

❓ **Pertanyaan terbuka:** kalau sudah ada kegiatan rutin, apakah `time_constraint` (jam luang) masih perlu diisi terpisah, atau jam luang = jam aktif harian (mis. 06:00–22:00) dikurangi kegiatan rutin & agenda?

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

❓ **Pertanyaan terbuka:** apakah task untuk semua minggu dibuat di awal, atau task **hanya dirinci untuk minggu berjalan** (misalnya dibuat ulang tiap awal minggu dengan memperhitungkan progres minggu sebelumnya)? Opsi kedua lebih adaptif untuk goal panjang, tapi butuh pemanggilan AI tiap minggu.

## 5. Kepadatan jadwal & hubungan dengan mood

**Keputusan (D5):** Penjadwal **tidak** mengisi seluruh jam luang (prinsip anti-overwhelm di spesifikasi bagian 6). Task goal mingguan **dibagi merata** ke hari-hari dalam minggu itu.

**Keputusan (D7):** Unit perencanaan adalah **minggu**; pembagian per hari bersifat fleksibel. Jika hari ini mood LOW dan hanya 2 dari 4 task terjadwal yang direkomendasikan, sisanya **tidak hilang** — digeser ke hari lain di minggu yang sama (re-planning, FR-11).

💡 **Usulan teknis:** batas beban harian = (total menit task minggu ini ÷ jumlah hari luang di minggu itu), dengan toleransi kecil, dan tidak melebihi jam luang hari itu.

## 6. Konsekuensi skip task

**Keputusan (D8) — ⏳ ditunda, dikerjakan setelah penjadwal dasar selesai.**

Jika user melewatkan (skip) task hari ini, ada dua kemungkinan konsekuensi:
1. **Kejar ketertinggalan** — task dibagikan ke hari-hari berikutnya, sehingga beban harian berikutnya **bertambah**.
2. **Goal mundur** — beban harian tetap, tetapi target selesai **goal besar ikut mundur**.

❓ **Pertanyaan terbuka:** siapa yang memilih — user tiap kali skip, preferensi tetap di pengaturan, atau otomatis (mis. pilih opsi 1 selama beban harian masih di bawah batas, selain itu opsi 2)? Bagaimana jika goal punya deadline keras (mis. tanggal ujian) yang tidak bisa mundur?

## 7. Asumsi teknis penjadwal

Berlaku untuk implementasi `app/services/scheduler.py` kecuali diubah:

- Potongan sesi minimal **15 menit**; sisa slot lebih kecil dari itu dilewati.
- Task tidak dijadwalkan sebelum **semua prasyaratnya** (`depends_on`) selesai dijadwalkan.
- Slot yang sudah terisi task dari **goal lain** milik user yang sama juga dianggap sibuk.
- Task yang tidak muat sebelum deadline **dilaporkan terpisah**, tidak diam-diam dijadwalkan melewati deadline.
- Zona waktu lokal (WIB), tanpa konversi zona waktu.
- Karena task boleh dipecah (D2), satu task bisa punya beberapa sesi → 💡 butuh tabel `jadwal_task` (`id_task`, `waktu_mulai`, `waktu_selesai`, `status`). Tabel `task` saat ini hanya punya satu kolom `deadline`.

## 8. Perlu dibahas dengan tim

Untuk Akio (sebaiknya **sebelum** migrasi Alembic awal di branch `542230` di-merge, agar cukup satu migrasi):
- Tabel `kegiatan_rutin`, `agenda`, `jadwal_task` (§3, §7)
- Level goal mingguan (§4)
- Kolom effort/impact & tabel dependensi task (lihat `backend/ai_model/CATATAN_INTEGRASI.md`)

Untuk Annora (PM/UX):
- Pertanyaan terbuka di §3, §4, §6
- Alur UI input kegiatan rutin & agenda mingguan
