import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.crud.base import CRUDBase
from backend.models.answer import UserAnswer
from backend.models.question import Question


class CRUDAnswer(CRUDBase[UserAnswer]):
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


crud_answer = CRUDAnswer(UserAnswer)
