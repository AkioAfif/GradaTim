# Komponen Kecerdasan Buatan — GradaTim

GradaTim memakai dua komponen AI dengan peran berbeda:

| Komponen | Tugas | Status |
| --- | --- | --- |
| **Perencana LLM** | Memecah goal besar menjadi target bulanan → mingguan → task | ✅ Terimplementasi |
| **Model personalisasi** | Memprediksi peluang sebuah sesi jadwal benar-benar dikerjakan user, untuk menempatkan task di slot yang tepat | 🚧 Rancangan |

Singkatnya: **LLM merencanakan, model kami mempersonalisasi.** LLM unggul memahami bahasa dan menyusun
langkah dari goal apa pun; ia tidak tahu kebiasaan masing-masing user. Bagian itu dipelajari model
personalisasi dari data penggunaan GradaTim sendiri.

---

## 1. Perencana LLM (terimplementasi)

### Alur

```
User membuat goal (judul, deskripsi, deadline, menit harian opsional)
        │
        ▼
POST /api/v1/goals/{id_goal}/decompose
        │
        ├─ rencana.py      → hitung kerangka tanggal: minggu Senin–Minggu & bulan kalender
        ├─ ai_service.py   → LLM mengisi judul/tujuan tiap bulan & minggu + task MINGGU KE-1 saja
        ├─ ai_service.py   → normalisasi output (lihat di bawah)
        └─ goal_service.py → simpan ke milestone (bulanan/mingguan), task, task_dependency
        │
        ▼
Setiap minggu berikutnya:
POST /api/v1/goals/{id_goal}/rinci-minggu?minggu=ini|depan
        └─ LLM merinci task minggu itu berdasarkan target minggu itu, target minggu
           berikutnya, dan progres task minggu-minggu sebelumnya (selesai / belum)
```

### Keputusan desain

**Task dirinci per minggu, bukan semuanya di awal.** Rencana yang dibuat sekaligus di awal cepat
basi begitu user tertinggal atau lebih cepat dari perkiraan. Dengan merinci per minggu, LLM bisa melihat
apa yang benar-benar selesai. Kalau banyak task tertinggal, task minggu itu dibuat lebih sedikit dan ringan.

**Tanggal dihitung sistem, bukan LLM.** LLM tidak andal dalam aritmetika tanggal. Kerangka minggu dan
bulan dihitung `rencana.py` lalu diberikan ke LLM; LLM hanya mengisi konten.

**Structured output (strict JSON schema).** Respons LLM langsung di-parse ke model Pydantic
(`GoalPlan`, `WeekTasks`) lewat `client.chat.completions.parse`, sehingga tidak ada parsing teks manual.

**Normalisasi setelah output.** Output LLM tidak dipercaya mentah-mentah:
- durasi task di-*clamp* ke 10–240 menit;
- task dinomori ulang 1..N sesuai urutan;
- dependensi yang menunjuk task tidak ada, diri sendiri, atau task yang lebih belakang dibuang,
  sehingga tidak mungkin terjadi dependensi melingkar;
- judul target yang kosong diganti judul cadangan.

**Tahan gagal.** Timeout 90 detik, retry otomatis hingga 4 kali (untuk 429/503 yang sering hanya sesaat).
Bila tetap gagal, API mengembalikan `502` dengan pesan yang bersih dan **tidak ada data yang tersimpan
setengah jadi**.

**Tidak terikat provider.** Klien memakai SDK `openai` ke endpoint apa pun yang kompatibel OpenAI.
Default-nya Google Gemini; ganti provider atau model cukup lewat `.env` (`LLM_BASE_URL`, `LLM_MODEL`).

**Teruji tanpa API key.** Seluruh tes (`pytest`) memakai LLM tiruan (*mock*), sehingga CI tidak
bergantung pada kuota atau jaringan.

Output LLM juga mengisi `effort_level` dan `impact_level` tiap task, yang dipakai untuk tampilan
Effort vs Impact (FR-9) dan sebagai fitur model personalisasi.

---

## 2. Model personalisasi (rancangan)

### Masalah yang diselesaikan

Penjadwal saat ini menaruh task di slot kosong mana pun yang muat. Padahal kemungkinan seseorang
benar-benar mengerjakan task berbeda-beda menurut jam, hari, beratnya task, dan kondisinya hari itu.
Task berat di jam 21.00 setelah hari yang melelahkan kemungkinan besar dilewati, lalu menumpuk dan
memicu *overwhelm*, yaitu masalah yang ingin diselesaikan GradaTim.

