from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from .dependacies import get_db
from fastapi.middleware.cors import CORSMiddleware
from .routes import checkins, activities, sync, insights
from .auth import auth_router

app = FastAPI(title="GoodToday API")

# CORS: allow Vite dev + Capacitor schemes + LAN override via env (optional)
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "capacitor://localhost",
    "ionic://localhost",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(checkins.router)
app.include_router(activities.router)
app.include_router(sync.router)
app.include_router(insights.router)

@app.get("/")
def root():
    return {
        "service": "GoodToday API",
        "status": "ok",
        "docs": "/docs",
        "health": "/healthz",
        "ready": "/readyz"
    }

@app.get("/readyz")
def ready(db: Session = Depends(get_db)):
    # simple DB ping
    db.execute(text("SELECT 1"))
    return {"db": "ok"}

@app.get("/healthz")
def health():
    return {"ok": True}