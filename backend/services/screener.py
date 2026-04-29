import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, AsyncIterator
from sqlalchemy.orm import Session

from backend import models
from backend.schemas import StockResult
from backend.services.indicators import calculate_indicators, check_condition, FUNDAMENTAL_CONDITIONS
from backend.services.us_stocks import get_sp500_tickers, fetch_us_stock_data, fetch_ticker_data_batch
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

    tech_conds = [c for c in conditions_data if c["condition_type"] not in FUNDAMENTAL_CONDITIONS]
    fund_conds = [c for c in conditions_data if c["condition_type"] in FUNDAMENTAL_CONDITIONS]
    has_fund = bool(fund_conds)

    yield {"type": "start", "total": total}

    for i in range(0, total, batch_size):
        batch = target_tickers[i:i + batch_size]
        batch_data: dict = await loop.run_in_executor(None, fetch_us_stock_data, batch)

        # Technical pre-filter
        tech_hits: list[tuple] = []
        for ticker, df in batch_data.items():
            try:
                df_ind = calculate_indicators(df)
                if logic == "AND":
                    # All tech conditions must pass; fund conditions checked after info fetch
                    tech_match = _evaluate_conditions(df_ind, tech_conds, "AND") if tech_conds else []
                    if tech_conds and tech_match is None:
                        continue
                    last = df_ind.iloc[-1]
                    prev = df_ind.iloc[-2] if len(df_ind) >= 2 else last
                    price = float(last["Close"])
                    change_1d = (
                        float((last["Close"] - prev["Close"]) / prev["Close"] * 100)
                        if float(prev["Close"]) != 0 else 0.0
                    )
                    tech_hits.append((ticker, price, change_1d, df_ind, tech_match or []))
                else:  # OR
                    tech_match = _evaluate_conditions(df_ind, tech_conds, "OR") if tech_conds else None
                    last = df_ind.iloc[-1]
                    prev = df_ind.iloc[-2] if len(df_ind) >= 2 else last
                    price = float(last["Close"])
                    change_1d = (
                        float((last["Close"] - prev["Close"]) / prev["Close"] * 100)
                        if float(prev["Close"]) != 0 else 0.0
                    )
                    if tech_match:
                        # Already satisfied by tech condition in OR
                        tech_hits.append((ticker, price, change_1d, df_ind, tech_match))
                    elif has_fund:
                        # Could still match via fundamentals
                        tech_hits.append((ticker, price, change_1d, df_ind, []))
            except Exception as e:
                logger.debug(f"Error processing {ticker}: {e}")

        processed = min(i + len(batch), total)

        if tech_hits:
            matched_tickers = [h[0] for h in tech_hits]
            info_map: dict = await loop.run_in_executor(None, fetch_ticker_data_batch, matched_tickers)

            for ticker, price, change_1d, df_ind, existing_reasons in tech_hits:
                info = info_map.get(ticker, {"name": ticker, "sector": "N/A"})
                fundamentals = {k: info.get(k) for k in [
                    "pe_ratio", "pb_ratio", "dividend_yield",
                    "profit_margins", "revenue_growth", "market_cap", "debt_to_equity"
                ]}

                if logic == "AND":
                    if fund_conds:
                        fund_match = _evaluate_conditions_fund(fund_conds, "AND", fundamentals)
                        if fund_match is None:
                            continue
                        match_reasons = existing_reasons + fund_match
                    else:
                        match_reasons = existing_reasons
                else:  # OR
                    if fund_conds and not existing_reasons:
                        fund_match = _evaluate_conditions_fund(fund_conds, "OR", fundamentals)
                        if not fund_match:
                            continue
                        match_reasons = fund_match
                    elif fund_conds and existing_reasons:
                        fund_match = _evaluate_conditions_fund(fund_conds, "OR", fundamentals)
                        match_reasons = existing_reasons + (fund_match or [])
                    else:
                        match_reasons = existing_reasons

                if not match_reasons:
                    continue

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
    if not settings.jquants_api_key:
        yield {"type": "error", "message": "J-Quants API key not configured"}
        return

    from backend.services.jp_stocks import get_jquants_client
    client = get_jquants_client(settings.jquants_api_key)
    loop = asyncio.get_event_loop()

    tech_conds = [c for c in conditions_data if c["condition_type"] not in FUNDAMENTAL_CONDITIONS]
    fund_conds = [c for c in conditions_data if c["condition_type"] in FUNDAMENTAL_CONDITIONS]
    has_fund = bool(fund_conds)

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

                last = df_ind.iloc[-1]
                prev = df_ind.iloc[-2] if len(df_ind) >= 2 else last
                price = float(last["Close"])
                change_1d = (
                    float((last["Close"] - prev["Close"]) / prev["Close"] * 100)
                    if float(prev["Close"]) != 0 else 0.0
                )
                info = stock_map.get(code, {})

                if logic == "AND":
                    tech_match = _evaluate_conditions(df_ind, tech_conds, "AND") if tech_conds else []
                    if tech_conds and tech_match is None:
                        return None

                    if has_fund:
                        fundamentals = await loop.run_in_executor(
                            None, client.get_jp_fundamentals, code, price
                        )
                        fund_match = _evaluate_conditions_fund(fund_conds, "AND", fundamentals)
                        if fund_match is None:
                            return None
                        match_reasons = (tech_match or []) + fund_match
                    else:
                        match_reasons = tech_match or []
                else:  # OR
                    tech_match = _evaluate_conditions(df_ind, tech_conds, "OR") if tech_conds else None

                    if tech_match:
                        if has_fund:
                            fundamentals = await loop.run_in_executor(
                                None, client.get_jp_fundamentals, code, price
                            )
                            fund_match = _evaluate_conditions_fund(fund_conds, "OR", fundamentals)
                            match_reasons = tech_match + (fund_match or [])
                        else:
                            match_reasons = tech_match
                    elif has_fund:
                        fundamentals = await loop.run_in_executor(
                            None, client.get_jp_fundamentals, code, price
                        )
                        fund_match = _evaluate_conditions_fund(fund_conds, "OR", fundamentals)
                        if not fund_match:
                            return None
                        match_reasons = fund_match
                    else:
                        return None

                if not match_reasons:
                    return None

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
    """テクニカル条件を評価してヒットしたラベルのリストを返す（非ヒットはNone）"""
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


def _evaluate_conditions_fund(conditions_data: list[dict], logic: str, fundamentals: dict) -> Optional[list[str]]:
    """ファンダメンタルズ条件を評価してヒットしたラベルのリストを返す（非ヒットはNone）"""
    if not conditions_data:
        return []

    hit_reasons = []
    for cond in conditions_data:
        matched = check_condition(None, cond["condition_type"], cond.get("params") or {}, fundamentals)
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
