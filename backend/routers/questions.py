import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.rate_limit import limiter
from backend.core.security import get_current_user_id
from backend.crud.crud_answer import crud_answer
from backend.crud.crud_question import crud_question
from backend.crud.crud_user import crud_user
from backend.database import get_db
from backend.schemas.common import Page
from backend.schemas.question import (
    AIExplanationRequest,
    AIExplanationResponse,
    QuestionAnswerResult,
    QuestionAnswerSubmit,
    QuestionDetail,
    QuestionFilterParams,
    QuestionListItem,
)
from backend.services import cache
from backend.services.ai_tutor_service import ai_tutor_service
from backend.services.gamification_service import calculate_xp

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("/filter", response_model=Page[QuestionListItem])
async def filter_questions(
    params: QuestionFilterParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Filtro dinâmico (estado, banca, matéria, ano, dificuldade) — read-through
    no Redis para não bater no Postgres a cada request repetida."""

    async def _load():
        items, total = await crud_question.filter_questions(db, params)
        page_data = Page[QuestionListItem](
            items=[QuestionListItem.model_validate(i) for i in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=(total + params.page_size - 1) // params.page_size if total else 0,
        )
        return page_data

    def _serialize(page: Page[QuestionListItem]):
        return page.model_dump(mode="json")

    def _deserialize(raw: dict) -> Page[QuestionListItem]:
        return Page[QuestionListItem].model_validate(raw)

    return await cache.read_through(
        key=params.cache_key(),
        ttl=settings.CACHE_TTL_FILTERS,
        loader=_load,
        serializer=_serialize,
        deserializer=_deserialize,
    )


@router.get("/{question_id}", response_model=QuestionDetail)
async def get_question_detail(question_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    cache_key = f"questions:detail:{question_id}"

    async def _load():
        question = await crud_question.get_detail(db, question_id)
        if question is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Questão não encontrada."
            )
        return QuestionDetail.model_validate(question)

    return await cache.read_through(
        key=cache_key,
        ttl=settings.CACHE_TTL_QUESTION_DETAIL,
        loader=_load,
        serializer=lambda q: q.model_dump(mode="json"),
        deserializer=lambda raw: QuestionDetail.model_validate(raw),
    )


@router.post("/{question_id}/answer", response_model=QuestionAnswerResult)
@limiter.limit(settings.RATE_LIMIT_ANSWERS)
async def submit_answer(
    request: Request,
    question_id: uuid.UUID,
    answer_in: QuestionAnswerSubmit,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Registra a resposta do usuário. Limitado a 10 envios / 15s por
    usuário/IP (SlowAPI) para mitigar automação/scraping de gabaritos."""
    question = await crud_question.get(db, question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Questão não encontrada.")

    answer = await crud_answer.submit_answer(
        db,
        user_id=user_id,
        question=question,
        selected_option=answer_in.selected_option,
        is_cebraspe_mode=answer_in.is_cebraspe_mode,
    )

    xp_earned = calculate_xp(
        is_correct=answer.is_correct,
        difficulty_level=question.difficulty_level,
        is_cebraspe_mode=answer_in.is_cebraspe_mode,
    )

    user = await crud_user.get(db, user_id)
    user = await crud_user.register_activity_and_grant_xp(db, user, xp_earned)

    await cache.delete_by_prefix("leaderboard:top:")

    return QuestionAnswerResult(
        question_id=question.id,
        selected_option=answer.selected_option,
        correct_option=question.correct_option,
        is_correct=answer.is_correct,
        xp_earned=xp_earned,
        current_streak=user.current_streak,
        total_xp=user.total_xp,
    )


@router.post("/{question_id}/explain-ai", response_model=AIExplanationResponse)
@limiter.limit("20/minute")
async def explain_with_ai(
    request: Request,
    question_id: uuid.UUID,
    explain_in: AIExplanationRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    question = await crud_question.get(db, question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Questão não encontrada.")

    explanation = await ai_tutor_service.explain(question, explain_in.user_selected_option)

    return AIExplanationResponse(
        question_id=question.id,
        explanation_markdown=explanation,
        generated_at=datetime.now(timezone.utc),
    )
