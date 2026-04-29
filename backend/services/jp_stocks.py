import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import logging
import time

logger = logging.getLogger(__name__)

_cache: dict = {}
_cache_ttl = 3600  # 1時間キャッシュ


def _cached(key: str, fn, ttl: int = _cache_ttl):
    now = time.time()
    if key in _cache and now - _cache[key]["ts"] < ttl:
        return _cache[key]["data"]
    data = fn()
    _cache[key] = {"data": data, "ts": now}
    return data


class JQuantsClient:
    BASE_URL = "https://api.jquants.com/v2"

    def __init__(self, api_key: str):
        self._api_key = api_key

    def _headers(self) -> dict:
        return {"x-api-key": self._api_key}

    def get_listed_stocks(self) -> list[dict]:
        """全上場銘柄一覧（キャッシュあり）"""
        def fetch():
            resp = requests.get(
                f"{self.BASE_URL}/listed/info",
                headers=self._headers(),
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get("info", [])

        return _cached("listed_stocks", fetch, ttl=86400)  # 24時間キャッシュ

    def get_daily_quotes(self, code: str, from_date: str, to_date: str) -> list[dict]:
        """日足データ取得（キャッシュあり）"""
        cache_key = f"quotes_{code}_{from_date}_{to_date}"

        def fetch():
            resp = requests.get(
                f"{self.BASE_URL}/equities/bars/daily",
                params={"code": code, "from": from_date, "to": to_date},
                headers=self._headers(),
                timeout=30,
            )
            resp.raise_for_status()
            # V2 レスポンスキーは "bars"
            return resp.json().get("bars", [])

        return _cached(cache_key, fetch, ttl=_cache_ttl)

    def get_daily_quotes_df(self, code: str, days: int = 365) -> pd.DataFrame:
        """日足データをDataFrameで返す"""
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        quotes = self.get_daily_quotes(code, from_date, to_date)
        if not quotes:
            return pd.DataFrame()

        df = pd.DataFrame(quotes)
        rename_map = {
            "Date": "Date",
            "Open": "Open",
            "High": "High",
            "Low": "Low",
            "Close": "Close",
            "Volume": "Volume",
            "AdjustmentClose": "AdjClose",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date").sort_index()

        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df.dropna(subset=["Close"])

    def get_financial_statements(self, code: str) -> list[dict]:
        """財務データ取得（/fins/statements）"""
        cache_key = f"fins_{code}"

        def fetch():
            resp = requests.get(
                f"{self.BASE_URL}/fins/statements",
                params={"code": code},
                headers=self._headers(),
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get("statements", [])

        return _cached(cache_key, fetch, ttl=86400)

    def get_jp_fundamentals(self, code: str, current_price: float) -> dict:
        """財務データからファンダメンタルズ指標を計算して返す"""
        try:
            statements = self.get_financial_statements(code)
            if not statements:
                return {}

            # 最新の財務データを使用
            latest = statements[-1] if statements else {}

            def _safe_float(val):
                try:
                    return float(val) if val is not None else None
                except Exception:
                    return None

            eps = _safe_float(latest.get("EarningsPerShare"))
            bps = _safe_float(latest.get("BookValuePerShare"))
            div_per_share = _safe_float(latest.get("DividendPerShare"))
            net_sales = _safe_float(latest.get("NetSales"))
            net_income = _safe_float(latest.get("NetIncome"))
            equity = _safe_float(latest.get("Equity"))
            total_liabilities = _safe_float(latest.get("TotalLiabilities"))
            shares = _safe_float(latest.get("NumberOfIssuedAndOutstandingSharesAtTheEndOfFiscalYearIncludingTreasuryStock"))

            fundamentals: dict = {}

            # PER
            if eps and eps > 0 and current_price > 0:
                fundamentals["pe_ratio"] = current_price / eps

            # PBR
            if bps and bps > 0 and current_price > 0:
                fundamentals["pb_ratio"] = current_price / bps

            # 配当利回り
            if div_per_share and current_price > 0:
                fundamentals["dividend_yield"] = div_per_share / current_price

            # 利益率
            if net_income and net_sales and net_sales > 0:
                fundamentals["profit_margins"] = net_income / net_sales

            # 時価総額
            if shares and current_price > 0:
                fundamentals["market_cap"] = shares * current_price

            # D/Eレシオ
            if total_liabilities and equity and equity > 0:
                fundamentals["debt_to_equity"] = total_liabilities / equity

            return fundamentals
        except Exception as e:
            logger.debug(f"Failed to get JP fundamentals for {code}: {e}")
            return {}


_client_instance: Optional[JQuantsClient] = None


def get_jquants_client(api_key: str) -> JQuantsClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = JQuantsClient(api_key)
    return _client_instance
