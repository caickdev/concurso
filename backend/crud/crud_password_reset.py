import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.security import hash_password
from backend.models.password_reset import PasswordResetToken
from backend.models.user import User


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


async def create_reset_token(db: AsyncSession, user: User) -> str:
    """Gera um token aleatório, salva só o hash dele no banco, e retorna o
    token bruto (usado uma única vez, para montar o link do e-mail)."""
    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    )
    entry = PasswordResetToken(
        user_id=user.id, token_hash=_hash_token(raw_token), expires_at=expires_at
    )
    db.add(entry)
    await db.commit()
    return raw_token


async def get_valid_token(db: AsyncSession, raw_token: str) -> PasswordResetToken | None:
    token_hash = _hash_token(raw_token)
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        return None
    if entry.used_at is not None:
        return None
    if entry.expires_at < datetime.now(timezone.utc):
        return None
    return entry


async def consume_token_and_reset_password(
    db: AsyncSession, entry: PasswordResetToken, user: User, new_password: str
) -> None:
    """Marca o token como usado e atualiza a senha, em uma única transação."""
    entry.used_at = datetime.now(timezone.utc)
    user.password_hash = hash_password(new_password)
    db.add(entry)
    db.add(user)
    await db.commit()