### Formulasi

Klasifikasi biner per **sesi jadwal** (`jadwal_task`):

- **Label:** sesi dikerjakan (`selesai`) atau tidak (`dilewati`), **hanya dari sesi yang dikonfirmasi user**.
- **Output:** peluang sesi dikerjakan, 0–1.

Status sesi untuk keperluan dataset:

| Kasus | Perlakuan di dataset |
| --- | --- |
| User konfirmasi "selesai" | label 1 |
| User konfirmasi "tidak dikerjakan" | label 0 |
| Waktu lewat tanpa konfirmasi | **dibuang** (tidak diketahui), bukan otomatis 0 |
| Sesi dipindah manual (`PATCH /jadwal/sesi/{id}`) | dicatat terpisah, tidak dihitung gagal |

Membuang sesi tanpa konfirmasi juga menimbulkan bias, karena user yang rajin konfirmasi cenderung
user yang memang rajin. **Tingkat konfirmasi dipantau dan dilaporkan** (per user dan total), dan
konfirmasi dibuat semudah mungkin (tombol di sesi + pengingat akhir hari).

### Fitur kandidat

| Kelompok | Fitur | Sumber |
| --- | --- | --- |
| Waktu | jam mulai, hari dalam minggu, durasi sesi | `jadwal_task` |
| Task | `tingkat_effort`, `tingkat_impact`, sisa hari ke deadline | `task` |
| Kondisi user | 5 jawaban kuesioner mood hari itu | `questionnaire_answer` |
| Riwayat | tingkat penyelesaian user 7 hari terakhir, urutan sesi ke-berapa di hari itu | turunan |

Kuesioner mood tidak lagi punya model sendiri; jawabannya menjadi input model ini.

### Kapan fitur dicatat

Aturannya: **fitur harus sudah diketahui sebelum sesi dimulai** (mencegah kebocoran informasi masa depan).

- Fitur waktu, task, dan riwayat **dibekukan (snapshot) saat sesi dijadwalkan**, misalnya ke kolom JSON
  di `jadwal_task`. Fitur riwayat yang dihitung ulang belakangan rawan ikut menghitung sesi sesudahnya.
- Fitur mood **digabungkan dari kuesioner hari itu**, hanya bila diisi sebelum sesi dimulai. Bila tidak,
  fitur mood kosong dan `mood_diisi = 0`.

### Dua varian model

Saat penjadwal menaruh sesi beberapa hari ke depan, mood belum ada. Memakai satu model dengan
`mood_diisi = 0` di penjadwal itu keliru: di data latih, `mood_diisi = 0` berarti "user tidak mengisi
kuesioner hari itu" (cenderung hari sibuk/malas), bukan "mood belum diketahui". Karena itu dilatih
dua varian dari pipeline yang sama:

| Varian | Fitur | Dipakai di |
| --- | --- | --- |
| **A** | waktu + task + riwayat | penjadwal (FR-4, FR-11) |
| **B** | A + mood + `mood_diisi` | rekomendasi hari ini (FR-7) |

Selisih performa A dan B sekaligus menjawab pertanyaan: *apakah kuesioner mood menambah daya prediksi?*

### Bias seleksi dan eksplorasi

Model hanya melihat hasil di slot yang dipilih penjadwal. Penjadwal saat ini *earliest-fit*: sesi diisi
ke slot kosong paling awal (setelah kegiatan rutin dan waktu sekarang), sehingga sebaran jam mulai di
data sempit dan slot yang jarang dipakai (mis. malam hari) hanya bisa ditebak model, bukan dipelajari.

Selama dogfooding, **sebagian sesi (mis. 30%) ditempatkan di slot acak yang valid** di dalam jam aktif,
dengan batas `daily_cap` tetap berlaku. Sesi eksplorasi ditandai agar bisa dianalisis terpisah.

### Evaluasi

- **Split berdasarkan waktu**, bukan acak: latih di minggu-minggu awal, uji di minggu terakhir.
  Split acak membocorkan informasi masa depan ke data latih.
- **Dua baseline pembanding:** (1) tingkat penyelesaian rata-rata user, (2) aturan heuristik yang ada sekarang.
  Model hanya dipakai bila mengalahkan keduanya.
