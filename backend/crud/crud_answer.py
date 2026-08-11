import uuid
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.crud.base import CRUDBase
from backend.models.answer import UserAnswer
from backend.models.question import Question
from backend.schemas.answer import AnsweredQuestionFilterParams


class CRUDAnswer(CRUDBase[UserAnswer]):
    _EAGER_OPTS = (
        joinedload(UserAnswer.question).joinedload(Question.board),
        joinedload(UserAnswer.question).joinedload(Question.subject),
        joinedload(UserAnswer.question).joinedload(Question.exam),
        joinedload(UserAnswer.question).joinedload(Question.state),
    )

    async def submit_answer(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        question: Question,
        selected_option: str,
        is_cebraspe_mode: bool,
    ) -> UserAnswer:
        is_correct = selected_option == question.correct_option
        answer = UserAnswer(
            user_id=user_id,
            question_id=question.id,
            selected_option=selected_option,
            is_correct=is_correct,
            is_cebraspe_mode=is_cebraspe_mode,
        )
        db.add(answer)
        await db.commit()
        await db.refresh(answer)
        return answer

    async def count_by_user(self, db: AsyncSession, user_id: uuid.UUID) -> int:
        result = await db.execute(
            select(func.count(UserAnswer.id)).where(UserAnswer.user_id == user_id)
        )
        return result.scalar_one()

    def _apply_answer_filters(
        self, stmt, user_id: uuid.UUID, params: AnsweredQuestionFilterParams
    ):
        stmt = stmt.join(Question, UserAnswer.question_id == Question.id).where(
            UserAnswer.user_id == user_id
        )
        if params.is_correct is not None:
            stmt = stmt.where(UserAnswer.is_correct == params.is_correct)
        if params.subject_id:
            stmt = stmt.where(Question.subject_id == params.subject_id)
        if params.board_id:
            stmt = stmt.where(Question.board_id == params.board_id)
        if params.year:
            stmt = stmt.where(Question.year == params.year)
        if params.difficulty_level:
            stmt = stmt.where(Question.difficulty_level == params.difficulty_level)
        return stmt

    async def filter_by_user(
        self, db: AsyncSession, user_id: uuid.UUID, params: AnsweredQuestionFilterParams
    ) -> tuple[Sequence[UserAnswer], int]:
        """Histórico de questões respondidas pelo usuário, mais recente
        primeiro — usado pela aba "Respondidas" (Corretas/Erradas) do
        dashboard, que fica disponível independentemente da paginação da
        listagem principal de questões não respondidas."""
        count_stmt = self._apply_answer_filters(select(func.count(UserAnswer.id)), user_id, params)
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = self._apply_answer_filters(select(UserAnswer), user_id, params)
        stmt = (
            stmt.options(*self._EAGER_OPTS)
            .order_by(UserAnswer.created_at.desc())
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
        )
        result = await db.execute(stmt)
        items = result.unique().scalars().all()
        return items, total


crud_answer = CRUDAnswer(UserAnswer)
