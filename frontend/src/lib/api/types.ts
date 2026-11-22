// Tipe respons/request API — cermin schema Pydantic di backend/app/schemas/.
// Datetime dari API berupa string WIB tanpa zona waktu ("2026-11-23T09:00:00"):
// jangan di-parse dengan new Date(str) begitu saja, pakai helper di lib/waktu.ts.
// Jam (time) berupa "HH:MM:SS"; tanggal (date) berupa "YYYY-MM-DD".

/** Datetime WIB naive, mis. "2026-11-23T09:00:00". */
export type WibDateTime = string;
/** Tanggal, "YYYY-MM-DD". */
export type TanggalStr = string;
/** Jam, "HH:MM:SS" (request boleh "HH:MM"). */
export type JamStr = string;

// ---------------- auth (schemas/user.py) ----------------

export type UserRead = {
  id_user: number;
  nama: string;
  email: string;
};

export type UserCreate = {
  nama: string;
  email: string;
  password: string;
};

export type UserLogin = {
  email: string;
  password: string;
};

export type Token = {
  access_token: string;
  token_type: string;
};

// ---------------- task (schemas/task.py) ----------------

export type TaskStatus = "todo" | "in_progress" | "done";

export type TaskRead = {
  id_task: number;
  id_milestone: number;
  id_parent_task: number | null;
  nama_task: string;
  deskripsi: string | null;
  deadline: WibDateTime | null;
  durasi_estimasi: number | null; // menit
  status: TaskStatus;
  tingkat_effort: string | null;
  tingkat_impact: string | null;
  prasyarat: number[]; // id_task yang harus selesai dulu
};

// ---------------- goal (schemas/goal.py) ----------------

export type GoalRead = {
  id_goal: number;
  judul_goal: string;
  deskripsi: string | null;
  deadline: WibDateTime | null;
  status: string;
};

export type GoalCreate = {
  judul_goal: string;
  deskripsi?: string | null;
  deadline: TanggalStr;
};

export type GoalUpdate = Partial<GoalCreate>;

export type MilestoneTipe = "bulanan" | "mingguan";

export type MilestoneRead = {
  id_milestone: number;
  id_parent_milestone: number | null;
  judul_milestone: string;
  deskripsi: string | null;
  deadline: WibDateTime | null;
  urutan: number;
  status: string;
  tipe: MilestoneTipe | null;
  tasks: TaskRead[];
};

/** Milestone berupa daftar datar urut pohon; susun bulanan → mingguan dari id_parent_milestone. */
export type GoalDetail = GoalRead & {
  milestones: MilestoneRead[];
};

export type DecomposeRequest = {
  menit_harian?: number | null; // 15–720; kosong = dihitung backend
};

export type RincianMingguRead = {
  baru: boolean; // false = minggu itu sudah dirinci sebelumnya (AI tidak dipanggil)
  milestone: MilestoneRead;
};

// ---------------- jadwal (schemas/jadwal.py) ----------------

export type StatusSesi = "terjadwal" | "selesai" | "dilewati" | "tidak_diketahui";

export type BlokKalender = {
  nama: string;
  waktu_mulai: WibDateTime;
  waktu_selesai: WibDateTime;
};

export type SesiRead = {
  id_jadwal: number;
  id_task: number;
  id_goal: number;
  nama_task: string;
  waktu_mulai: WibDateTime;
  waktu_selesai: WibDateTime;
  status: StatusSesi;
  dipindah: boolean;
  status_task: TaskStatus;
};

export type JadwalMingguan = {
  mulai: WibDateTime; // Senin 00:00
  akhir: WibDateTime; // Senin berikutnya 00:00
  jam_aktif_mulai: JamStr;
  jam_aktif_selesai: JamStr;
  kegiatan_rutin: BlokKalender[];
  agenda: BlokKalender[];
  sesi: SesiRead[];
};

export type TaskRingkas = {
  id_task: number;
  nama_task: string;
};

export type HasilPenjadwalanRead = {
  sesi_baru: SesiRead[];
  tidak_muat: TaskRingkas[];
};

export type SusunUlangRequest = {
  ditunda?: number[];
};

export type HasilSusunUlangRead = {
  dipindah: TaskRingkas[];
  tidak_muat: TaskRingkas[];
  sesi_baru: SesiRead[];
  sesi_terlewat: SesiRead[];
};

/** `tidak_diketahui` hanya diset sistem, tidak bisa dikirim. */
export type SesiUpdate = {
  status?: "terjadwal" | "selesai" | "dilewati";
  waktu_mulai?: WibDateTime;
  waktu_selesai?: WibDateTime;
};

// ---------------- mood (schemas/mood.py) ----------------

export type MoodAnswers = {
  q1_focus: number;
  q2_calm: number;
  q3_motivated: number;
  q4_sleep: number;
  q5_readiness: number;
};

export type CapacityLevel = "LOW" | "MEDIUM" | "HIGH";

export type MoodAssessment = {
  capacity_level: CapacityLevel;
  capacity_index: number;
  confidence: number;
  probabilities: Record<CapacityLevel, number>;
  max_tasks: number;
  total_mood_score: number;
  recommendation_message: string;
};

export type SesiHariIni = {
  id_jadwal: number;
  waktu_mulai: WibDateTime;
  waktu_selesai: WibDateTime;
};

export type TaskRekomendasi = {
  id_task: number;
  id_goal: number;
  nama_task: string;
  tingkat_effort: string | null;
  tingkat_impact: string | null;
  deadline: WibDateTime | null;
  sesi: SesiHariIni[];
};

export type MoodHariIni = {
  id_questionnaire: number;
  tanggal: TanggalStr;
  jawaban: MoodAnswers;
  hasil: MoodAssessment;
  rekomendasi: {
    direkomendasikan: TaskRekomendasi[];
    disarankan_ditunda: TaskRekomendasi[];
  };
};

// ---------------- kegiatan rutin (schemas/time_constraint.py) ----------------

export type TimeConstraintRead = {
  id_constraint: number;
  id_user: number;
  nama: string;
  hari_dalam_minggu: number; // 0=Senin … 6=Minggu
  waktu_mulai: JamStr;
  waktu_selesai: JamStr; // < waktu_mulai = melewati tengah malam
};

export type TimeConstraintCreate = {
  nama: string;
  hari_dalam_minggu: number;
  waktu_mulai: JamStr;
  waktu_selesai: JamStr;
};

export type TimeConstraintUpdate = Partial<TimeConstraintCreate>;

// ---------------- agenda (schemas/agenda.py) ----------------

export type AgendaRead = {
  id_agenda: number;
  id_user: number;
  nama: string;
  waktu_mulai: WibDateTime;
  waktu_selesai: WibDateTime;
  peringatan_bentrok: string[]; // hanya terisi di respons POST/PATCH
};

/** Mulai & selesai harus di hari yang sama. */
export type AgendaCreate = {
  nama: string;
  waktu_mulai: WibDateTime;
  waktu_selesai: WibDateTime;
};

export type AgendaUpdate = Partial<AgendaCreate>;
