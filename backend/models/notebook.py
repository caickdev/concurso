"""Caderno de Erros — questões marcadas pelo usuário para revisão."""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from backend.models.base import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from backend.models.question import Question
    from backend.models.user import User


class NotebookStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    REVIEWED = "REVIEWED"
    MASTERED = "MASTERED"


class NotebookItem(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "notebook_items"
    __table_args__ = (
        Index("ux_notebook_user_question", "user_id", "question_id", unique=True),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    personal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[NotebookStatus] = mapped_column(
        Enum(NotebookStatus, name="notebook_status_enum"),
        default=NotebookStatus.PENDING_REVIEW,
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship(back_populates="notebook_items")
    question: Mapped["Question"] = relationship(back_populates="notebook_items")

    def __repr__(self) -> str:
        return f"<NotebookItem user={self.user_id} question={self.question_id} status={self.status}>"
