import uuid
from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import hash_password
from backend.crud.base import CRUDBase
from backend.models.user import User
from backend.schemas.user import UserCreate


class CRUDUser(CRUDBase[User]):
    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create_user(self, db: AsyncSession, user_in: UserCreate) -> User:
        user = User(
            email=user_in.email.lower(),
            password_hash=hash_password(user_in.password),
            full_name=user_in.full_name,
        )
        db.add(user)
        try:
            await db.commit()
        except IntegrityError as exc:
            # Cobre a corrida entre a checagem prévia de e-mail (get_by_email)
            # e o commit — duas requests concorrentes com o mesmo e-mail.
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado."
            ) from exc
        await db.refresh(user)
        return user

    async def register_activity_and_grant_xp(
        self, db: AsyncSession, user: User, xp_earned: int
    ) -> User:
        """Atualiza streak diário e XP total de forma atômica após uma resposta.

        Regras de streak:
        - Mesma data de `last_active_date`: nenhuma alteração no streak.
        - Data == last_active_date + 1 dia: incrementa o streak.
        - Qualquer outro caso (gap ou primeiro acesso): reinicia o streak em 1.
        """
        today = date.today()
        if user.last_active_date == today:
            pass  # já contabilizado hoje
        elif user.last_active_date == today - timedelta(days=1):
            user.current_streak += 1
        else:
            user.current_streak = 1
        user.longest_streak = max(user.longest_streak, user.current_streak)
        user.last_active_date = today
        user.total_xp += xp_earned

        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def get_leaderboard(self, db: AsyncSession, limit: int = 50) -> list[User]:
        result = await db.execute(
            select(User).order_by(User.total_xp.desc()).limit(limit)
        )
        return list(result.scalars().all())


crud_user = CRUDUser(User)
