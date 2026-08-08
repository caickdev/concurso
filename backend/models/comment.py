from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from backend.models.base import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from backend.models.question import Question
    from backend.models.user import User

# Comentário passa a ficar oculto automaticamente ao atingir esta contagem de denúncias.
AUTO_HIDE_REPORT_THRESHOLD = 5


class StudentComment(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "student_comments"
    __table_args__ = (
        Index("ix_comments_question_approved", "question_id", "is_approved"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    report_count: Mapped[int] = mapped_column(default=0, nullable=False)

    user: Mapped["User"] = relationship(back_populates="comments")
    question: Mapped["Question"] = relationship(back_populates="comments")
    reports: Mapped[List["CommentReport"]] = relationship(
        back_populates="comment", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<StudentComment {self.id} question={self.question_id}>"


class CommentReport(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "comment_reports"
    __table_args__ = (
        # Um usuário só pode denunciar o mesmo comentário uma vez.
        Index("ux_comment_reports_comment_user", "comment_id", "user_id", unique=True),
    )

    comment_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("student_comments.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)

    comment: Mapped["StudentComment"] = relationship(back_populates="reports")
    user: Mapped["User"] = relationship(back_populates="comment_reports")

    def __repr__(self) -> str:
        return f"<CommentReport comment={self.comment_id} user={self.user_id}>"
