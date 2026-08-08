from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.crud.crud_user import crud_user
from backend.database import get_db
from backend.schemas.user import LeaderboardEntry
from backend.services import cache

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("", response_model=list[LeaderboardEntry])
async def get_leaderboard(limit: int = 50, db: AsyncSession = Depends(get_db)):
    cache_key = f"leaderboard:top:{limit}"

    async def _load() -> list[LeaderboardEntry]:
        users = await crud_user.get_leaderboard(db, limit=limit)
        return [
            LeaderboardEntry(
                rank=idx + 1,
                user_id=u.id,
                full_name=u.full_name,
                total_xp=u.total_xp,
                current_streak=u.current_streak,
            )
            for idx, u in enumerate(users)
        ]

    return await cache.read_through(
        key=cache_key,
        ttl=settings.CACHE_TTL_LEADERBOARD,
        loader=_load,
        serializer=lambda entries: [e.model_dump(mode="json") for e in entries],
        deserializer=lambda raw: [LeaderboardEntry.model_validate(e) for e in raw],
    )