- **Metrik:** ROC-AUC dan F1, ditambah kalibrasi peluang (Brier score, reliability plot) karena
  outputnya dipakai sebagai skor. Karena test set kecil (±100 sesi), semua metrik dilaporkan dengan
  **interval kepercayaan bootstrap**.
- **Model:** mulai dari logistic regression (mudah dijelaskan), lalu Random Forest atau gradient boosting.
- **Hasil negatif tetap sah.** Bila model tidak mengalahkan baseline "tingkat penyelesaian rata-rata
  user", hasil itu dilaporkan apa adanya dan penjadwal tetap memakai heuristik.

**Batas klaim penjelasan.** Koefisien logistic regression yang dilatih dari gabungan semua user
menggambarkan pola umum ("secara umum task berat lebih sering selesai pagi hari"), bukan pola
per orang. Sampel ±50 sesi per user tidak cukup untuk model per user; aspek personal datang dari
fitur riwayat masing-masing user.

### Integrasi

1. **Penjadwal (FR-4, FR-11):** setiap slot kandidat diberi skor oleh varian A; task ber-effort tinggi
   ditempatkan di slot berpeluang tinggi. Batas `daily_cap` yang sudah ada tetap berlaku agar task berat
   tidak menumpuk di beberapa slot "bagus".
2. **Rekomendasi hari ini (FR-7):** task diurutkan memakai peluang dari varian B, dengan mood hari itu
   sebagai input.
3. **Cold start:** user tanpa riwayat memakai aturan heuristik sampai datanya cukup.

### Pengumpulan data

Data diperoleh dari pemakaian riil (*dogfooding*) oleh tim dan pengguna uji. Perkiraan kasar:
10 orang × 4 sesi/hari × 14 hari ≈ 500 sampel. Jumlah ini kecil dan akan dinyatakan sebagai
keterbatasan, tetapi cukup untuk model sederhana dan perbandingan dengan baseline.

---

## 3. Model mood saat ini dan alasan diganti

`backend/ai_model/` berisi Random Forest yang memetakan 5 jawaban mood ke kapasitas LOW/MEDIUM/HIGH
(akurasi 0,87). Model ini akan digantikan model personalisasi karena:

- **Datanya sintetis dan labelnya berasal dari aturan.** Label dibuat dari ambang `total_score`
  (≤13 → LOW, ≤18 → MEDIUM) ditambah noise 15%, sehingga model hanya mempelajari ulang aturan tersebut.
  Akurasi 0,87 mencerminkan tingkat noise yang ditambahkan, bukan kemampuan memahami pengguna.
- **Tidak ada di alur utama.** Hasilnya setara dengan if-else; menghapusnya tidak mengubah perilaku aplikasi.

---

## 4. Keputusan yang masih terbuka

- [ ] **Kebersihan label.** Saat ini sesi menjadi `dilewati` *otomatis* ketika waktunya lewat dan
      jadwal disusun ulang, sehingga sesi yang dikerjakan tapi lupa dicentang tercatat gagal. Selain itu,
      task bisa ditandai `done` lewat `PATCH /tasks` tanpa status sesinya berubah. Arah yang diusulkan:
      konfirmasi eksplisit per sesi + status "tidak diketahui" (lihat tabel di §2).
- [x] **Snapshot fitur.** Diputuskan: fitur waktu/task/riwayat dibekukan saat penjadwalan; mood digabung
      dari kuesioner hari-H bila diisi sebelum sesi mulai (§2 "Kapan fitur dicatat").
- [ ] **Eksplorasi slot acak.** Berapa persen sesi yang diacak, dan apakah user diberi tahu?
- [ ] **Jadwal dogfooding.** Butuh frontend yang tersambung ke backend dan minimal ±2 minggu pemakaian
      sebelum presentasi. Pencatatan data (konfirmasi, snapshot, eksplorasi) harus jalan **sebelum**
      dogfooding dimulai; model bisa dikerjakan sambil menunggu data.
- [ ] **Persetujuan tim** untuk menghapus model mood terpisah.

## 5. Urutan kerja

1. Tutup keputusan terbuka di §4.
2. Pencatatan data: konfirmasi sesi, status "tidak diketahui"/dipindah, snapshot fitur, eksplorasi slot acak.
3. Dogfooding ±2 minggu; pantau tingkat konfirmasi.
4. Paralel dengan (3): pipeline dataset → training → evaluasi, diuji dengan data tiruan.
5. Latih varian A dan B, bandingkan dengan baseline, integrasikan bila menang.
