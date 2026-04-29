interface Props {
  current: number;
  total: number;
}

export function ProgressBar({ current, total }: Props) {
  const pct = total > 0 ? Math.min(Math.round((current / total) * 100), 100) : 0;

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs text-gray-500">
        <span className="flex items-center gap-1.5">
          <svg className="w-3.5 h-3.5 animate-spin text-blue-500" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          {current.toLocaleString()} / {total.toLocaleString()} 銘柄を処理中...
        </span>
        <span className="font-semibold text-blue-600">{pct}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
        <div
          className="bg-blue-500 h-2 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
