import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload
from backend.database import get_db, SessionLocal
from backend import models, schemas
from backend.services.screener import stream_screening_raw

router = APIRouter()


@router.post("/run-stream")
async def run_screening_stream(
    request: schemas.ScreeningRequest,
    db: Session = Depends(get_db),
):
    """SSEでスクリーニング進捗をストリーム配信するエンドポイント"""
    # セッションが生きているうちにすべてのデータを取得・シリアライズ
    pattern = (
        db.query(models.Pattern)
        .options(selectinload(models.Pattern.conditions))
        .filter(models.Pattern.id == request.pattern_id)
        .first()
    )
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    pattern_id = pattern.id
    market = pattern.market
    logic = pattern.logic
    conditions_data = [
        {"condition_type": c.condition_type, "label": c.label, "params": c.params or {}}
        for c in pattern.conditions
    ]
    tickers = request.tickers

    async def generate():
        # ストリーミング中は独立したセッションを使う
        stream_db = SessionLocal()
        try:
            async for event in stream_screening_raw(
                pattern_id, market, logic, conditions_data, tickers, stream_db
            ):
                yield f"data: {json.dumps(event, default=str)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            stream_db.close()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/history", response_model=list[schemas.ScreeningHistoryItem])
def get_screening_history(db: Session = Depends(get_db)):
    records = (
        db.query(models.ScreeningResult)
        .join(models.Pattern)
        .order_by(models.ScreeningResult.executed_at.desc())
        .limit(50)
        .all()
    )

    items = []
    for r in records:
        try:
            count = len(json.loads(r.results_json))
        except Exception:
            count = 0
        items.append(schemas.ScreeningHistoryItem(
            id=r.id,
            pattern_id=r.pattern_id,
            pattern_name=r.pattern.name,
            executed_at=r.executed_at,
            result_count=count,
        ))
    return items
