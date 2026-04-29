import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models, schemas
from backend.services.screener import run_screening

router = APIRouter()


@router.post("/run", response_model=schemas.ScreeningResponse)
async def run_screening_endpoint(
    request: schemas.ScreeningRequest,
    db: Session = Depends(get_db),
):
    pattern = db.query(models.Pattern).filter(models.Pattern.id == request.pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    try:
        results = await run_screening(
            pattern_id=request.pattern_id,
            db=db,
            tickers=request.tickers,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screening failed: {str(e)}")

    executed_at = datetime.utcnow()
    results_data = [r.model_dump() for r in results]

    db_result = models.ScreeningResult(
        pattern_id=request.pattern_id,
        executed_at=executed_at,
        results_json=json.dumps(results_data, default=str),
    )
    db.add(db_result)
    db.commit()

    return schemas.ScreeningResponse(
        results=results,
        executed_at=executed_at,
        pattern_id=request.pattern_id,
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
