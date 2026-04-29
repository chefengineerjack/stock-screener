import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, AsyncIterator
from sqlalchemy.orm import Session

from backend import models
from backend.schemas import StockResult
from backend.services.indicators import calculate_indicators, check_condition
from backend.services.us_stocks import get_sp500_tickers, fetch_us_stock_data, fetch_stock_info_batch
from backend.config import get_settings

logger = logging.getLogger(__name__)


async def stream_screening_raw(
    pattern_id: int,
    market: str,
    logic: str,
    conditions_data: list[dict],
    tickers: Optional[list[str]],
    db: Session,
) -> AsyncIterator[dict]:
    """
    プレーンな dict データでスクリーニングをSSEストリーム配信する。
    SQLAlchemy オブジェクトは一切受け取らず、独立したセッションで動作する。
    """
    if not conditions_data:
        yield {"type": "done", "results": [], "executed_at": datetime.utcnow().isoformat()}
        return

    if market == "US":
        async for event in _stream_us_stocks(pattern_id, logic, conditions_data, tickers, db):
            yield event
    elif market == "JP":
        async for event in _stream_jp_stocks(pattern_id, logic, conditions_data, tickers, db):
            yield event
    else:
        yield {"type": "error", "message": f"Unknown market: {market}"}


async def _stream_us_stocks(
    pattern_id: int,
    logic: str,
    conditions_data: list[dict],
    tickers: Optional[list[str]],
    db: Session,
) -> AsyncIterator[dict]:
    target_tickers = tickers or get_sp500_tickers()
    total = len(target_tickers)
    all_results: list[StockResult] = []
    loop = asyncio.get_event_loop()
    batch_size = 50

    yield {"type": "start", "total": total}

    for i in range(0, total, batch_size):
        batch = target_tickers[i:i + batch_size]
        batch_data: dict = await loop.run_in_executor(None, fetch_us_stock_data, batch)

        batch_hits: list[tuple] = []
        for ticker, df in batch_data.items():
            try:
                df_ind = calculate_indicators(df)
                match_reasons = _evaluate_conditions(df_ind, conditions_data, logic)
                if match_reasons is None:
                    continue
                last = df_ind.iloc[-1]
                prev = df_ind.iloc[-2] if len(df_ind) >= 2 else last
                price = float(last["Close"])
                change_1d = (
                    float((last["Close"] - prev["Close"]) / prev["Close"] * 100)
                    if float(prev["Close"]) != 0 else 0.0
                )
                batch_hits.append((ticker, price, change_1d, match_reasons))
            except Exception as e:
                logger.debug(f"Error processing {ticker}: {e}")

        processed = min(i + len(batch), total)

        # ヒット銘柄の名前・セクターを取得（少数なので許容）
        if batch_hits:
            matched_tickers = [h[0] for h in batch_hits]
            info_map: dict = await loop.run_in_executor(None, fetch_stock_info_batch, matched_tickers)
            for ticker, price, change_1d, match_reasons in batch_hits:
                info = info_map.get(ticker, {"name": ticker, "sector": "N/A"})
                all_results.append(StockResult(
                    symbol=ticker,
                    name=info["name"],
                    price=round(price, 2),
                    change_1d=round(change_1d, 2),
                    sector=info["sector"],
                    match_reasons=match_reasons,
                ))

        yield {"type": "progress", "current": processed, "total": total}

    _save_results(pattern_id, all_results, db)

    yield {
        "type": "done",
        "results": [r.model_dump() for r in all_results],
        "executed_at": datetime.utcnow().isoformat(),
    }


async def _stream_jp_stocks(
    pattern_id: int,
    logic: str,
    conditions_data: list[dict],
    tickers: Optional[list[str]],
    db: Session,
) -> AsyncIterator[dict]:
    settings = get_settings()
    if not settings.jquants_email or not settings.jquants_password:
        yield {"type": "error", "message": "J-Quants credentials not configured"}
        return

    from backend.services.jp_stocks import get_jquants_client
    client = get_jquants_client(settings.jquants_email, settings.jquants_password)
    loop = asyncio.get_event_loop()

    if tickers:
        stock_list = [{"Code": t, "CompanyName": t, "Sector17CodeName": "N/A"} for t in tickers]
    else:
        stock_list = await loop.run_in_executor(None, client.get_listed_stocks)

    stock_map = {s["Code"]: s for s in stock_list}
    target_codes = list(stock_map.keys())[:500]
    total = len(target_codes)
    all_results: list[StockResult] = []

    yield {"type": "start", "total": total}

    batch_size = 20
    semaphore = asyncio.Semaphore(10)

    async def process_code(code: str) -> Optional[StockResult]:
        async with semaphore:
            try:
                df = await loop.run_in_executor(None, client.get_daily_quotes_df, code)
                if df.empty or len(df) < 20:
                    return None
                df_ind = calculate_indicators(df)
                match_reasons = _evaluate_conditions(df_ind, conditions_data, logic)
                if match_reasons is None:
                    return None
                last = df_ind.iloc[-1]
                prev = df_ind.iloc[-2] if len(df_ind) >= 2 else last
                price = float(last["Close"])
                change_1d = (
                    float((last["Close"] - prev["Close"]) / prev["Close"] * 100)
                    if float(prev["Close"]) != 0 else 0.0
                )
                info = stock_map.get(code, {})
                return StockResult(
                    symbol=code,
                    name=info.get("CompanyName", code),
                    price=round(price, 2),
                    change_1d=round(change_1d, 2),
                    sector=info.get("Sector17CodeName", "N/A"),
                    match_reasons=match_reasons,
                )
            except Exception as e:
                logger.debug(f"Error processing JP stock {code}: {e}")
                return None

    for i in range(0, total, batch_size):
        batch = target_codes[i:i + batch_size]
        batch_results = await asyncio.gather(*[process_code(c) for c in batch])
        for r in batch_results:
            if r is not None:
                all_results.append(r)
        yield {"type": "progress", "current": min(i + batch_size, total), "total": total}

    _save_results(pattern_id, all_results, db)

    yield {
        "type": "done",
        "results": [r.model_dump() for r in all_results],
        "executed_at": datetime.utcnow().isoformat(),
    }


def _evaluate_conditions(df, conditions_data: list[dict], logic: str) -> Optional[list[str]]:
    """条件を評価してヒットしたラベルのリストを返す（非ヒットはNone）"""
    if not conditions_data:
        return None

    hit_reasons = []
    for cond in conditions_data:
        matched = check_condition(df, cond["condition_type"], cond.get("params") or {})
        if matched:
            hit_reasons.append(cond["label"])

    if logic == "AND":
        return hit_reasons if len(hit_reasons) == len(conditions_data) else None
    else:
        return hit_reasons if hit_reasons else None


def _save_results(pattern_id: int, results: list[StockResult], db: Session) -> None:
    try:
        db_result = models.ScreeningResult(
            pattern_id=pattern_id,
            executed_at=datetime.utcnow(),
            results_json=json.dumps([r.model_dump() for r in results], default=str),
        )
        db.add(db_result)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to save screening result: {e}")
        db.rollback()
