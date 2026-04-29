import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import logging
import functools
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
    BASE_URL = "https://api.jquants.com/v1"

    def __init__(self, email: str, password: str):
        self._email = email
        self._password = password
        self._token: Optional[str] = None
        self._token_expires: float = 0

    def _ensure_token(self):
        if self._token and time.time() < self._token_expires:
            return
        self._token = self._authenticate()
        self._token_expires = time.time() + 82800  # 23時間

    def _authenticate(self) -> str:
        resp = requests.post(
            f"{self.BASE_URL}/token/auth_user",
            json={"mailaddress": self._email, "password": self._password},
            timeout=30,
        )
        resp.raise_for_status()
        refresh = resp.json()["refreshToken"]

        resp2 = requests.post(
            f"{self.BASE_URL}/token/auth_refresh",
            params={"refreshtoken": refresh},
            timeout=30,
        )
        resp2.raise_for_status()
        return resp2.json()["idToken"]

    def _headers(self) -> dict:
        self._ensure_token()
        return {"Authorization": f"Bearer {self._token}"}

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
                f"{self.BASE_URL}/prices/daily_quotes",
                params={"code": code, "from": from_date, "to": to_date},
                headers=self._headers(),
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get("daily_quotes", [])

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


_client_instance: Optional[JQuantsClient] = None


def get_jquants_client(email: str, password: str) -> JQuantsClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = JQuantsClient(email, password)
    return _client_instance
