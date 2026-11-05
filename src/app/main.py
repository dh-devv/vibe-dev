from fastapi import FastAPI

from src.app.config import settings

app = FastAPI(title="미루기 재판소 API")
app.state.settings = settings


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
