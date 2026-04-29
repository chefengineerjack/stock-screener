from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models, schemas

router = APIRouter()


@router.get("", response_model=list[schemas.PatternResponse])
def list_patterns(db: Session = Depends(get_db)):
    return db.query(models.Pattern).order_by(models.Pattern.created_at.desc()).all()


@router.post("", response_model=schemas.PatternResponse)
def create_pattern(pattern: schemas.PatternCreate, db: Session = Depends(get_db)):
    db_pattern = models.Pattern(
        name=pattern.name,
        market=pattern.market,
        logic=pattern.logic,
    )
    db.add(db_pattern)
    db.flush()

    for cond in pattern.conditions:
        db_cond = models.Condition(
            pattern_id=db_pattern.id,
            condition_type=cond.condition_type,
            label=cond.label,
            params=cond.params,
        )
        db.add(db_cond)

    db.commit()
    db.refresh(db_pattern)
    return db_pattern


@router.put("/{pattern_id}", response_model=schemas.PatternResponse)
def update_pattern(pattern_id: int, pattern: schemas.PatternUpdate, db: Session = Depends(get_db)):
    db_pattern = db.query(models.Pattern).filter(models.Pattern.id == pattern_id).first()
    if not db_pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    db_pattern.name = pattern.name
    db_pattern.market = pattern.market
    db_pattern.logic = pattern.logic

    db.query(models.Condition).filter(models.Condition.pattern_id == pattern_id).delete()

    for cond in pattern.conditions:
        db_cond = models.Condition(
            pattern_id=pattern_id,
            condition_type=cond.condition_type,
            label=cond.label,
            params=cond.params,
        )
        db.add(db_cond)

    db.commit()
    db.refresh(db_pattern)
    return db_pattern


@router.delete("/{pattern_id}")
def delete_pattern(pattern_id: int, db: Session = Depends(get_db)):
    db_pattern = db.query(models.Pattern).filter(models.Pattern.id == pattern_id).first()
    if not db_pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    db.delete(db_pattern)
    db.commit()
    return {"ok": True}
