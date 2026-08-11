import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from backend.models.question import DifficultyLevel
from backend.schemas.question import QuestionListItem


class AnsweredQuestionFilterParams(BaseModel):
    """Parâmetros de GET /users/me/answers — mesmos filtros de matéria/banca/
    ano/dificuldade do /questions/filter, mais is_correct para separar
    questões respondidas certas das erradas."""
    subject_id: Optional[uuid.UUID] = None
    board_id: Optional[uuid.UUID] = None
    year: Optional[int] = Field(default=None, ge=1990, le=2100)
    difficulty_level: Optional[DifficultyLevel] = None
    is_correct: Optional[bool] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class AnsweredQuestionRead(BaseModel):
    """Uma questão já respondida pelo usuário, com o gabarito exposto (só faz
    sentido depois que ele já respondeu) para permitir revisão a qualquer
    momento, separada por acerto/erro."""
    id: uuid.UUID
    question: QuestionListItem
    selected_option: str
    correct_option: str
    is_correct: bool
    answered_at: datetime
