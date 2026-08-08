"""Dependências FastAPI que combinam autenticação (core/security.py) com
acesso ao banco — vivem à parte para evitar import circular entre
core/security.py e crud/crud_user.py (crud_user já importa de security)."""
import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import get_current_user_id
from backend.crud.crud_user import crud_user
from backend.database import get_db


async def require_admin(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    """Garante que o usuário autenticado é administrador. Usa a mesma sessão
    de banco da rota (via Depends) para não abrir uma conexão extra."""
    user = await crud_user.get(db, user_id)
    if user is None or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a administradores."
        )
    return user_id
