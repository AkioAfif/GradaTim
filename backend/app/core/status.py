"""Nilai status yang disepakati tim (string biasa, bukan Enum DB)."""

TASK_TODO = "todo"
TASK_IN_PROGRESS = "in_progress"
TASK_DONE = "done"
TASK_STATUSES = (TASK_TODO, TASK_IN_PROGRESS, TASK_DONE)

JADWAL_TERJADWAL = "terjadwal"
JADWAL_SELESAI = "selesai"
JADWAL_DILEWATI = "dilewati"  # user konfirmasi tidak dikerjakan
JADWAL_TIDAK_DIKETAHUI = "tidak_diketahui"  # waktunya lewat tanpa konfirmasi (diset saat susun ulang)
JADWAL_STATUSES = (JADWAL_TERJADWAL, JADWAL_SELESAI, JADWAL_DILEWATI, JADWAL_TIDAK_DIKETAHUI)
# Sesi riwayat: tidak dianggap sibuk, tidak dihitung "sudah terjadwal", tidak dihitung di status task.
JADWAL_TIDAK_AKTIF = (JADWAL_DILEWATI, JADWAL_TIDAK_DIKETAHUI)

GOAL_ACTIVE = "active"

MILESTONE_TIPE_BULANAN = "bulanan"
MILESTONE_TIPE_MINGGUAN = "mingguan"
