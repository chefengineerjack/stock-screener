from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class ConditionBase(BaseModel):
    condition_type: str
    label: str
    params: dict[str, Any] = {}


class ConditionCreate(ConditionBase):
    pass


class ConditionResponse(ConditionBase):
    id: int
    pattern_id: int

    class Config:
        from_attributes = True


class PatternBase(BaseModel):
    name: str
    market: str  # "US" | "JP"
    logic: str = "AND"  # "AND" | "OR"


class PatternCreate(PatternBase):
    conditions: list[ConditionCreate] = []


class PatternUpdate(PatternBase):
    conditions: list[ConditionCreate] = []


class PatternResponse(PatternBase):
    id: int
    created_at: datetime
    updated_at: datetime
    conditions: list[ConditionResponse] = []

    class Config:
        from_attributes = True


class StockResult(BaseModel):
    symbol: str
    name: str
    price: float
    change_1d: float
    sector: str
    match_reasons: list[str]


class ScreeningRequest(BaseModel):
    pattern_id: int
    tickers: Optional[list[str]] = None


class ScreeningResponse(BaseModel):
    results: list[StockResult]
    executed_at: datetime
    pattern_id: int


class ScreeningHistoryItem(BaseModel):
    id: int
    pattern_id: int
    pattern_name: str
    executed_at: datetime
    result_count: int

    class Config:
        from_attributes = True
