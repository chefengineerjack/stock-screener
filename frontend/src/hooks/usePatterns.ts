import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";
import type { Pattern, PatternCreate } from "../types";

export function usePatterns() {
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPatterns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.patterns.list();
      setPatterns(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load patterns");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPatterns();
  }, [fetchPatterns]);

  const createPattern = useCallback(async (data: PatternCreate): Promise<Pattern> => {
    const created = await api.patterns.create(data);
    setPatterns((prev) => [created, ...prev]);
    return created;
  }, []);

  const updatePattern = useCallback(
    async (id: number, data: PatternCreate): Promise<Pattern> => {
      const updated = await api.patterns.update(id, data);
      setPatterns((prev) => prev.map((p) => (p.id === id ? updated : p)));
      return updated;
    },
    []
  );

  const deletePattern = useCallback(async (id: number): Promise<void> => {
    await api.patterns.delete(id);
    setPatterns((prev) => prev.filter((p) => p.id !== id));
  }, []);

  return { patterns, loading, error, fetchPatterns, createPattern, updatePattern, deletePattern };
}
