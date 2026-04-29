import asyncio
import logging
from datetime import datetime
from typing import Optional, AsyncIterator
from sqlalchemy.orm import Session

from backend import models
from backend.schemas import StockResult
from backend.services.indicators import calculate_indicators, check_condition
from backend.services.us_stocks import get_sp500_tickers, fetch_us_stock_data
from backend.config import get_settings

logger = logging.getLogger(__name__)


async def run_screening(
    pattern_id: int,
    db: Session,
    tickers: Optional[list[str]] = None,
) -> list[StockResult]:
    """スクリーニング実行（メイン関数）"""
    pattern = db.query(models.Pattern).filter(models.Pattern.id == pattern_id).first()
    if not pattern:
        raise ValueError(f"Pattern {pattern_id} not found")

    conditions = pattern.conditions
    if not conditions:
        return []

    if pattern.market == "US":
        return await _screen_us_stocks(pattern, conditions, tickers)
    elif pattern.market == "JP":
        return await _screen_jp_stocks(pattern, conditions, tickers)
    else:
        raise ValueError(f"Unknown market: {pattern.market}")


async def _screen_us_stocks(
    pattern: models.Pattern,
    conditions: list[models.Condition],
    tickers: Optional[list[str]],
) -> list[StockResult]:
    target_tickers = tickers or get_sp500_tickers()

    loop = asyncio.get_event_loop()
    all_data = await loop.run_in_executor(None, fetch_us_stock_data, target_tickers)

    results = []
    for ticker, df in all_data.items():
        try:
            df_with_indicators = calculate_indicators(df)
            match_reasons = _evaluate_conditions(df_with_indicators, conditions, pattern.logic)

            if match_reasons is None:
                continue

            last = df_with_indicators.iloc[-1]
            prev = df_with_indicators.iloc[-2] if len(df_with_indicators) >= 2 else last

            price = float(last["Close"])
            change_1d = float(
                (last["Close"] - prev["Close"]) / prev["Close"] * 100
            ) if prev["Close"] != 0 else 0.0

            results.append(StockResult(
                symbol=ticker,
                name=ticker,
                price=round(price, 2),
                change_1d=round(change_1d, 2),
                sector="N/A",
                match_reasons=match_reasons,
            ))
        except Exception as e:
            logger.debug(f"Error processing {ticker}: {e}")

    return results


async def _screen_jp_stocks(
    pattern: models.Pattern,
    conditions: list[models.Condition],
    tickers: Optional[list[str]],
) -> list[StockResult]:
    settings = get_settings()
    if not settings.jquants_email or not settings.jquants_password:
        raise ValueError("J-Quants credentials not configured")

    from backend.services.jp_stocks import get_jquants_client
    client = get_jquants_client(settings.jquants_email, settings.jquants_password)

    loop = asyncio.get_event_loop()

    if tickers:
        stock_list = [{"Code": t, "CompanyName": t, "Sector17CodeName": "N/A"} for t in tickers]
    else:
        stock_list = await loop.run_in_executor(None, client.get_listed_stocks)

    stock_map = {s["Code"]: s for s in stock_list}
    target_codes = list(stock_map.keys())[:500]

    results = []
    semaphore = asyncio.Semaphore(10)

    async def process_stock(code: str):
        async with semaphore:
            try:
                df = await loop.run_in_executor(None, client.get_daily_quotes_df, code)
                if df.empty or len(df) < 20:
                    return None

                df_with_indicators = calculate_indicators(df)
                match_reasons = _evaluate_conditions(df_with_indicators, conditions, pattern.logic)

                if match_reasons is None:
                    return None

                last = df_with_indicators.iloc[-1]
                prev = df_with_indicators.iloc[-2] if len(df_with_indicators) >= 2 else last

                price = float(last["Close"])
                change_1d = float(
                    (last["Close"] - prev["Close"]) / prev["Close"] * 100
                ) if prev["Close"] != 0 else 0.0

                stock_info = stock_map.get(code, {})
                return StockResult(
                    symbol=code,
                    name=stock_info.get("CompanyName", code),
                    price=round(price, 2),
                    change_1d=round(change_1d, 2),
                    sector=stock_info.get("Sector17CodeName", "N/A"),
                    match_reasons=match_reasons,
                )
            except Exception as e:
                logger.debug(f"Error processing JP stock {code}: {e}")
                return None

    tasks = [process_stock(code) for code in target_codes]
    batch_results = await asyncio.gather(*tasks, return_exceptions=False)

    for r in batch_results:
        if r is not None:
            results.append(r)

    return results


def _evaluate_conditions(
    df,
    conditions: list[models.Condition],
    logic: str,
) -> Optional[list[str]]:
    """条件を評価してヒットした条件のラベルリストを返す（非ヒットはNone）"""
    if not conditions:
        return None

    hit_reasons = []
    for cond in conditions:
        matched = check_condition(df, cond.condition_type, cond.params or {})
        if matched:
            hit_reasons.append(cond.label)

    if logic == "AND":
        if len(hit_reasons) == len(conditions):
            return hit_reasons
        return None
    else:  # OR
        if hit_reasons:
            return hit_reasons
        return None
