import pandas as pd
import numpy as np


def _sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(window=length, min_periods=length).mean()


def _ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False, min_periods=length).mean()


def _rsi(series: pd.Series, length: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=length - 1, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(com=length - 1, adjust=False, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(series: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = _ema(series, fast)
    ema_slow = _ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return macd_line, signal_line


def _bbands(series: pd.Series, length: int = 20, std: float = 2.0):
    mid = _sma(series, length)
    rolling_std = series.rolling(window=length, min_periods=length).std()
    upper = mid + std * rolling_std
    lower = mid - std * rolling_std
    return upper, lower


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """OHLCVデータフレームに全テクニカル指標を追加"""
    if len(df) < 20:
        return df

    df = df.copy()
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    if len(df) >= 14:
        df["RSI_14"] = _rsi(close, 14)

    if len(df) >= 50:
        df["SMA_50"] = _sma(close, 50)

    if len(df) >= 200:
        df["SMA_200"] = _sma(close, 200)

    if len(df) >= 35:
        macd_line, signal_line = _macd(close)
        df["MACD"] = macd_line
        df["MACD_signal"] = signal_line

    if len(df) >= 20:
        bb_upper, bb_lower = _bbands(close, 20, 2.0)
        df["BB_upper"] = bb_upper
        df["BB_lower"] = bb_lower
        df["Volume_MA20"] = _sma(volume, 20)

    window_52w = min(252, len(df))
    df["High_52w"] = high.rolling(window_52w).max()
    df["Low_52w"] = low.rolling(window_52w).min()

    if len(df) >= 6:
        df["Return_5d"] = close.pct_change(5) * 100

    return df


def check_condition(df: pd.DataFrame, condition_type: str, params: dict) -> bool:
    """単一条件の判定"""
    if df.empty or len(df) < 2:
        return False

    last = df.iloc[-1]

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
        return handler(df, last, params)
    except Exception:
        return False


def _safe(val) -> bool:
    return val is not None and not (isinstance(val, float) and np.isnan(val))


def _rsi_oversold(df, last, params):
    threshold = params.get("threshold", 30)
    return _safe(last.get("RSI_14")) and last["RSI_14"] < threshold


def _rsi_overbought(df, last, params):
    threshold = params.get("threshold", 70)
    return _safe(last.get("RSI_14")) and last["RSI_14"] > threshold


def _golden_cross(df, last, params):
    days = params.get("days", 5)
    if "SMA_50" not in df.columns or "SMA_200" not in df.columns:
        return False
    window = df.tail(days + 1)
    for i in range(1, len(window)):
        curr = window.iloc[i]
        prev = window.iloc[i - 1]
        if (_safe(curr.get("SMA_50")) and _safe(curr.get("SMA_200")) and
                _safe(prev.get("SMA_50")) and _safe(prev.get("SMA_200"))):
            if prev["SMA_50"] <= prev["SMA_200"] and curr["SMA_50"] > curr["SMA_200"]:
                return True
    return False


def _death_cross(df, last, params):
    days = params.get("days", 5)
    if "SMA_50" not in df.columns or "SMA_200" not in df.columns:
        return False
    window = df.tail(days + 1)
    for i in range(1, len(window)):
        curr = window.iloc[i]
        prev = window.iloc[i - 1]
        if (_safe(curr.get("SMA_50")) and _safe(curr.get("SMA_200")) and
                _safe(prev.get("SMA_50")) and _safe(prev.get("SMA_200"))):
            if prev["SMA_50"] >= prev["SMA_200"] and curr["SMA_50"] < curr["SMA_200"]:
                return True
    return False


def _above_sma200(df, last, params):
    return _safe(last.get("SMA_200")) and last["Close"] > last["SMA_200"]


def _below_sma200(df, last, params):
    return _safe(last.get("SMA_200")) and last["Close"] < last["SMA_200"]


def _above_sma50(df, last, params):
    return _safe(last.get("SMA_50")) and last["Close"] > last["SMA_50"]


def _near_52w_high(df, last, params):
    ratio = params.get("ratio", 0.95)
    return _safe(last.get("High_52w")) and last["Close"] >= last["High_52w"] * ratio


def _near_52w_low(df, last, params):
    ratio = params.get("ratio", 1.10)
    return _safe(last.get("Low_52w")) and last["Close"] <= last["Low_52w"] * ratio


def _price_up_5d(df, last, params):
    threshold = params.get("threshold", 5.0)
    return _safe(last.get("Return_5d")) and last["Return_5d"] >= threshold


def _price_down_5d(df, last, params):
    threshold = params.get("threshold", -5.0)
    return _safe(last.get("Return_5d")) and last["Return_5d"] <= threshold


def _volume_spike(df, last, params):
    multiplier = params.get("multiplier", 2.0)
    return _safe(last.get("Volume_MA20")) and last["Volume"] > last["Volume_MA20"] * multiplier


def _macd_bullish(df, last, params):
    days = params.get("days", 3)
    if "MACD" not in df.columns or "MACD_signal" not in df.columns:
        return False
    window = df.tail(days + 1)
    for i in range(1, len(window)):
        curr = window.iloc[i]
        prev = window.iloc[i - 1]
        if (_safe(curr.get("MACD")) and _safe(curr.get("MACD_signal")) and
                _safe(prev.get("MACD")) and _safe(prev.get("MACD_signal"))):
            if prev["MACD"] <= prev["MACD_signal"] and curr["MACD"] > curr["MACD_signal"]:
                return True
    return False


def _macd_bearish(df, last, params):
    days = params.get("days", 3)
    if "MACD" not in df.columns or "MACD_signal" not in df.columns:
        return False
    window = df.tail(days + 1)
    for i in range(1, len(window)):
        curr = window.iloc[i]
        prev = window.iloc[i - 1]
        if (_safe(curr.get("MACD")) and _safe(curr.get("MACD_signal")) and
                _safe(prev.get("MACD")) and _safe(prev.get("MACD_signal"))):
            if prev["MACD"] >= prev["MACD_signal"] and curr["MACD"] < curr["MACD_signal"]:
                return True
    return False


def _bb_upper(df, last, params):
    return _safe(last.get("BB_upper")) and last["Close"] > last["BB_upper"]


def _bb_lower(df, last, params):
    return _safe(last.get("BB_lower")) and last["Close"] < last["BB_lower"]
