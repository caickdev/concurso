"""Tokens de redefinição de senha ("esqueci minha senha")."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from backend.models.base import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from backend.models.user import User


class PasswordResetToken(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        Index("ix_password_reset_tokens_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # SHA256 do token — nunca armazenamos o token em texto puro, só o hash
    # (mesmo princípio de nunca guardar senha em texto puro: se o banco
    # vazar, o hash sozinho não permite redefinir a senha de ninguém).
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<PasswordResetToken user={self.user_id} used={self.used_at is not None}>"
