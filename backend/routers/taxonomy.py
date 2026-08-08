"""Listas de apoio para os filtros (matéria, banca, estado) — tabelas
pequenas, sem paginação, com cache de leitura mais longo (mudam raramente)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends

from backend.database import get_db
from backend.models.taxonomy import Board, State, Subject
from backend.schemas.question import BoardRead, StateRead, SubjectRead
from backend.services import cache

router = APIRouter(tags=["taxonomy"])

_TTL = 3600  # 1h — taxonomia muda raramente


@router.get("/subjects", response_model=list[SubjectRead])
async def list_subjects(db: AsyncSession = Depends(get_db)):
    async def _load():
        result = await db.execute(select(Subject).order_by(Subject.name))
        return [SubjectRead.model_validate(s).model_dump(mode="json") for s in result.scalars().all()]

    return await cache.read_through(
        key="taxonomy:subjects", ttl=_TTL, loader=_load,
        deserializer=lambda raw: [SubjectRead.model_validate(s) for s in raw],
    )


@router.get("/boards", response_model=list[BoardRead])
async def list_boards(db: AsyncSession = Depends(get_db)):
    async def _load():
        result = await db.execute(select(Board).order_by(Board.name))
        return [BoardRead.model_validate(b).model_dump(mode="json") for b in result.scalars().all()]

    return await cache.read_through(
        key="taxonomy:boards", ttl=_TTL, loader=_load,
        deserializer=lambda raw: [BoardRead.model_validate(b) for b in raw],
    )


@router.get("/states", response_model=list[StateRead])
async def list_states(db: AsyncSession = Depends(get_db)):
    async def _load():
        result = await db.execute(select(State).order_by(State.name))
        return [StateRead.model_validate(s).model_dump(mode="json") for s in result.scalars().all()]

    return await cache.read_through(
        key="taxonomy:states", ttl=_TTL, loader=_load,
        deserializer=lambda raw: [StateRead.model_validate(s) for s in raw],
    )
