import yfinance as yf
import pandas as pd
from typing import Optional
import logging

logger = logging.getLogger(__name__)

SP500_FALLBACK = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "UNH", "LLY",
    "JPM", "V", "AVGO", "XOM", "PG", "MA", "HD", "COST", "MRK", "ABBV",
    "CVX", "CRM", "BAC", "PEP", "KO", "TMO", "ACN", "MCD", "CSCO", "WMT",
    "ABT", "NFLX", "LIN", "ADBE", "DHR", "AMD", "TXN", "PM", "WFC", "NEE",
    "INTC", "ORCL", "VZ", "BMY", "AMGN", "RTX", "QCOM", "HON", "UNP", "COP",
]


def get_sp500_tickers() -> list[str]:
    """WikipediaからS&P500構成銘柄を取得（失敗時はフォールバック）"""
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", timeout=10)
        tickers = tables[0]["Symbol"].tolist()
        return [t.replace(".", "-") for t in tickers]
    except Exception as e:
        logger.warning(f"Failed to fetch S&P500 from Wikipedia: {e}, using fallback list")
        return SP500_FALLBACK


def fetch_us_stock_data(tickers: list[str], period: str = "1y") -> dict[str, pd.DataFrame]:
    """yfinanceで株価データをバッチ取得（50銘柄ずつ）"""
    results = {}
    batch_size = 50

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        try:
            raw = yf.download(
                batch,
                period=period,
                group_by="ticker",
                threads=True,
                progress=False,
                auto_adjust=True,
            )
            if raw.empty:
                continue

            if len(batch) == 1:
                ticker = batch[0]
                if not raw.empty:
                    results[ticker] = raw.copy()
            else:
                for ticker in batch:
                    try:
                        if ticker in raw.columns.get_level_values(0):
                            df = raw[ticker].dropna(how="all")
                            if not df.empty and len(df) >= 20:
                                results[ticker] = df
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Batch download failed for {batch[:3]}...: {e}")

    return results


def get_stock_info(ticker: str) -> dict:
    """個別銘柄の情報取得"""
    try:
        info = yf.Ticker(ticker).info
        return {
            "name": info.get("longName") or info.get("shortName", ticker),
            "sector": info.get("sector", "N/A"),
        }
    except Exception:
        return {"name": ticker, "sector": "N/A"}


def get_us_stock_metadata(tickers: list[str]) -> dict[str, dict]:
    """複数銘柄のメタデータを取得"""
    meta = {}
    for ticker in tickers:
        meta[ticker] = get_stock_info(ticker)
    return meta
