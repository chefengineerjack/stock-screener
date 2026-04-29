import { useState, useEffect } from "react";
import type { Pattern, PatternCreate, Market, Logic, PresetCondition } from "../types";
import { PRESET_CONDITIONS } from "../types";
import { ConditionSelector } from "./ConditionSelector";

interface Props {
  pattern?: Pattern | null;
  onSave: (data: PatternCreate) => Promise<void>;
  onDelete?: () => Promise<void>;
  onCancel: () => void;
}

export function PatternForm({ pattern, onSave, onDelete, onCancel }: Props) {
  const [name, setName] = useState("");
  const [market, setMarket] = useState<Market>("US");
  const [logic, setLogic] = useState<Logic>("AND");
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (pattern) {
      setName(pattern.name);
      setMarket(pattern.market);
      setLogic(pattern.logic);
      setSelectedTypes(pattern.conditions.map((c) => c.condition_type));
    } else {
      setName("");
      setMarket("US");
      setLogic("AND");
      setSelectedTypes([]);
    }
  }, [pattern]);

  const handleToggle = (cond: PresetCondition) => {
    setSelectedTypes((prev) =>
      prev.includes(cond.type) ? prev.filter((t) => t !== cond.type) : [...prev, cond.type]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setSaving(true);
    setError(null);
    try {
      const conditions = selectedTypes.map((type) => {
        const preset = PRESET_CONDITIONS.find((p) => p.type === type)!;
        return { condition_type: type, label: preset.label, params: preset.params };
      });
      await onSave({ name: name.trim(), market, logic, conditions });
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存に失敗しました");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!onDelete || !confirm("このパターンを削除しますか?")) return;
    setSaving(true);
    try {
      await onDelete();
    } catch (e) {
      setError(e instanceof Error ? e.message : "削除に失敗しました");
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">パターン名</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="例: RSI売られすぎ + ゴールデンクロス"
          required
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="flex gap-4">
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-700 mb-1">対象市場</label>
          <select
            value={market}
            onChange={(e) => setMarket(e.target.value as Market)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="US">米国株 (US)</option>
            <option value="JP">日本株 (JP)</option>
          </select>
        </div>

        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-700 mb-1">条件ロジック</label>
          <select
            value={logic}
            onChange={(e) => setLogic(e.target.value as Logic)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="AND">AND (すべて合致)</option>
            <option value="OR">OR (いずれか合致)</option>
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          スクリーニング条件
          <span className="ml-2 text-xs text-gray-400">({selectedTypes.length} 件選択中)</span>
        </label>
        <div className="border border-gray-200 rounded-md p-4 max-h-80 overflow-y-auto bg-gray-50">
          <ConditionSelector selected={selectedTypes} onToggle={handleToggle} />
        </div>
      </div>

      {error && (
        <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-md px-3 py-2">
          {error}
        </div>
      )}

      <div className="flex gap-3 pt-2">
        <button
          type="submit"
          disabled={saving || !name.trim()}
          className="flex-1 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-300 text-white font-medium py-2 px-4 rounded-md text-sm transition-colors"
        >
          {saving ? "保存中..." : pattern ? "更新" : "作成"}
        </button>

        <button
          type="button"
          onClick={onCancel}
          className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2 px-4 rounded-md text-sm transition-colors"
        >
          キャンセル
        </button>

        {pattern && onDelete && (
          <button
            type="button"
            onClick={handleDelete}
            disabled={saving}
            className="bg-red-100 hover:bg-red-200 text-red-700 font-medium py-2 px-4 rounded-md text-sm transition-colors"
          >
            削除
          </button>
        )}
      </div>
    </form>
  );
}
