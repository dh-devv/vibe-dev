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
