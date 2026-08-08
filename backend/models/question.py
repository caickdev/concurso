"""Modelo central de Questão, com índice composto para os filtros mais usados
e coluna vetorial (pgvector) para busca semântica."""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, List

from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from backend.models.base import TimestampMixin, UpdatedAtMixin, UUIDPKMixin

if TYPE_CHECKING:
    from backend.models.answer import UserAnswer
    from backend.models.comment import StudentComment
    from backend.models.notebook import NotebookItem
    from backend.models.taxonomy import Board, Exam, State, Subject

# Dimensão do embedding — compatível com modelos de embedding de 384 dims
# (ex.: sentence-transformers multilíngue). Ajustável via migração caso o
# modelo de embedding escolhido mude.
EMBEDDING_DIM = 384


class DifficultyLevel(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class Question(Base, UUIDPKMixin, TimestampMixin, UpdatedAtMixin):
    __tablename__ = "questions"
    __table_args__ = (
        # Índice composto cobrindo a combinação de filtros mais comum da rota
        # GET /questions/filter (banca, matéria, ano, dificuldade, estado).
        Index(
            "ix_questions_filter_composite",
            "board_id", "subject_id", "year", "difficulty_level", "state_id",
        ),
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {"A": "...", "B": "...", ...}
    correct_option: Mapped[str] = mapped_column(String(4), nullable=False)  # ex.: "A", "C"

    board_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("boards.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    state_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("states.id", ondelete="SET NULL"), nullable=True, index=True
    )

    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    difficulty_level: Mapped[DifficultyLevel] = mapped_column(
        Enum(DifficultyLevel, name="difficulty_level_enum"),
        nullable=False,
        default=DifficultyLevel.MEDIUM,
        index=True,
    )

    # SHA256 do (enunciado + alternativas normalizados) — previne duplicidade
    # no pipeline de scraping mesmo entre fontes distintas.
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    # Embedding pgvector para busca semântica / questões similares.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)

    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    board: Mapped["Board"] = relationship(back_populates="questions")
    subject: Mapped["Subject"] = relationship(back_populates="questions")
    exam: Mapped["Exam"] = relationship(back_populates="questions")
    state: Mapped["State | None"] = relationship(back_populates="questions")

    user_answers: Mapped[List["UserAnswer"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )
    comments: Mapped[List["StudentComment"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )
    notebook_items: Mapped[List["NotebookItem"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Question {self.id} ({self.difficulty_level})>"
