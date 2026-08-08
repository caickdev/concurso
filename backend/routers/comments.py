import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import get_current_user_id
from backend.crud.crud_comment import crud_comment
from backend.database import get_db
from backend.schemas.comment import CommentCreate, CommentRead, CommentReportCreate
from backend.services.moderation_service import enforce_no_profanity

router = APIRouter(prefix="/questions/{question_id}/comments", tags=["comments"])


def _to_comment_read(comment) -> CommentRead:
    return CommentRead(
        id=comment.id,
        question_id=comment.question_id,
        user_id=comment.user_id,
        author_name=comment.user.full_name,
        content=comment.content,
        created_at=comment.created_at,
    )


@router.get("", response_model=list[CommentRead])
async def list_comments(question_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    comments = await crud_comment.list_visible_by_question(db, question_id)
    return [_to_comment_read(c) for c in comments]


@router.post("", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
async def create_comment(
    question_id: uuid.UUID,
    comment_in: CommentCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    enforce_no_profanity(comment_in.content)
    comment = await crud_comment.create_comment(
        db, user_id=user_id, question_id=question_id, content=comment_in.content
    )
    await db.refresh(comment, attribute_names=["user"])
    return _to_comment_read(comment)


@router.post("/{comment_id}/report", status_code=status.HTTP_204_NO_CONTENT)
async def report_comment(
    question_id: uuid.UUID,
    comment_id: uuid.UUID,
    report_in: CommentReportCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    comment = await crud_comment.report_comment(
        db, comment_id=comment_id, user_id=user_id, reason=report_in.reason
    )
    if comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comentário não encontrado.")
