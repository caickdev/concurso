"""Entidades de suporte para os filtros: Estado, Banca, Matéria e Concurso/Órgão."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from backend.models.base import UUIDPKMixin

if TYPE_CHECKING:
    from backend.models.question import Question


class State(Base, UUIDPKMixin):
    """Unidade federativa (UF) do concurso — ex.: SP, RJ, DF, ou 'Federal'."""
    __tablename__ = "states"

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    uf: Mapped[str] = mapped_column(String(2), unique=True, index=True, nullable=False)

    questions: Mapped[List["Question"]] = relationship(back_populates="state")

    def __repr__(self) -> str:
        return f"<State {self.uf}>"


class Board(Base, UUIDPKMixin):
    """Banca organizadora — ex.: CEBRASPE, FGV, FCC, VUNESP."""
    __tablename__ = "boards"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    # Aliases conhecidos normalizados para esta banca (ex.: CESPE/UnB -> CEBRASPE).
    aliases: Mapped[List[str]] = mapped_column(
        ARRAY(String(120)), nullable=False, default=list
    )

    questions: Mapped[List["Question"]] = relationship(back_populates="board")

    def __repr__(self) -> str:
        return f"<Board {self.name}>"


class Subject(Base, UUIDPKMixin):
    """Matéria/disciplina — ex.: Direito Constitucional, Português."""
    __tablename__ = "subjects"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)

    questions: Mapped[List["Question"]] = relationship(back_populates="subject")

    def __repr__(self) -> str:
        return f"<Subject {self.name}>"


class Exam(Base, UUIDPKMixin):
    """Concurso/órgão específico — ex.: 'TRF 3ª Região 2023 - Técnico Judiciário'."""
    __tablename__ = "exams"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)  # cargo
    year: Mapped[int] = mapped_column(nullable=False, index=True)

    questions: Mapped[List["Question"]] = relationship(back_populates="exam")

    def __repr__(self) -> str:
        return f"<Exam {self.organization} {self.year}>"
