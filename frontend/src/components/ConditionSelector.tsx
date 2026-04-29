import { PRESET_CONDITIONS, type PresetCondition } from "../types";

interface Props {
  selected: string[];
  onToggle: (condition: PresetCondition) => void;
}

const CATEGORIES = ["RSI", "移動平均", "価格帯", "出来高", "MACD", "ボリンジャーバンド", "ファンダメンタルズ"];

export function ConditionSelector({ selected, onToggle }: Props) {
  return (
    <div className="space-y-4">
      {CATEGORIES.map((category) => {
        const conditions = PRESET_CONDITIONS.filter((c) => c.category === category);
        return (
          <div key={category}>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              {category}
            </h4>
            <div className="grid grid-cols-1 gap-1">
              {conditions.map((cond) => {
                const isSelected = selected.includes(cond.type);
                return (
                  <button
                    key={cond.type}
                    type="button"
                    onClick={() => onToggle(cond)}
                    className={`text-left text-sm px-3 py-2 rounded-md border transition-all ${
                      isSelected
                        ? "border-blue-500 bg-blue-50 text-blue-700 font-medium"
                        : "border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50"
                    }`}
                  >
                    <span className={`mr-2 ${isSelected ? "text-blue-500" : "text-gray-400"}`}>
                      {isSelected ? "✓" : "+"}
                    </span>
                    {cond.label}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
