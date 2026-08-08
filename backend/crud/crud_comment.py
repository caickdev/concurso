import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.crud.base import CRUDBase
from backend.models.comment import AUTO_HIDE_REPORT_THRESHOLD, CommentReport, StudentComment


class CRUDComment(CRUDBase[StudentComment]):
    async def list_visible_by_question(
        self, db: AsyncSession, question_id: uuid.UUID
    ) -> list[StudentComment]:
        stmt = (
            select(StudentComment)
            .where(
                StudentComment.question_id == question_id,
                StudentComment.is_approved.is_(True),
                StudentComment.is_hidden.is_(False),
            )
            .options(joinedload(StudentComment.user))
            .order_by(StudentComment.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.unique().scalars().all())

    async def create_comment(
        self, db: AsyncSession, *, user_id: uuid.UUID, question_id: uuid.UUID, content: str
    ) -> StudentComment:
        comment = StudentComment(user_id=user_id, question_id=question_id, content=content)
        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        return comment

    async def report_comment(
        self, db: AsyncSession, *, comment_id: uuid.UUID, user_id: uuid.UUID, reason: str
    ) -> StudentComment | None:
        comment = await self.get(db, comment_id)
        if comment is None:
            return None

        report = CommentReport(comment_id=comment_id, user_id=user_id, reason=reason)
        db.add(report)
        try:
            await db.flush()
        except IntegrityError:
            # Usuário já denunciou este comentário anteriormente — idempotente.
            await db.rollback()
            return comment

        comment.report_count += 1
        if comment.report_count >= AUTO_HIDE_REPORT_THRESHOLD:
            comment.is_hidden = True

        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        return comment


crud_comment = CRUDComment(StudentComment)
