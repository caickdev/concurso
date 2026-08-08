"""Hashing de senha, criação/validação de JWT e dependências de autenticação (cookie HttpOnly)."""
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from backend.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenPayload(BaseModel):
    sub: str  # user_id
    exp: datetime
    type: Literal["access", "refresh"]


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def _create_token(subject: UUID, expires_delta: timedelta, token_type: Literal["access", "refresh"]) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "exp": now + expires_delta,
        "iat": now,
        "type": token_type,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: UUID) -> str:
    return _create_token(
        user_id, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), "access"
    )


def create_refresh_token(user_id: UUID) -> str:
    return _create_token(
        user_id, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), "refresh"
    )


def decode_token(token: str) -> TokenPayload:
    try:
        raw = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return TokenPayload(**raw)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas ou token expirado.",
        ) from exc


def set_auth_cookie(response, token: str) -> None:
    """Define o cookie HttpOnly/Secure/SameSite=Strict com o access token."""
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )


def clear_auth_cookie(response) -> None:
    response.delete_cookie(key=settings.COOKIE_NAME, path="/", domain=settings.COOKIE_DOMAIN)


async def get_current_user_id(
    access_token: str | None = Cookie(default=None, alias=settings.COOKIE_NAME),
) -> UUID:
    """Extrai e valida o usuário autenticado a partir do cookie HttpOnly."""
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado.",
        )
    payload = decode_token(access_token)
    if payload.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tipo de token inválido.",
        )
    return UUID(payload.sub)


async def get_current_user_id_optional(
    access_token: str | None = Cookie(default=None, alias=settings.COOKIE_NAME),
) -> UUID | None:
    if access_token is None:
        return None
    try:
        payload = decode_token(access_token)
        return UUID(payload.sub)
    except HTTPException:
        return None
