import type { Pattern, PatternCreate, ScreeningHistoryItem } from "../types";

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

export type ScreeningEvent =
  | { type: "start"; total: number }
  | { type: "progress"; current: number; total: number }
  | { type: "done"; results: import("../types").StockResult[]; executed_at: string }
  | { type: "error"; message: string };

async function* streamSSE(path: string, body: object): AsyncGenerator<ScreeningEvent> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok || !res.body) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "Request failed");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          yield JSON.parse(line.slice(6)) as ScreeningEvent;
        } catch {
          // ignore malformed event
        }
      }
    }
  }
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
    stream: (patternId: number, tickers?: string[]) =>
      streamSSE("/api/screening/run-stream", { pattern_id: patternId, tickers }),
    history: () => request<ScreeningHistoryItem[]>("/api/screening/history"),
  },
};
