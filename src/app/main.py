from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.agents.model import CopilotTrialModel
from src.app import records, trial
from src.app.config import settings
from src.app.errors import register_error_handlers
from src.app.limits import RateLimiter


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await app.state.trial_model.close()
    if app.state.pool is not None:
        await app.state.pool.close()
        app.state.pool = None


app = FastAPI(title="미루기 재판소 API", lifespan=lifespan)
app.state.settings = settings
app.state.pool = None
app.state.limiter = RateLimiter(
    settings.ip_per_minute,
    settings.ip_per_day,
    settings.user_per_minute,
    settings.user_per_day,
    settings.global_per_day,
)
app.state.trial_model = CopilotTrialModel(settings)
register_error_handlers(app)
app.include_router(trial.router)
app.include_router(records.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
