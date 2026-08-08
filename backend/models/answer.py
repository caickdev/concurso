from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from backend.models.base import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from backend.models.question import Question
    from backend.models.user import User


class UserAnswer(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "user_answers"
    __table_args__ = (
        # Acelera "quais questões o usuário já respondeu" e o cálculo de streak/XP.
        Index("ix_user_answers_user_created", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    selected_option: Mapped[str] = mapped_column(String(4), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_cebraspe_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="answers")
    question: Mapped["Question"] = relationship(back_populates="user_answers")

    def __repr__(self) -> str:
        return f"<UserAnswer user={self.user_id} question={self.question_id} correct={self.is_correct}>"
