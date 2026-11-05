from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        retryable: bool = False,
        headers: Mapping[str, str] | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(code)
        self.status = status
        self.code = code
        self.message = message
        self.retryable = retryable
        self.headers = dict(headers or {})
        self.extra = dict(extra or {})


def error_body(code: str, message: str, retryable: bool = False) -> dict[str, Any]:
    return {"code": code, "message": message, "retryable": retryable}


def _validation_message(errors: list[Any]) -> str:
    fields = {str(part) for err in errors for part in err.get("loc", ())}
    if "case" in fields:
        return "사건 내용은 5자 이상 300자 이하로 입력해 주세요."
    if "deadline" in fields:
        return "마감일은 오늘부터 365일 이내의 YYYY-MM-DD 형식으로 입력해 주세요."
    return "요청 형식이 올바르지 않습니다. 입력 내용을 확인해 주세요."


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(_request: Request, exc: ApiError) -> JSONResponse:
        body = {**error_body(exc.code, exc.message, exc.retryable), **exc.extra}
        return JSONResponse(body, status_code=exc.status, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # 오류 본문에 사용자 입력을 되돌려 주지 않는다
        body = error_body("INVALID_INPUT", _validation_message(exc.errors()))
        return JSONResponse(body, status_code=422)
