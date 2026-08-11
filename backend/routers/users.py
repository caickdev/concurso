import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import get_current_user_id
from backend.crud.crud_answer import crud_answer
from backend.crud.crud_notebook import crud_notebook
from backend.crud.crud_user import crud_user
from backend.database import get_db
from backend.schemas.answer import AnsweredQuestionFilterParams, AnsweredQuestionRead
from backend.schemas.common import Page
from backend.schemas.notebook import NotebookItemCreate, NotebookItemRead, NotebookItemUpdate
from backend.schemas.question import QuestionListItem
from backend.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me", response_model=UserRead)
async def update_me(
    update_in: UserUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user = await crud_user.get(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")

    if update_in.full_name is not None:
        user.full_name = update_in.full_name
    if update_in.daily_goal is not None:
        user.daily_goal = update_in.daily_goal

    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# --- Histórico de respostas (Corretas/Erradas) ---

@router.get("/me/answers", response_model=Page[AnsweredQuestionRead])
async def list_answered_questions(
    params: AnsweredQuestionFilterParams = Depends(),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Todas as questões que o usuário já respondeu, mais recentes primeiro —
    já que /questions/filter nunca mais devolve uma questão respondida, este
    é o único lugar para revê-la depois, com o gabarito exposto e filtrável
    por acerto/erro (params.is_correct)."""
    answers, total = await crud_answer.filter_by_user(db, user_id, params)
    items = [
        AnsweredQuestionRead(
            id=answer.id,
            question=QuestionListItem.model_validate(answer.question),
            selected_option=answer.selected_option,
            correct_option=answer.question.correct_option,
            is_correct=answer.is_correct,
            answered_at=answer.created_at,
        )
        for answer in answers
    ]
    return Page[AnsweredQuestionRead](
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=(total + params.page_size - 1) // params.page_size if total else 0,
    )


# --- Caderno de Erros ---

@router.get("/me/notebook", response_model=list[NotebookItemRead])
async def list_notebook(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await crud_notebook.list_by_user(db, user_id)


@router.post("/me/notebook", response_model=NotebookItemRead, status_code=status.HTTP_201_CREATED)
async def add_to_notebook(
    item_in: NotebookItemCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await crud_notebook.add_item(
        db,
        user_id=user_id,
        question_id=item_in.question_id,
        personal_notes=item_in.personal_notes,
    )


@router.patch("/me/notebook/{item_id}", response_model=NotebookItemRead)
async def update_notebook_item(
    item_id: uuid.UUID,
    update_in: NotebookItemUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    item = await crud_notebook.get_for_user(db, item_id=item_id, user_id=user_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado.")

    if update_in.personal_notes is not None:
        item.personal_notes = update_in.personal_notes
    if update_in.status is not None:
        item.status = update_in.status

    db.add(item)
    await db.commit()
    return await crud_notebook.get_for_user(db, item_id=item.id, user_id=user_id)


@router.delete("/me/notebook/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_notebook(
    item_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    item = await crud_notebook.get_for_user(db, item_id=item_id, user_id=user_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado.")
    await db.delete(item)
    await db.commit()
