import { api } from "./client";
import type { TimeConstraintCreate, TimeConstraintRead, TimeConstraintUpdate } from "./types";

export async function listTimeConstraints(): Promise<TimeConstraintRead[]> {
  const { data } = await api.get<TimeConstraintRead[]>("/time-constraints");
  return data;
}

export async function createTimeConstraint(payload: TimeConstraintCreate): Promise<TimeConstraintRead> {
  const { data } = await api.post<TimeConstraintRead>("/time-constraints", payload);
  return data;
}

export async function updateTimeConstraint(
  idConstraint: number,
  payload: TimeConstraintUpdate
): Promise<TimeConstraintRead> {
  const { data } = await api.patch<TimeConstraintRead>(`/time-constraints/${idConstraint}`, payload);
  return data;
}

export async function deleteTimeConstraint(idConstraint: number): Promise<void> {
  await api.delete(`/time-constraints/${idConstraint}`);
}
