from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import SessionLocal, init_db
from .routers import interpret, nav, portfolio, settings, signals, trades
from .seed import seed_funds

app = FastAPI(title="quant-api", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3010"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()
    db = SessionLocal()
    try:
        seed_funds(db)
    finally:
        db.close()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(trades.router)
app.include_router(nav.router)
app.include_router(signals.router)
app.include_router(portfolio.router)
app.include_router(settings.router)
app.include_router(interpret.router)
