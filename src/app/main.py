from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from src.app.auth import router as auth_router
from src.app.config import Settings, settings
from src.app.database import create_session_factory
from src.app.rate_limit import InMemoryRateLimiter
from src.app.records import router as records_router
from src.app.trials import router as trials_router

logging.getLogger("uvicorn.access").disabled = True


def _oidc_client(config: Settings) -> Any:
    if not (config.oidc_issuer and config.oidc_client_id and config.session_secret_key):
        return None
    oauth = OAuth()
    oauth.register(
        name="oidc",
        client_id=config.oidc_client_id,
        client_secret=config.oidc_client_secret,
        server_metadata_url=f"{config.oidc_issuer.rstrip('/')}/.well-known/openid-configuration",
        client_kwargs={"scope": "openid"},
    )
    return oauth.create_client("oidc")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    config: Settings = app.state.settings
    if config.database_url:
        app.state.session_factory = create_session_factory(config.database_url)
    app.state.oidc_client = _oidc_client(config)
    yield
    factory = getattr(app.state, "session_factory", None)
    if factory is not None:
        await factory.kw["bind"].dispose()


def create_app(config: Settings = settings) -> FastAPI:
    application = FastAPI(title="미루기 재판소 API", lifespan=lifespan)
    application.state.settings = config
    application.state.session_factory = None
    application.state.oidc_client = None
    application.state.rate_limiter = InMemoryRateLimiter()
    if config.session_secret_key:
        application.add_middleware(
            SessionMiddleware,
            secret_key=config.session_secret_key,
            session_cookie="vibe_session",
            max_age=config.session_ttl_seconds,
            same_site="lax",
            https_only=config.cookie_secure,
        )

    @application.middleware("http")
    async def prevent_private_api_caching(request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        if request.url.path.startswith(("/api/", "/auth/")):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @application.exception_handler(HTTPException)
    async def http_error_handler(
        request: Request, error: HTTPException
    ) -> JSONResponse:
        if isinstance(error.detail, dict):
            body = error.detail
        else:
            body = {
                "code": "HTTP_ERROR",
                "message": str(error.detail),
                "retryable": False,
            }
        return JSONResponse(
            status_code=error.status_code,
            content=body,
            headers=error.headers,
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "code": "INVALID_INPUT",
                "message": "입력 형식을 확인해 주세요.",
                "retryable": False,
            },
        )

    application.include_router(auth_router)
    application.include_router(records_router)
    application.include_router(trials_router)

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    frontend = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    index = frontend / "index.html"
    if index.is_file():
        from starlette.responses import FileResponse

        @application.get("/")
        async def home() -> FileResponse:
            return FileResponse(index)

        @application.get("/{client_path:path}")
        async def frontend_route(client_path: str) -> FileResponse:
            if client_path.startswith(("api/", "auth/")):
                from fastapi import HTTPException

                raise HTTPException(status_code=404, detail="경로를 찾을 수 없습니다.")
            candidate = (frontend / client_path).resolve()
            if frontend.resolve() in candidate.parents and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(index)

    return application


app = create_app()
