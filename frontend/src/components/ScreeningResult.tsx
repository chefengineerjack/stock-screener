import type { StockResult, ScreeningHistoryItem } from "../types";

interface ResultTableProps {
  results: StockResult[];
  executedAt?: string;
}

function formatPrice(price: number): string {
  return price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatChange(change: number): string {
  return `${change >= 0 ? "+" : ""}${change.toFixed(2)}%`;
}

export function ScreeningResult({ results, executedAt }: ResultTableProps) {
  if (results.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-gray-400">
        <svg className="w-12 h-12 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
        <p className="text-sm">条件に合致する銘柄が見つかりませんでした</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-gray-700">
          {results.length} 銘柄ヒット
        </span>
        {executedAt && (
          <span className="text-xs text-gray-400">
            実行: {new Date(executedAt).toLocaleString("ja-JP")}
          </span>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wider">シンボル</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wider">銘柄名</th>
              <th className="text-right px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wider">現在値</th>
              <th className="text-right px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wider">前日比</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wider">セクター</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wider">合致理由</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {results.map((stock) => (
              <tr key={stock.symbol} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 font-mono font-semibold text-blue-600">{stock.symbol}</td>
                <td className="px-4 py-3 text-gray-800 max-w-[200px] truncate">{stock.name}</td>
                <td className="px-4 py-3 text-right font-mono text-gray-800">
                  {formatPrice(stock.price)}
                </td>
                <td className={`px-4 py-3 text-right font-mono font-semibold ${
                  stock.change_1d >= 0 ? "text-green-600" : "text-red-600"
                }`}>
                  {formatChange(stock.change_1d)}
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs max-w-[120px] truncate">{stock.sector}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {stock.match_reasons.map((reason, i) => (
                      <span
                        key={i}
                        className="inline-block bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded-full border border-blue-100"
                      >
                        {reason}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

interface HistoryProps {
  history: ScreeningHistoryItem[];
}

export function ScreeningHistory({ history }: HistoryProps) {
  if (history.length === 0) {
    return <p className="text-sm text-gray-400">実行履歴がありません</p>;
  }

  return (
    <div className="space-y-2">
      {history.map((item) => (
        <div key={item.id} className="flex items-center justify-between bg-gray-50 rounded-md px-3 py-2 text-sm">
          <div>
            <span className="font-medium text-gray-700">{item.pattern_name}</span>
            <span className="ml-2 text-gray-400 text-xs">
              {new Date(item.executed_at).toLocaleString("ja-JP")}
            </span>
          </div>
          <span className="text-blue-600 font-semibold">{item.result_count} 件</span>
        </div>
      ))}
    </div>
  );
}
