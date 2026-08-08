from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from backend.models.base import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from backend.models.answer import UserAnswer
    from backend.models.comment import CommentReport, StudentComment
    from backend.models.notebook import NotebookItem


class User(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Gamificação
    daily_goal: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_active_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)

    answers: Mapped[List["UserAnswer"]] = relationship(back_populates="user")
    comments: Mapped[List["StudentComment"]] = relationship(back_populates="user")
    comment_reports: Mapped[List["CommentReport"]] = relationship(back_populates="user")
    notebook_items: Mapped[List["NotebookItem"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.email}>"
