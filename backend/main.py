from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base
from backend.routers import patterns, screening

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Stock Screener API", version="1.0.0")

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
