import { api } from "./client";
import type { AgendaCreate, AgendaRead, AgendaUpdate, TanggalStr } from "./types";

/** Agenda yang beririsan dengan [mulai, sampai] (inklusif). */
export async function listAgenda(range: { mulai?: TanggalStr; sampai?: TanggalStr } = {}): Promise<AgendaRead[]> {
  const { data } = await api.get<AgendaRead[]>("/agenda", { params: range });
  return data;
}

/** Agenda tetap disimpan walau bentrok; lihat `peringatan_bentrok` di respons. */
export async function createAgenda(payload: AgendaCreate): Promise<AgendaRead> {
  const { data } = await api.post<AgendaRead>("/agenda", payload);
  return data;
}

export async function updateAgenda(idAgenda: number, payload: AgendaUpdate): Promise<AgendaRead> {
  const { data } = await api.patch<AgendaRead>(`/agenda/${idAgenda}`, payload);
  return data;
}

export async function deleteAgenda(idAgenda: number): Promise<void> {
  await api.delete(`/agenda/${idAgenda}`);
}
