import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from backend.models.notebook import NotebookStatus
from backend.schemas.common import ORMModel
from backend.schemas.question import QuestionListItem


class NotebookItemCreate(BaseModel):
    question_id: uuid.UUID
    personal_notes: str | None = Field(default=None, max_length=4000)


class NotebookItemUpdate(BaseModel):
    personal_notes: str | None = Field(default=None, max_length=4000)
    status: NotebookStatus | None = None


class NotebookItemRead(ORMModel):
    id: uuid.UUID
    question: QuestionListItem
    personal_notes: str | None
    status: NotebookStatus
    created_at: datetime
