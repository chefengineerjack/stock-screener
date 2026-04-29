from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base, SessionLocal
from backend.routers import patterns, screening
from backend import models

Base.metadata.create_all(bind=engine)


PRESET_PATTERNS = [
    {
        "name": "バリュー株スクリーナー（米国）",
        "market": "US",
        "logic": "AND",
        "conditions": [
            {"condition_type": "per_low", "label": "PER 割安 (< 15)", "params": {"threshold": 15}},
            {"condition_type": "pbr_low", "label": "PBR 1倍割れ", "params": {"threshold": 1.0}},
            {"condition_type": "above_sma200", "label": "SMA200 上抜け", "params": {}},
        ],
    },
    {
        "name": "モメンタム株スクリーナー（米国）",
        "market": "US",
        "logic": "AND",
        "conditions": [
            {"condition_type": "above_sma200", "label": "SMA200 上抜け", "params": {}},
            {"condition_type": "above_sma50", "label": "SMA50 上抜け", "params": {}},
            {"condition_type": "near_52w_high", "label": "52週高値 95%以内", "params": {"ratio": 0.95}},
            {"condition_type": "rsi_overbought", "label": "RSI 買われすぎ (RSI > 70)", "params": {"threshold": 70}},
        ],
    },
    {
        "name": "ゴールデンクロス直後（米国）",
        "market": "US",
        "logic": "AND",
        "conditions": [
            {"condition_type": "golden_cross", "label": "ゴールデンクロス (SMA50 > SMA200)", "params": {"days": 5}},
            {"condition_type": "volume_spike", "label": "出来高急増 (20日平均 × 2)", "params": {"multiplier": 2.0}},
        ],
    },
    {
        "name": "売られすぎ反発狙い（米国）",
        "market": "US",
        "logic": "AND",
        "conditions": [
            {"condition_type": "rsi_oversold", "label": "RSI 売られすぎ (RSI < 30)", "params": {"threshold": 30}},
            {"condition_type": "near_52w_low", "label": "52週安値 110%以内", "params": {"ratio": 1.10}},
            {"condition_type": "above_sma200", "label": "SMA200 上抜け", "params": {}},
        ],
    },
    {
        "name": "ボリンジャースクイーズ後のブレイク（米国）",
        "market": "US",
        "logic": "AND",
        "conditions": [
            {"condition_type": "bb_squeeze", "label": "BBスクイーズ（バンド幅収縮）", "params": {"lookback": 120, "percentile": 20}},
            {"condition_type": "volume_spike", "label": "出来高急増 (20日平均 × 2)", "params": {"multiplier": 2.0}},
        ],
    },
    {
        "name": "上昇トレンド継続（BB上限ウォーク）",
        "market": "US",
        "logic": "AND",
        "conditions": [
            {"condition_type": "bb_walk_up", "label": "BBバンドウォーク上昇", "params": {"days": 5, "min_count": 4}},
            {"condition_type": "above_sma50", "label": "SMA50 上抜け", "params": {}},
        ],
    },
    {
        "name": "高配当・低PER（米国）",
        "market": "US",
        "logic": "AND",
        "conditions": [
            {"condition_type": "dividend_high", "label": "高配当利回り (> 3%)", "params": {"threshold": 0.03}},
            {"condition_type": "per_low", "label": "PER 割安 (< 15)", "params": {"threshold": 15}},
        ],
    },
    {
        "name": "高成長テック株スクリーナー（米国）",
        "market": "US",
        "logic": "AND",
        "conditions": [
            {"condition_type": "revenue_growth", "label": "売上高成長率 (> 10%)", "params": {"threshold": 0.10}},
            {"condition_type": "profit_margin_high", "label": "利益率高い (> 20%)", "params": {"threshold": 0.20}},
            {"condition_type": "market_cap_large", "label": "大型株 (時価総額 > $100億)", "params": {"threshold": 10_000_000_000}},
        ],
    },
    {
        "name": "小型成長株スクリーナー（米国）",
        "market": "US",
        "logic": "AND",
        "conditions": [
            {"condition_type": "market_cap_small", "label": "小型株 (時価総額 < $20億)", "params": {"threshold": 2_000_000_000}},
            {"condition_type": "revenue_growth", "label": "売上高成長率 (> 10%)", "params": {"threshold": 0.10}},
            {"condition_type": "above_sma50", "label": "SMA50 上抜け", "params": {}},
        ],
    },
    {
        "name": "MACDクロス＋出来高増加（米国）",
        "market": "US",
        "logic": "AND",
        "conditions": [
            {"condition_type": "macd_bullish", "label": "MACDゴールデンクロス", "params": {"days": 3}},
            {"condition_type": "volume_spike", "label": "出来高急増 (20日平均 × 2)", "params": {"multiplier": 2.0}},
        ],
    },
    {
        "name": "日本株 バリュー株スクリーナー",
        "market": "JP",
        "logic": "AND",
        "conditions": [
            {"condition_type": "per_low", "label": "PER 割安 (< 15)", "params": {"threshold": 15}},
            {"condition_type": "pbr_low", "label": "PBR 1倍割れ", "params": {"threshold": 1.0}},
            {"condition_type": "above_sma200", "label": "SMA200 上抜け", "params": {}},
        ],
    },
    {
        "name": "日本株 モメンタムスクリーナー",
        "market": "JP",
        "logic": "AND",
        "conditions": [
            {"condition_type": "above_sma200", "label": "SMA200 上抜け", "params": {}},
            {"condition_type": "near_52w_high", "label": "52週高値 95%以内", "params": {"ratio": 0.95}},
            {"condition_type": "volume_spike", "label": "出来高急増 (20日平均 × 2)", "params": {"multiplier": 2.0}},
        ],
    },
]


def seed_initial_patterns():
    db = SessionLocal()
    try:
        state = db.query(models.AppState).filter(models.AppState.key == "patterns_seeded").first()
        if state:
            return

        for p in PRESET_PATTERNS:
            pattern = models.Pattern(
                name=p["name"],
                market=p["market"],
                logic=p["logic"],
            )
            db.add(pattern)
            db.flush()
            for c in p["conditions"]:
                condition = models.Condition(
                    pattern_id=pattern.id,
                    condition_type=c["condition_type"],
                    label=c["label"],
                    params=c.get("params", {}),
                )
                db.add(condition)

        db.add(models.AppState(key="patterns_seeded", value="1"))
        db.commit()
    except Exception as e:
        db.rollback()
        import logging
        logging.getLogger(__name__).error(f"Failed to seed initial patterns: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_initial_patterns()
    yield


app = FastAPI(title="Stock Screener API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(patterns.router, prefix="/api/patterns", tags=["patterns"])
app.include_router(screening.router, prefix="/api/screening", tags=["screening"])


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
