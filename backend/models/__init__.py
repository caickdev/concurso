"""Agrega todos os modelos ORM para que `Base.metadata` os conheça (Alembic autogenerate)."""
from backend.models.answer import UserAnswer
from backend.models.comment import CommentReport, StudentComment
from backend.models.notebook import NotebookItem, NotebookStatus
from backend.models.password_reset import PasswordResetToken
from backend.models.question import DifficultyLevel, Question
from backend.models.taxonomy import Board, Exam, State, Subject
from backend.models.user import User

__all__ = [
    "User",
    "State",
    "Board",
    "Subject",
    "Exam",
    "Question",
    "DifficultyLevel",
    "UserAnswer",
    "StudentComment",
    "CommentReport",
    "NotebookItem",
    "NotebookStatus",
    "PasswordResetToken",
]
