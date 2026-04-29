import type { Pattern, PatternCreate, ScreeningResponse, ScreeningHistoryItem } from "../types";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "Request failed");
  }
  return res.json();
}

export const api = {
  patterns: {
    list: () => request<Pattern[]>("/api/patterns"),
    create: (data: PatternCreate) =>
      request<Pattern>("/api/patterns", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: PatternCreate) =>
      request<Pattern>(`/api/patterns/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: number) =>
      request<{ ok: boolean }>(`/api/patterns/${id}`, { method: "DELETE" }),
  },
  screening: {
    run: (patternId: number, tickers?: string[]) =>
      request<ScreeningResponse>("/api/screening/run", {
        method: "POST",
        body: JSON.stringify({ pattern_id: patternId, tickers }),
      }),
    history: () => request<ScreeningHistoryItem[]>("/api/screening/history"),
  },
};
