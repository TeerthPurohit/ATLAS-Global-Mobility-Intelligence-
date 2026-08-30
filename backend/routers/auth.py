"""Auth router endpoints: POST /auth/signup, POST /auth/login,
POST /auth/logout, GET /auth/me.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Cookie, Depends, Response
from loguru import logger

from backend.errors import DomainError
from backend.schemas import ErrorCode, LoginRequest, SignupRequest, UserOut
from backend.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

_SESSION_MAX_AGE_SECONDS = auth_service.DEFAULT_SESSION_TTL_DAYS * 86400


def _set_session_cookie(response: Response, session_token: str) -> None:
    response.set_cookie(
        key=auth_service.SESSION_COOKIE_NAME,
        value=session_token,
        max_age=_SESSION_MAX_AGE_SECONDS,
        path="/",
        httponly=True,
        secure=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
    )


@router.post("/signup", response_model=UserOut)
def signup(req: SignupRequest, response: Response) -> UserOut:
    logger.info("POST /auth/signup step=start email={}", req.email)
    user = auth_service.create_user(email=req.email, password=req.password)
    session_token = auth_service.create_session(user["id"])
    _set_session_cookie(response, session_token)
    logger.info("POST /auth/signup step=done user_id={}", user["id"])
    return UserOut(**user)


@router.post("/login", response_model=UserOut)
def login(req: LoginRequest, response: Response) -> UserOut:
    logger.info("POST /auth/login step=start email={}", req.email)
    user = auth_service.authenticate_user(email=req.email, password=req.password)
    if user is None:
        logger.warning("POST /auth/login step=invalid_credentials email={}", req.email)
        raise DomainError(ErrorCode.AUTH_INVALID_CREDENTIALS, "Invalid email or password", 401)
    session_token = auth_service.create_session(user["id"])
    _set_session_cookie(response, session_token)
    logger.info("POST /auth/login step=done user_id={}", user["id"])
    return UserOut(**user)


@router.post("/logout")
def logout(response: Response, session_token: str | None = Cookie(default=None, alias=auth_service.SESSION_COOKIE_NAME)) -> dict:
    logger.info("POST /auth/logout step=start")
    if session_token is not None:
        auth_service.delete_session(session_token)
    response.delete_cookie(auth_service.SESSION_COOKIE_NAME, path="/")
    logger.info("POST /auth/logout step=done")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def get_me(current_user: dict = Depends(auth_service.get_current_user)) -> UserOut:  # noqa: B008 -- FastAPI's Depends() idiom
    return UserOut(**current_user)
