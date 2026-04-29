import pandas as pd
import pandas_ta as ta
import numpy as np


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """OHLCVデータフレームに全テクニカル指標を追加"""
    if len(df) < 20:
        return df

    df = df.copy()

    if len(df) >= 14:
        df["RSI_14"] = ta.rsi(df["Close"], length=14)

    if len(df) >= 50:
        df["SMA_50"] = ta.sma(df["Close"], length=50)

    if len(df) >= 200:
        df["SMA_200"] = ta.sma(df["Close"], length=200)

    if len(df) >= 26:
        macd = ta.macd(df["Close"])
        if macd is not None and not macd.empty:
            df["MACD"] = macd.get("MACD_12_26_9", np.nan)
            df["MACD_signal"] = macd.get("MACDs_12_26_9", np.nan)

    if len(df) >= 20:
        bb = ta.bbands(df["Close"], length=20, std=2)
        if bb is not None and not bb.empty:
            df["BB_upper"] = bb.get("BBU_20_2.0", np.nan)
            df["BB_lower"] = bb.get("BBL_20_2.0", np.nan)

        df["Volume_MA20"] = ta.sma(df["Volume"], length=20)

    df["High_52w"] = df["High"].rolling(min(252, len(df))).max()
    df["Low_52w"] = df["Low"].rolling(min(252, len(df))).min()

    if len(df) >= 6:
        df["Return_5d"] = df["Close"].pct_change(5) * 100

    return df


def check_condition(df: pd.DataFrame, condition_type: str, params: dict) -> bool:
    """単一条件の判定"""
    if df.empty or len(df) < 2:
        return False

    last = df.iloc[-1]
    prev = df.iloc[-2]

    handlers = {
        "rsi_oversold": _rsi_oversold,
        "rsi_overbought": _rsi_overbought,
        "golden_cross": _golden_cross,
        "death_cross": _death_cross,
        "above_sma200": _above_sma200,
        "below_sma200": _below_sma200,
        "above_sma50": _above_sma50,
        "near_52w_high": _near_52w_high,
        "near_52w_low": _near_52w_low,
        "price_up_5d": _price_up_5d,
        "price_down_5d": _price_down_5d,
        "volume_spike": _volume_spike,
        "macd_bullish": _macd_bullish,
        "macd_bearish": _macd_bearish,
        "bb_upper": _bb_upper,
        "bb_lower": _bb_lower,
    }

    handler = handlers.get(condition_type)
    if handler is None:
        return False

    try:
        return handler(df, last, prev, params)
    except Exception:
        return False


def _rsi_oversold(df, last, prev, params):
    threshold = params.get("threshold", 30)
    return not pd.isna(last.get("RSI_14")) and last["RSI_14"] < threshold


def _rsi_overbought(df, last, prev, params):
    threshold = params.get("threshold", 70)
    return not pd.isna(last.get("RSI_14")) and last["RSI_14"] > threshold


def _golden_cross(df, last, prev, params):
    days = params.get("days", 5)
    window = df.tail(days + 1)
    if "SMA_50" not in window.columns or "SMA_200" not in window.columns:
        return False
    for i in range(1, len(window)):
        curr = window.iloc[i]
        p = window.iloc[i - 1]
        if (not pd.isna(curr["SMA_50"]) and not pd.isna(curr["SMA_200"]) and
                not pd.isna(p["SMA_50"]) and not pd.isna(p["SMA_200"])):
            if p["SMA_50"] <= p["SMA_200"] and curr["SMA_50"] > curr["SMA_200"]:
                return True
    return False


def _death_cross(df, last, prev, params):
    days = params.get("days", 5)
    window = df.tail(days + 1)
    if "SMA_50" not in window.columns or "SMA_200" not in window.columns:
        return False
    for i in range(1, len(window)):
        curr = window.iloc[i]
        p = window.iloc[i - 1]
        if (not pd.isna(curr["SMA_50"]) and not pd.isna(curr["SMA_200"]) and
                not pd.isna(p["SMA_50"]) and not pd.isna(p["SMA_200"])):
            if p["SMA_50"] >= p["SMA_200"] and curr["SMA_50"] < curr["SMA_200"]:
                return True
    return False


def _above_sma200(df, last, prev, params):
    return ("SMA_200" in last and not pd.isna(last.get("SMA_200")) and
            last["Close"] > last["SMA_200"])


def _below_sma200(df, last, prev, params):
    return ("SMA_200" in last and not pd.isna(last.get("SMA_200")) and
            last["Close"] < last["SMA_200"])


def _above_sma50(df, last, prev, params):
    return ("SMA_50" in last and not pd.isna(last.get("SMA_50")) and
            last["Close"] > last["SMA_50"])


def _near_52w_high(df, last, prev, params):
    ratio = params.get("ratio", 0.95)
    return ("High_52w" in last and not pd.isna(last.get("High_52w")) and
            last["Close"] >= last["High_52w"] * ratio)


def _near_52w_low(df, last, prev, params):
    ratio = params.get("ratio", 1.10)
    return ("Low_52w" in last and not pd.isna(last.get("Low_52w")) and
            last["Close"] <= last["Low_52w"] * ratio)


def _price_up_5d(df, last, prev, params):
    threshold = params.get("threshold", 5.0)
    return ("Return_5d" in last and not pd.isna(last.get("Return_5d")) and
            last["Return_5d"] >= threshold)


def _price_down_5d(df, last, prev, params):
    threshold = params.get("threshold", -5.0)
    return ("Return_5d" in last and not pd.isna(last.get("Return_5d")) and
            last["Return_5d"] <= threshold)


def _volume_spike(df, last, prev, params):
    multiplier = params.get("multiplier", 2.0)
    return ("Volume_MA20" in last and not pd.isna(last.get("Volume_MA20")) and
            last["Volume"] > last["Volume_MA20"] * multiplier)


def _macd_bullish(df, last, prev, params):
    days = params.get("days", 3)
    window = df.tail(days + 1)
    if "MACD" not in window.columns or "MACD_signal" not in window.columns:
        return False
    for i in range(1, len(window)):
        curr = window.iloc[i]
        p = window.iloc[i - 1]
        if (not pd.isna(curr["MACD"]) and not pd.isna(curr["MACD_signal"]) and
                not pd.isna(p["MACD"]) and not pd.isna(p["MACD_signal"])):
            if p["MACD"] <= p["MACD_signal"] and curr["MACD"] > curr["MACD_signal"]:
                return True
    return False


def _macd_bearish(df, last, prev, params):
    days = params.get("days", 3)
    window = df.tail(days + 1)
    if "MACD" not in window.columns or "MACD_signal" not in window.columns:
        return False
    for i in range(1, len(window)):
        curr = window.iloc[i]
        p = window.iloc[i - 1]
        if (not pd.isna(curr["MACD"]) and not pd.isna(curr["MACD_signal"]) and
                not pd.isna(p["MACD"]) and not pd.isna(p["MACD_signal"])):
            if p["MACD"] >= p["MACD_signal"] and curr["MACD"] < curr["MACD_signal"]:
                return True
    return False


def _bb_upper(df, last, prev, params):
    return ("BB_upper" in last and not pd.isna(last.get("BB_upper")) and
            last["Close"] > last["BB_upper"])


def _bb_lower(df, last, prev, params):
    return ("BB_lower" in last and not pd.isna(last.get("BB_lower")) and
            last["Close"] < last["BB_lower"])
