from fastapi import FastAPI
from .routes import checkins, activities, sync, insights

app = FastAPI(title="GoodToday API")

app.include_router(checkins.router)
app.include_router(activities.router)
app.include_router(sync.router)
app.include_router(insights.router)

@app.get("/healthz")
def health():
    return {"ok": True}