import re
import uuid
from datetime import date, datetime

import bleach
from pydantic import BaseModel, EmailStr, Field, field_validator

from backend.schemas.common import ORMModel

_PASSWORD_MIN_LEN = 8
_PASSWORD_UPPER_RE = re.compile(r"[A-Z]")
_PASSWORD_DIGIT_RE = re.compile(r"\d")


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=_PASSWORD_MIN_LEN, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)

    @field_validator("full_name")
    @classmethod
    def sanitize_full_name(cls, v: str) -> str:
        # Remove qualquer marcação HTML injetada no nome (proteção contra XSS armazenado).
        cleaned = bleach.clean(v, tags=[], strip=True).strip()
        if not cleaned:
            raise ValueError("Nome completo inválido.")
        return cleaned

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not _PASSWORD_UPPER_RE.search(v):
            raise ValueError("A senha deve conter ao menos uma letra maiúscula.")
        if not _PASSWORD_DIGIT_RE.search(v):
            raise ValueError("A senha deve conter ao menos um dígito.")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(ORMModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    daily_goal: int
    current_streak: int
    longest_streak: int
    last_active_date: date | None
    total_xp: int
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    daily_goal: int | None = Field(default=None, ge=1, le=500)

    @field_validator("full_name")
    @classmethod
    def sanitize_full_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return bleach.clean(v, tags=[], strip=True).strip()


class TokenResponse(BaseModel):
    message: str = "Autenticado com sucesso."


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=_PASSWORD_MIN_LEN, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not _PASSWORD_UPPER_RE.search(v):
            raise ValueError("A senha deve conter ao menos uma letra maiúscula.")
        if not _PASSWORD_DIGIT_RE.search(v):
            raise ValueError("A senha deve conter ao menos um dígito.")
        return v


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: uuid.UUID
    full_name: str
    total_xp: int
    current_streak: int
