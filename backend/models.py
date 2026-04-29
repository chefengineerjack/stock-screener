from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base


class Pattern(Base):
    __tablename__ = "patterns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    market = Column(String, nullable=False)  # "US" | "JP"
    logic = Column(String, nullable=False, default="AND")  # "AND" | "OR"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    conditions = relationship("Condition", back_populates="pattern", cascade="all, delete-orphan")
    screening_results = relationship("ScreeningResult", back_populates="pattern", cascade="all, delete-orphan")


class Condition(Base):
    __tablename__ = "conditions"

    id = Column(Integer, primary_key=True, index=True)
    pattern_id = Column(Integer, ForeignKey("patterns.id"), nullable=False)
    condition_type = Column(String, nullable=False)
    label = Column(String, nullable=False)
    params = Column(JSON, default={})

    pattern = relationship("Pattern", back_populates="conditions")


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    id = Column(Integer, primary_key=True, index=True)
    pattern_id = Column(Integer, ForeignKey("patterns.id"), nullable=False)
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
    results_json = Column(Text, nullable=False, default="[]")

    pattern = relationship("Pattern", back_populates="screening_results")
