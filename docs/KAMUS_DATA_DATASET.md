# Kamus Data — Dataset Model Personalisasi

Dataset dihasilkan oleh `backend/scripts/ekspor_dataset.py` (logika di `app/services/dataset_service.py`).
Latar belakang dan rancangan model: [`AI.md`](AI.md) §2.

```
cd backend
.\venv\Scripts\python.exe scripts\ekspor_dataset.py --keluaran dataset_personalisasi.csv
```

## Unit dan cakupan

- **Satu baris = satu sesi jadwal** (`jadwal_task`) yang sudah berakhir sebelum waktu ekspor (`--sampai`).
- **Semua sesi ikut**, termasuk yang belum dikonfirmasi dan sesi eksplorasi, agar tingkat konfirmasi
  bisa dilaporkan. **Untuk training, pakai baris yang `label`-nya terisi.**
- Sesi eksplorasi tidak dipisah; dibedakan lewat kolom `eksplorasi`.
- Identitas user disamarkan (`u01`, `u02`, ...). Dataset tidak memuat nama, email, maupun judul goal/task.
- File CSV hasil ekspor berisi data pengguna: **jangan di-commit** ke repository.

## Kolom

### Identitas dan waktu

| Kolom | Tipe | Arti |
| --- | --- | --- |
| `id_sesi` | int | ID sesi (`jadwal_task.id_jadwal`) |
| `user` | teks | Kode user samaran (`u01`, ...), urut menurut ID user |
| `tanggal` | tanggal | Tanggal sesi dimulai (WIB) |
| `minggu` | tanggal | Senin dari minggu sesi; dipakai untuk split latih/uji berdasarkan waktu |

### Label dan penanda

| Kolom | Tipe | Arti |
| --- | --- | --- |
| `status` | teks | Status sesi saat ekspor: `selesai`, `dilewati`, `tidak_diketahui`, `terjadwal` |
| `label` | 0/1/kosong | **Target.** 1 = user konfirmasi selesai, 0 = user konfirmasi tidak dikerjakan, kosong = belum dikonfirmasi (`tidak_diketahui`, atau `terjadwal` yang sudah lewat) |
| `dipindah` | 0/1 | Sesi pernah dipindah manual oleh user; fitur sudah di-snapshot ulang di slot barunya |
| `eksplorasi` | 0/1 | Slot sesi dipilih acak oleh penjadwal (mengurangi bias seleksi) |

### Fitur snapshot (diambil saat sesi dijadwalkan atau dipindah)

Semua fitur hanya memakai informasi yang sudah diketahui saat snapshot diambil. Kosong untuk sesi yang
dibuat sebelum snapshot fitur ada.

| Kolom | Tipe | Arti |
| --- | --- | --- |
| `fitur_versi` | int | Versi definisi fitur (saat ini 1) |
| `jam_mulai` | desimal | Jam mulai sesi, mis. 19.5 = 19:30 |
| `hari` | int | Hari dalam minggu, 0 = Senin … 6 = Minggu |
| `durasi_menit` | int | Durasi sesi |
| `jam_sebelum_mulai` | desimal | Selisih jam antara saat dijadwalkan dan sesi mulai |
| `effort` | teks | Tingkat usaha task dari perencana LLM: `low`/`medium`/`high` |
| `impact` | teks | Tingkat dampak task dari perencana LLM: `low`/`medium`/`high` |
| `durasi_estimasi_task` | int | Estimasi durasi total task (menit); sebuah task bisa dicicil beberapa sesi |
| `sisa_hari_deadline` | int | Hari dari tanggal sesi ke deadline task (atau deadline goal bila task tidak punya); kosong bila tidak ada deadline |
| `urutan_sesi_hari_itu` | int | Sesi ke-berapa di hari itu (1 = pertama) di antara sesi aktif user |
| `jumlah_sesi_hari_itu` | int | Jumlah sesi aktif user di hari itu |
| `riwayat_selesai` | int | Jumlah sesi user yang dikonfirmasi selesai dalam 7 hari sebelum snapshot |
| `riwayat_dilewati` | int | Jumlah sesi user yang dikonfirmasi dilewati dalam 7 hari sebelum snapshot |
| `tingkat_selesai_riwayat` | desimal | `riwayat_selesai / (riwayat_selesai + riwayat_dilewati)`; kosong bila belum ada riwayat |

### Mood (dari kuesioner hari yang sama)

Mood hanya diisi bila kuesioner hari itu diisi **sebelum sesi mulai** (`mood_questionnaire.diisi_pada`).
Kuesioner yang diisi setelah sesi mulai, atau baris lama tanpa jam pengisian, tidak dipakai.

| Kolom | Tipe | Arti |
| --- | --- | --- |
| `mood_diisi` | 0/1 | 1 bila mood tersedia untuk sesi ini |
| `mood_q1_fokus` | 1–5 | Jawaban pertanyaan fokus |
| `mood_q2_tenang` | 1–5 | Jawaban pertanyaan ketenangan |
| `mood_q3_motivasi` | 1–5 | Jawaban pertanyaan motivasi |
| `mood_q4_tidur` | 1–5 | Jawaban pertanyaan kualitas tidur |
| `mood_q5_kesiapan` | 1–5 | Jawaban pertanyaan kesiapan |

Fitur mood hanya dipakai varian B (rekomendasi hari ini). Varian A (penjadwal) tidak memakai kolom mood
sama sekali, termasuk `mood_diisi` (lihat `AI.md` §2 "Dua varian model").

## Ringkasan yang dicetak skrip

| Angka | Arti |
| --- | --- |
| Sesi berakhir | Jumlah baris dataset |
| selesai / dilewati | Jumlah label 1 / 0 |
| Belum dikonfirmasi | Baris tanpa label |
| Tingkat konfirmasi | Persentase baris berlabel, total dan per user. Dilaporkan karena membuang sesi tanpa konfirmasi bisa menimbulkan bias (user rajin cenderung lebih sering konfirmasi) |
| Sesi eksplorasi | Jumlah dan persentase sesi slot acak |
| Sesi dipindah | Jumlah sesi yang pernah dipindah manual |
| Tanpa snapshot fitur | Sesi lama tanpa fitur (perlu dibuang atau ditangani saat training) |
| Sesi dengan mood | Persentase sesi yang punya data mood |
