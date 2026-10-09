"""Nilai status yang disepakati tim (string biasa, bukan Enum DB)."""

TASK_TODO = "todo"
TASK_IN_PROGRESS = "in_progress"
TASK_DONE = "done"
TASK_STATUSES = (TASK_TODO, TASK_IN_PROGRESS, TASK_DONE)

JADWAL_TERJADWAL = "terjadwal"
JADWAL_SELESAI = "selesai"
JADWAL_DILEWATI = "dilewati"
JADWAL_STATUSES = (JADWAL_TERJADWAL, JADWAL_SELESAI, JADWAL_DILEWATI)

GOAL_ACTIVE = "active"

MILESTONE_TIPE_BULANAN = "bulanan"
MILESTONE_TIPE_MINGGUAN = "mingguan"
