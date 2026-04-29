export function Header() {
  return (
    <header className="bg-gray-900 text-white px-6 py-4 flex items-center gap-3 shadow-lg">
      <svg className="w-7 h-7 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
      <h1 className="text-xl font-bold tracking-tight">Stock Screener</h1>
      <span className="ml-auto text-xs text-gray-400">US / JP 株式スクリーニング</span>
    </header>
  );
}
