<<<<<<< HEAD
from __future__ import annotations

import secrets
import time
from typing import Any

import httpx
from authlib.integrations.base_client.errors import OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.config import Settings
from src.app.database import get_db
from src.app.models import AppUser, Trial

router = APIRouter()


def _oidc_ready(settings: Settings) -> bool:
    return all(
        (
            settings.oidc_issuer,
            settings.oidc_client_id,
            settings.session_secret_key,
        )
    )


def _csrf_token(request: Request) -> str:
    cookie_token = request.cookies.get("vibe_csrf")
    header_token = request.headers.get("x-csrf-token")
    if (
        not cookie_token
        or not header_token
        or not secrets.compare_digest(cookie_token, header_token)
    ):
        raise HTTPException(status_code=403, detail="CSRF 검증에 실패했습니다.")
    return cookie_token


async def require_csrf(request: Request) -> None:
    _csrf_token(request)


def _user_session(request: Request) -> dict[str, Any]:
    if not _oidc_ready(request.app.state.settings):
        raise HTTPException(status_code=503, detail="인증 제공자 설정이 필요합니다.")
    identity = request.session
    issuer = identity.get("issuer")
    subject = identity.get("subject")
    expires_at = identity.get("expires_at", 0)
    if (
        not isinstance(issuer, str)
        or issuer != request.app.state.settings.oidc_issuer
        or not isinstance(subject, str)
        or not subject
        or not isinstance(expires_at, int)
        or expires_at <= int(time.time())
    ):
        identity.clear()
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    return identity


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> AppUser:
    identity = _user_session(request)
    result = await session.execute(
        select(AppUser).where(
            AppUser.oidc_issuer == identity["issuer"],
            AppUser.oidc_subject == identity["subject"],
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        request.session.clear()
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    return user


async def get_current_user_with_csrf(
    request: Request,
    user: AppUser = Depends(get_current_user),
) -> AppUser:
    _csrf_token(request)
    return user


def _oauth_client(request: Request) -> Any:
    client = getattr(request.app.state, "oidc_client", None)
    if client is None:
        raise HTTPException(status_code=503, detail="인증 제공자 설정이 필요합니다.")
    return client


@router.get("/auth/login")
async def login(request: Request) -> RedirectResponse:
    client = _oauth_client(request)
    redirect_uri = (
        f"{request.app.state.settings.public_base_url.rstrip('/')}/auth/callback"
    )
    try:
        return await client.authorize_redirect(
            request,
            redirect_uri,
            code_challenge_method="S256",
        )
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=503,
            detail="로그인 서비스에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.",
        ) from error


@router.get("/auth/callback")
async def callback(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Response:
    client = _oauth_client(request)
    try:
        token = await client.authorize_access_token(request)
    except OAuthError as error:
        raise HTTPException(status_code=401, detail="로그인 인증을 완료하지 못했습니다.") from error
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=503,
            detail="로그인 서비스에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.",
        ) from error

    claims = token.get("userinfo")
    if not isinstance(claims, dict):
        raise HTTPException(status_code=401, detail="로그인 인증을 완료하지 못했습니다.")
    issuer = claims.get("iss")
    subject = claims.get("sub")
    expires_at = claims.get("exp", token.get("expires_at"))
    if (
        not isinstance(issuer, str)
        or issuer != request.app.state.settings.oidc_issuer
        or not isinstance(subject, str)
        or not subject
        or not isinstance(expires_at, (int, float))
        or expires_at <= time.time()
    ):
        raise HTTPException(status_code=401, detail="로그인 인증을 완료하지 못했습니다.")

    user_query = select(AppUser).where(
        AppUser.oidc_issuer == issuer,
        AppUser.oidc_subject == subject,
    )
    user = (await session.execute(user_query)).scalar_one_or_none()
    if user is None:
        user = AppUser(oidc_issuer=issuer, oidc_subject=subject)
        session.add(user)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            user = (await session.execute(user_query)).scalar_one_or_none()
            if user is None:
                raise

    request.session.clear()
    request.session.update(
        {
            "issuer": issuer,
            "subject": subject,
            "expires_at": min(
                int(expires_at),
                int(time.time()) + request.app.state.settings.session_ttl_seconds,
            ),
        }
    )
    csrf_token = secrets.token_urlsafe(32)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        "vibe_csrf",
        csrf_token,
        max_age=request.app.state.settings.session_ttl_seconds,
        secure=request.app.state.settings.cookie_secure,
        httponly=False,
        samesite="lax",
        path="/",
    )
    return response


@router.post("/auth/logout", dependencies=[Depends(require_csrf)])
async def logout(request: Request) -> Response:
    request.session.clear()
    response = Response(status_code=204)
    response.delete_cookie(
        "vibe_csrf",
        secure=request.app.state.settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/api/me")
async def me(user: AppUser = Depends(get_current_user)) -> dict[str, object]:
    return {"id": str(user.id), "authenticated": True}


@router.delete("/api/account")
async def delete_account(
    request: Request,
    user: AppUser = Depends(get_current_user_with_csrf),
    session: AsyncSession = Depends(get_db),
) -> Response:
    await session.execute(delete(Trial).where(Trial.owner_id == user.id))
    await session.execute(delete(AppUser).where(AppUser.id == user.id))
    await session.commit()
    request.session.clear()
    response = Response(status_code=204)
    response.delete_cookie(
        "vibe_csrf",
        secure=request.app.state.settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return response
=======
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Request

from src.app.db import ensure_user, get_pool
from src.app.errors import ApiError

# OIDC 연동 전 로컬 개발용 소유자. DEV_AUTH_ENABLED=true일 때만 쓴다
_DEV_ISSUER = "local-dev"
_DEV_SUBJECT = "local-dev-user"


@dataclass(frozen=True)
class Owner:
    issuer: str
    subject: str

    @property
    def key(self) -> str:
        return f"{self.issuer}|{self.subject}"


async def current_owner(request: Request) -> Owner:
    """소유자는 서버가 검증한 인증 정보로만 정한다. 요청의 사용자 ID는 쓰지 않는다."""
    if request.app.state.settings.dev_auth_enabled:
        return Owner(_DEV_ISSUER, _DEV_SUBJECT)
    raise ApiError(401, "UNAUTHORIZED", "로그인이 필요하거나 로그인 세션이 만료되었습니다.", False)


async def owner_id(request: Request, owner: Owner = Depends(current_owner)) -> UUID:
    pool = await get_pool(request)
    return await ensure_user(pool, owner.issuer, owner.subject)
>>>>>>> 382e149d50f0c260af14e231ed70bff13a024f26
