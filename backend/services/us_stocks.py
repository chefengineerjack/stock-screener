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

            if isinstance(raw.columns, pd.MultiIndex):
                for ticker in batch:
                    try:
                        if ticker in raw.columns.get_level_values(0):
                            df = raw[ticker].dropna(how="all")
                            if not df.empty and len(df) >= 20:
                                results[ticker] = df
                    except Exception:
                        pass
            else:
                # Single ticker: flat column structure
                if len(batch) == 1:
                    df = raw.dropna(how="all")
                    if not df.empty and len(df) >= 20:
                        results[batch[0]] = df
        except Exception as e:
            logger.warning(f"Batch download failed for {batch[:3]}...: {e}")

    return results


def fetch_stock_info_batch(tickers: list[str]) -> dict[str, dict]:
    """合致銘柄の名前・セクター情報を取得（ヒット後の少数銘柄のみ呼ぶ）"""
    result = {}
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
            result[ticker] = {
                "name": info.get("longName") or info.get("shortName") or ticker,
                "sector": info.get("sector") or "N/A",
            }
        except Exception:
            result[ticker] = {"name": ticker, "sector": "N/A"}
    return result
