import { useState, useCallback } from "react";
import "./index.css";
import { Header } from "./components/Header";
import { PatternList } from "./components/PatternList";
import { PatternForm } from "./components/PatternForm";
import { ScreeningResult, ScreeningHistory } from "./components/ScreeningResult";
import { usePatterns } from "./hooks/usePatterns";
import { api } from "./api/client";
import type { PatternCreate, StockResult, ScreeningHistoryItem } from "./types";

type ViewMode = "detail" | "form" | "new";

export default function App() {
  const { patterns, loading, createPattern, updatePattern, deletePattern } = usePatterns();

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("detail");

  const [screening, setScreening] = useState<{
    running: boolean;
    results: StockResult[];
    executedAt?: string;
    error?: string;
  }>({ running: false, results: [] });

  const [history, setHistory] = useState<ScreeningHistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  const selectedPattern = patterns.find((p) => p.id === selectedId) ?? null;

  const handleSelect = useCallback((id: number) => {
    setSelectedId(id);
    setViewMode("detail");
    setScreening({ running: false, results: [] });
  }, []);

  const handleNew = useCallback(() => {
    setSelectedId(null);
    setViewMode("new");
  }, []);

  const handleSave = useCallback(
    async (data: PatternCreate) => {
      if (viewMode === "new") {
        const created = await createPattern(data);
        setSelectedId(created.id);
        setViewMode("detail");
      } else if (viewMode === "form" && selectedId !== null) {
        await updatePattern(selectedId, data);
        setViewMode("detail");
      }
    },
    [viewMode, selectedId, createPattern, updatePattern]
  );

  const handleDelete = useCallback(async () => {
    if (selectedId === null) return;
    await deletePattern(selectedId);
    setSelectedId(null);
    setViewMode("detail");
  }, [selectedId, deletePattern]);

  const handleRunScreening = useCallback(async () => {
    if (!selectedPattern) return;
    setScreening({ running: true, results: [] });
    try {
      const res = await api.screening.run(selectedPattern.id);
      setScreening({ running: false, results: res.results, executedAt: res.executed_at });
    } catch (e) {
      setScreening({
        running: false,
        results: [],
        error: e instanceof Error ? e.message : "スクリーニング実行中にエラーが発生しました",
      });
    }
  }, [selectedPattern]);

  const handleShowHistory = useCallback(async () => {
    setShowHistory(true);
    try {
      const h = await api.screening.history();
      setHistory(h);
    } catch {
      setHistory([]);
    }
  }, []);

  return (
    <div className="flex flex-col h-screen bg-gray-100" style={{ fontFamily: "system-ui, sans-serif" }}>
      <Header />

      <div className="flex flex-1 overflow-hidden">
        <PatternList
          patterns={patterns}
          selectedId={selectedId}
          onSelect={handleSelect}
          onNew={handleNew}
          loading={loading}
        />

        <main className="flex-1 overflow-y-auto p-6">
          {(viewMode === "new" || viewMode === "form") ? (
            <div className="max-w-2xl mx-auto">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h2 className="text-lg font-semibold text-gray-800 mb-5">
                  {viewMode === "new" ? "新規パターン作成" : "パターン編集"}
                </h2>
                <PatternForm
                  pattern={viewMode === "form" ? selectedPattern : null}
                  onSave={handleSave}
                  onDelete={viewMode === "form" ? handleDelete : undefined}
                  onCancel={() => setViewMode(selectedId ? "detail" : "detail")}
                />
              </div>
            </div>
          ) : selectedPattern ? (
            <div className="space-y-5">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">{selectedPattern.name}</h2>
                    <div className="flex items-center gap-3 mt-2">
                      <span className={`px-2.5 py-1 rounded text-xs font-semibold ${
                        selectedPattern.market === "US"
                          ? "bg-blue-100 text-blue-700"
                          : "bg-red-100 text-red-700"
                      }`}>
                        {selectedPattern.market === "US" ? "米国株" : "日本株"}
                      </span>
                      <span className="px-2.5 py-1 bg-gray-100 text-gray-600 rounded text-xs font-semibold">
                        {selectedPattern.logic}
                      </span>
                      <span className="text-sm text-gray-400">
                        {selectedPattern.conditions.length} 条件
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => setViewMode("form")}
                    className="text-sm text-gray-500 hover:text-gray-700 border border-gray-300 rounded-md px-3 py-1.5 hover:bg-gray-50 transition-colors"
                  >
                    編集
                  </button>
                </div>

                {selectedPattern.conditions.length > 0 && (
                  <div className="mt-4">
                    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                      スクリーニング条件
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {selectedPattern.conditions.map((c) => (
                        <span
                          key={c.id}
                          className="inline-block bg-blue-50 text-blue-700 text-xs px-2.5 py-1 rounded-full border border-blue-100"
                        >
                          {c.label}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex gap-3 mt-5 pt-5 border-t border-gray-100">
                  <button
                    onClick={handleRunScreening}
                    disabled={screening.running || selectedPattern.conditions.length === 0}
                    className="bg-green-600 hover:bg-green-500 disabled:bg-gray-300 text-white font-medium py-2.5 px-6 rounded-lg text-sm transition-colors flex items-center gap-2"
                  >
                    {screening.running ? (
                      <>
                        <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        スクリーニング実行中...
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                        スクリーニング実行
                      </>
                    )}
                  </button>

                  <button
                    onClick={handleShowHistory}
                    className="border border-gray-300 hover:bg-gray-50 text-gray-600 font-medium py-2.5 px-5 rounded-lg text-sm transition-colors"
                  >
                    実行履歴
                  </button>
                </div>
              </div>

              {screening.error && (
                <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
                  {screening.error}
                </div>
              )}

              {(screening.results.length > 0 || screening.running) && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <h3 className="text-base font-semibold text-gray-800 mb-4">スクリーニング結果</h3>
                  {screening.running ? (
                    <div className="flex items-center gap-3 py-8 justify-center text-gray-400">
                      <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      <span className="text-sm">データを取得してスクリーニング中...</span>
                    </div>
                  ) : (
                    <ScreeningResult results={screening.results} executedAt={screening.executedAt} />
                  )}
                </div>
              )}

              {showHistory && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-base font-semibold text-gray-800">実行履歴</h3>
                    <button
                      onClick={() => setShowHistory(false)}
                      className="text-gray-400 hover:text-gray-600 text-sm"
                    >
                      閉じる
                    </button>
                  </div>
                  <ScreeningHistory history={history} />
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <svg className="w-16 h-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1}
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <p className="text-lg font-medium">パターンを選択してください</p>
              <p className="text-sm mt-1">左サイドバーからパターンを選ぶか、新規作成してください</p>
              <button
                onClick={handleNew}
                className="mt-4 bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 px-5 rounded-lg text-sm transition-colors"
              >
                + 新規パターン作成
              </button>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
