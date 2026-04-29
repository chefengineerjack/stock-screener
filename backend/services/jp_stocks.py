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

    def _get_all_pages(self, url: str, params: dict) -> list[dict]:
        """V2ページネーション対応の全件取得（pagination_keyカーソル方式）"""
        all_data: list[dict] = []
        while True:
            resp = requests.get(url, params=params, headers=self._headers(), timeout=30)
            resp.raise_for_status()
            body = resp.json()
            all_data.extend(body.get("data", []))
            pagination_key = body.get("pagination_key")
            if not pagination_key:
                break
            params = {**params, "pagination_key": pagination_key}
        return all_data

    def get_listed_stocks(self) -> list[dict]:
        """全上場銘柄一覧（キャッシュあり） /v2/equities/master"""
        def fetch():
            return self._get_all_pages(f"{self.BASE_URL}/equities/master", {})

        return _cached("listed_stocks", fetch, ttl=86400)  # 24時間キャッシュ

    def get_daily_quotes(self, code: str, from_date: str, to_date: str) -> list[dict]:
        """日足データ取得（キャッシュあり） /v2/equities/bars/daily"""
        cache_key = f"quotes_{code}_{from_date}_{to_date}"

        def fetch():
            return self._get_all_pages(
                f"{self.BASE_URL}/equities/bars/daily",
                {"code": code, "from": from_date, "to": to_date},
            )

        return _cached(cache_key, fetch, ttl=_cache_ttl)

    def get_daily_quotes_df(self, code: str, days: int = 365) -> pd.DataFrame:
        """日足データをDataFrameで返す"""
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        quotes = self.get_daily_quotes(code, from_date, to_date)
        if not quotes:
            return pd.DataFrame()

        df = pd.DataFrame(quotes)

        # V2カラム名(O/H/L/C/Vo) → 内部標準名(Open/High/Low/Close/Volume)
        rename_map = {
            "Date": "Date",
            "O": "Open",
            "H": "High",
            "L": "Low",
            "C": "Close",
            "Vo": "Volume",
            "AdjC": "AdjClose",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date").sort_index()

        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df.dropna(subset=["Close"])

    def get_fins_summary(self, code: str) -> list[dict]:
        """財務サマリー取得 /v2/fins/summary"""
        cache_key = f"fins_{code}"

        def fetch():
            return self._get_all_pages(f"{self.BASE_URL}/fins/summary", {"code": code})

        return _cached(cache_key, fetch, ttl=86400)

    def get_jp_fundamentals(self, code: str, current_price: float) -> dict:
        """財務サマリーからファンダメンタルズ指標を計算して返す"""
        try:
            summaries = self.get_fins_summary(code)
            if not summaries:
                return {}

            latest = summaries[-1]

            def _safe_float(val):
                try:
                    return float(val) if val is not None else None
                except Exception:
                    return None

            # V2 /fins/summary のカラム名
            eps = _safe_float(latest.get("EPS"))
            bps = _safe_float(latest.get("BPS"))
            div_ann = _safe_float(latest.get("DivAnn"))
            sales = _safe_float(latest.get("Sales"))
            net_profit = _safe_float(latest.get("NP"))
            equity = _safe_float(latest.get("Eq"))
            total_assets = _safe_float(latest.get("TA"))

            fundamentals: dict = {}

            if eps and eps > 0 and current_price > 0:
                fundamentals["pe_ratio"] = current_price / eps

            if bps and bps > 0 and current_price > 0:
                fundamentals["pb_ratio"] = current_price / bps

            if div_ann and current_price > 0:
                fundamentals["dividend_yield"] = div_ann / current_price

            if net_profit and sales and sales > 0:
                fundamentals["profit_margins"] = net_profit / sales

            # D/E = (総資産 - 純資産) / 純資産
            if total_assets and equity and equity > 0:
                fundamentals["debt_to_equity"] = (total_assets - equity) / equity

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
