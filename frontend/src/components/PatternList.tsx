import type { Pattern } from "../types";

interface Props {
  patterns: Pattern[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onNew: () => void;
  loading: boolean;
}

export function PatternList({ patterns, selectedId, onSelect, onNew, loading }: Props) {
  return (
    <aside className="w-64 bg-gray-800 text-white flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
        <span className="font-semibold text-sm text-gray-300">パターン一覧</span>
        <button
          onClick={onNew}
          className="bg-blue-600 hover:bg-blue-500 text-white text-xs px-3 py-1 rounded-md transition-colors"
        >
          + 新規
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-4 text-gray-400 text-sm text-center">読み込み中...</div>
        ) : patterns.length === 0 ? (
          <div className="p-4 text-gray-400 text-sm text-center">
            パターンがありません
          </div>
        ) : (
          <ul>
            {patterns.map((p) => (
              <li key={p.id}>
                <button
                  onClick={() => onSelect(p.id)}
                  className={`w-full text-left px-4 py-3 border-b border-gray-700 transition-colors hover:bg-gray-700 ${
                    selectedId === p.id ? "bg-gray-700 border-l-4 border-l-blue-500" : ""
                  }`}
                >
                  <div className="text-sm font-medium truncate">{p.name}</div>
                  <div className="text-xs text-gray-400 mt-0.5 flex items-center gap-2">
                    <span className={`px-1.5 py-0.5 rounded text-xs font-semibold ${
                      p.market === "US" ? "bg-blue-900 text-blue-300" : "bg-red-900 text-red-300"
                    }`}>
                      {p.market}
                    </span>
                    <span>{p.logic}</span>
                    <span>{p.conditions.length} 条件</span>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
