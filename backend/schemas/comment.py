import uuid
from datetime import datetime

import bleach
from pydantic import BaseModel, Field, field_validator

from backend.schemas.common import ORMModel

_ALLOWED_TAGS: list[str] = []  # comentários são texto puro — nenhuma tag HTML permitida


class CommentCreate(BaseModel):
    content: str = Field(min_length=3, max_length=2000)

    @field_validator("content")
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        cleaned = bleach.clean(v, tags=_ALLOWED_TAGS, strip=True).strip()
        if not cleaned:
            raise ValueError("Comentário inválido.")
        return cleaned


class CommentRead(ORMModel):
    id: uuid.UUID
    question_id: uuid.UUID
    user_id: uuid.UUID
    author_name: str
    content: str
    created_at: datetime


class CommentReportCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=255)

    @field_validator("reason")
    @classmethod
    def sanitize_reason(cls, v: str) -> str:
        return bleach.clean(v, tags=[], strip=True).strip()
