
export const PLANS_STORAGE_KEY = "gradatim-plans";

export type SavedPlan = {
  id: string;
  title: string;
  deadline: string;
  category: string;
  priority: "Low" | "Medium" | "High";
  reflection: string;
  createdAt: string;
  planningData: Record<string, unknown>;
};

export function getSavedPlans(): SavedPlan[] {
  try {
    const stored = localStorage.getItem(PLANS_STORAGE_KEY);

    if (!stored) return [];

    const parsed: unknown = JSON.parse(stored);

    if (!Array.isArray(parsed)) return [];

    return parsed.filter(
      (item): item is SavedPlan =>
        typeof item === "object" &&
        item !== null &&
        typeof item.id === "string" &&
        typeof item.title === "string"
    );
  } catch (error) {
    console.error("Gagal membaca rencana:", error);
    return [];
  }
}

export function savePlan(plan: SavedPlan): void {
  const plans = getSavedPlans();

  localStorage.setItem(
    PLANS_STORAGE_KEY,
    JSON.stringify([plan, ...plans])
  );
}
