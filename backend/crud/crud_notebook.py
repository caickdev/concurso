import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.crud.base import CRUDBase
from backend.models.notebook import NotebookItem
from backend.models.question import Question


class CRUDNotebook(CRUDBase[NotebookItem]):
    _QUESTION_EAGER_OPTS = (
        joinedload(NotebookItem.question).joinedload(Question.board),
        joinedload(NotebookItem.question).joinedload(Question.subject),
        joinedload(NotebookItem.question).joinedload(Question.exam),
        joinedload(NotebookItem.question).joinedload(Question.state),
    )

    async def list_by_user(self, db: AsyncSession, user_id: uuid.UUID) -> list[NotebookItem]:
        stmt = (
            select(NotebookItem)
            .where(NotebookItem.user_id == user_id)
            .options(*self._QUESTION_EAGER_OPTS)
            .order_by(NotebookItem.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.unique().scalars().all())

    async def get_for_user(
        self, db: AsyncSession, *, item_id: uuid.UUID, user_id: uuid.UUID
    ) -> NotebookItem | None:
        stmt = (
            select(NotebookItem)
            .where(NotebookItem.id == item_id, NotebookItem.user_id == user_id)
            .options(*self._QUESTION_EAGER_OPTS)
        )
        result = await db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_by_user_and_question(
        self, db: AsyncSession, *, user_id: uuid.UUID, question_id: uuid.UUID
    ) -> NotebookItem | None:
        stmt = (
            select(NotebookItem)
            .where(NotebookItem.user_id == user_id, NotebookItem.question_id == question_id)
            .options(*self._QUESTION_EAGER_OPTS)
        )
        result = await db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def add_item(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        question_id: uuid.UUID,
        personal_notes: str | None,
    ) -> NotebookItem:
        """Cria o item ou, se a questão já estiver no caderno do usuário
        (violação da unique constraint), retorna o item existente de forma
        idempotente em vez de propagar um IntegrityError."""
        item = NotebookItem(
            user_id=user_id, question_id=question_id, personal_notes=personal_notes
        )
        db.add(item)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            existing = await self.get_by_user_and_question(
                db, user_id=user_id, question_id=question_id
            )
            if existing is not None:
                return existing
            raise
        return await self.get_for_user(db, item_id=item.id, user_id=user_id)


crud_notebook = CRUDNotebook(NotebookItem)
