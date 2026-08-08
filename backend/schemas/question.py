import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from backend.models.question import DifficultyLevel
from backend.schemas.common import ORMModel


class BoardRead(ORMModel):
    id: uuid.UUID
    name: str
    slug: str


class SubjectRead(ORMModel):
    id: uuid.UUID
    name: str
    slug: str


class StateRead(ORMModel):
    id: uuid.UUID
    name: str
    uf: str


class ExamRead(ORMModel):
    id: uuid.UUID
    name: str
    organization: str
    role: str | None
    year: int


class QuestionFilterParams(BaseModel):
    """Parâmetros do filtro dinâmico GET /questions/filter — usados também como
    chave de cache determinística no Redis."""
    state_id: Optional[uuid.UUID] = None
    board_id: Optional[uuid.UUID] = None
    subject_id: Optional[uuid.UUID] = None
    exam_id: Optional[uuid.UUID] = None
    year: Optional[int] = Field(default=None, ge=1990, le=2100)
    difficulty_level: Optional[DifficultyLevel] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    def cache_key(self) -> str:
        parts = [
            f"state={self.state_id}",
            f"board={self.board_id}",
            f"subject={self.subject_id}",
            f"exam={self.exam_id}",
            f"year={self.year}",
            f"diff={self.difficulty_level}",
            f"page={self.page}",
            f"size={self.page_size}",
        ]
        return "questions:filter:" + "|".join(parts)


class QuestionListItem(ORMModel):
    """Versão resumida para listagens — omite `correct_option` para não vazar o gabarito."""
    id: uuid.UUID
    content: str
    options: Dict[str, str]
    year: int
    difficulty_level: DifficultyLevel
    board: BoardRead
    subject: SubjectRead
    exam: ExamRead
    state: StateRead | None


class QuestionDetail(QuestionListItem):
    """Detalhe completo — o gabarito só é exposto após a resposta ser registrada
    (ver routers/questions.py), nunca em listagens públicas."""
    created_at: datetime


class QuestionAnswerSubmit(BaseModel):
    selected_option: str = Field(min_length=1, max_length=4)
    is_cebraspe_mode: bool = False

    @field_validator("selected_option")
    @classmethod
    def normalize_option(cls, v: str) -> str:
        return v.strip().upper()


class QuestionAnswerResult(BaseModel):
    question_id: uuid.UUID
    selected_option: str
    correct_option: str
    is_correct: bool
    xp_earned: int
    current_streak: int
    total_xp: int


class AIExplanationRequest(BaseModel):
    user_selected_option: Optional[str] = Field(default=None, max_length=4)


class AIExplanationResponse(BaseModel):
    question_id: uuid.UUID
    explanation_markdown: str
    generated_at: datetime


class RawQuestionPayload(BaseModel):
    """Formato intermediário compartilhado por todos os caminhos de ingestão
    de questões (scraper, POST /questions/batch, scripts/insert_questions.py)
    — validado antes de resolver FKs (board/subject/exam/state) e antes de
    gerar o hash de deduplicação."""
    content: str = Field(min_length=1)
    options: Dict[str, str]
    correct_option: str
    board_name: str = Field(min_length=1)
    subject_name: str = Field(min_length=1)
    organization: str = Field(min_length=1)
    role: Optional[str] = None
    year: int = Field(ge=1990, le=2100)
    state_uf: Optional[str] = None
    source_url: Optional[str] = None
    difficulty_hint: Optional[str] = None  # ex.: "fácil", "difícil"
    difficulty_level: Optional[DifficultyLevel] = None  # se informado, pula a heurística

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: Dict[str, str]) -> Dict[str, str]:
        if len(v) < 2:
            raise ValueError("Questão precisa de ao menos 2 alternativas.")
        return v

    @field_validator("correct_option")
    @classmethod
    def normalize_correct_option(cls, v: str) -> str:
        return v.strip().upper()


class QuestionBatchRequest(BaseModel):
    questions: List[RawQuestionPayload] = Field(min_length=1, max_length=200)


class QuestionBatchResult(BaseModel):
    received: int
    invalid: int
    duplicates: int
    inserted: int
    errors: List[str] = Field(default_factory=list)
