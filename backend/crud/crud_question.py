import uuid
from typing import Any, Sequence

from sqlalchemy import exists, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.crud.base import CRUDBase
from backend.models.answer import UserAnswer
from backend.models.question import Question
from backend.schemas.question import QuestionFilterParams


class CRUDQuestion(CRUDBase[Question]):
    _EAGER_OPTS = (
        joinedload(Question.board),
        joinedload(Question.subject),
        joinedload(Question.exam),
        joinedload(Question.state),
    )

    async def get_detail(self, db: AsyncSession, question_id: uuid.UUID) -> Question | None:
        stmt = select(Question).where(Question.id == question_id).options(*self._EAGER_OPTS)
        result = await db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_by_content_hash(self, db: AsyncSession, content_hash: str) -> Question | None:
        result = await db.execute(
            select(Question).where(Question.content_hash == content_hash)
        )
        return result.scalar_one_or_none()

    def _apply_filters(
        self, stmt, params: QuestionFilterParams, user_id: uuid.UUID | None = None
    ):
        if params.state_id:
            stmt = stmt.where(Question.state_id == params.state_id)
        if params.board_id:
            stmt = stmt.where(Question.board_id == params.board_id)
        if params.subject_id:
            stmt = stmt.where(Question.subject_id == params.subject_id)
        if params.exam_id:
            stmt = stmt.where(Question.exam_id == params.exam_id)
        if params.year:
            stmt = stmt.where(Question.year == params.year)
        if params.difficulty_level:
            stmt = stmt.where(Question.difficulty_level == params.difficulty_level)
        if user_id is not None:
            # Usuário autenticado: nunca mostra de novo uma questão que ele já
            # respondeu — o histórico completo (certas/erradas) fica
            # disponível separadamente em GET /users/me/answers.
            stmt = stmt.where(
                ~exists().where(
                    UserAnswer.question_id == Question.id,
                    UserAnswer.user_id == user_id,
                )
            )
        return stmt

    async def filter_questions(
        self, db: AsyncSession, params: QuestionFilterParams, user_id: uuid.UUID | None = None
    ) -> tuple[Sequence[Question], int]:
        """Consulta filtrada e paginada. Usa o índice composto
        ix_questions_filter_composite para evitar full scan sob os filtros
        mais comuns. Só é chamada em cache miss (ver services/cache.py)."""
        base_stmt = self._apply_filters(select(Question), params, user_id)

        count_stmt = self._apply_filters(select(func.count(Question.id)), params, user_id)
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = (
            base_stmt.options(*self._EAGER_OPTS)
            .order_by(Question.created_at.desc())
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
        )
        result = await db.execute(stmt)
        items = result.unique().scalars().all()
        return items, total

    async def bulk_insert_questions(
        self, db: AsyncSession, rows: list[dict[str, Any]]
    ) -> int:
        """Insere um lote de questões em uma única viagem ao banco, ignorando
        duplicidades por `content_hash` (ON CONFLICT DO NOTHING). Usado pelo
        pipeline de scraping para evitar um commit por questão."""
        if not rows:
            return 0
        stmt = pg_insert(Question).values(rows).on_conflict_do_nothing(
            index_elements=["content_hash"]
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount or 0


crud_question = CRUDQuestion(Question)
