import { api } from "./client";
import type { TaskRead, TaskStatus } from "./types";

export type TaskFilter = {
  id_goal?: number;
  status?: TaskStatus;
};

export async function listTasks(filter: TaskFilter = {}): Promise<TaskRead[]> {
  const { data } = await api.get<TaskRead[]>("/tasks", { params: filter });
  return data;
}

export async function getTask(idTask: number): Promise<TaskRead> {
  const { data } = await api.get<TaskRead>(`/tasks/${idTask}`);
  return data;
}

/** Ubah status task (checklist). Sesi jadwal tidak disentuh backend. */
export async function updateTaskStatus(idTask: number, status: TaskStatus): Promise<TaskRead> {
  const { data } = await api.patch<TaskRead>(`/tasks/${idTask}`, { status });
  return data;
}
