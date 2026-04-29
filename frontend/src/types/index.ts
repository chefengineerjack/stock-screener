export type Market = "US" | "JP";
export type Logic = "AND" | "OR";

export interface Condition {
  id?: number;
  pattern_id?: number;
  condition_type: string;
  label: string;
  params: Record<string, unknown>;
}

export interface Pattern {
  id: number;
  name: string;
  market: Market;
  logic: Logic;
  created_at: string;
  updated_at: string;
  conditions: Condition[];
}

export interface PatternCreate {
  name: string;
  market: Market;
  logic: Logic;
  conditions: Omit<Condition, "id" | "pattern_id">[];
}

export interface StockResult {
  symbol: string;
  name: string;
  price: number;
  change_1d: number;
  sector: string;
  match_reasons: string[];
}

export interface ScreeningResponse {
  results: StockResult[];
  executed_at: string;
  pattern_id: number;
}

export interface ScreeningHistoryItem {
  id: number;
  pattern_id: number;
  pattern_name: string;
  executed_at: string;
  result_count: number;
}

export interface PresetCondition {
  type: string;
  label: string;
  category: string;
  params: Record<string, unknown>;
}

export const PRESET_CONDITIONS: PresetCondition[] = [
  // RSI
  { type: "rsi_oversold", label: "RSI 売られすぎ (RSI < 30)", category: "RSI", params: { threshold: 30 } },
  { type: "rsi_overbought", label: "RSI 買われすぎ (RSI > 70)", category: "RSI", params: { threshold: 70 } },

  // 移動平均
  { type: "golden_cross", label: "ゴールデンクロス (SMA50 > SMA200)", category: "移動平均", params: { days: 5 } },
  { type: "death_cross", label: "デッドクロス (SMA50 < SMA200)", category: "移動平均", params: { days: 5 } },
  { type: "above_sma200", label: "SMA200 上抜け", category: "移動平均", params: {} },
  { type: "below_sma200", label: "SMA200 下抜け", category: "移動平均", params: {} },
  { type: "above_sma50", label: "SMA50 上抜け", category: "移動平均", params: {} },

  // 価格帯
  { type: "near_52w_high", label: "52週高値 95%以内", category: "価格帯", params: { ratio: 0.95 } },
  { type: "near_52w_low", label: "52週安値 110%以内", category: "価格帯", params: { ratio: 1.10 } },
  { type: "price_up_5d", label: "5日間 +5% 以上", category: "価格帯", params: { threshold: 5.0 } },
  { type: "price_down_5d", label: "5日間 -5% 以下", category: "価格帯", params: { threshold: -5.0 } },

  // 出来高
  { type: "volume_spike", label: "出来高急増 (20日平均 × 2)", category: "出来高", params: { multiplier: 2.0 } },

  // MACD
  { type: "macd_bullish", label: "MACDゴールデンクロス", category: "MACD", params: { days: 3 } },
  { type: "macd_bearish", label: "MACDデッドクロス", category: "MACD", params: { days: 3 } },

  // ボリンジャーバンド
  { type: "bb_upper", label: "ボリンジャー上限突破", category: "ボリンジャーバンド", params: {} },
  { type: "bb_lower", label: "ボリンジャー下限割れ", category: "ボリンジャーバンド", params: {} },
];
