from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.rate_limit import limiter
from backend.core.security import (
    clear_auth_cookie,
    create_access_token,
    get_current_user_id,
    set_auth_cookie,
    verify_password,
)
from backend.crud.crud_user import crud_user
from backend.database import get_db
from backend.schemas.user import TokenResponse, UserCreate, UserLogin, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await crud_user.get_by_email(db, user_in.email.lower())
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado."
        )
    user = await crud_user.create_user(db, user_in)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login(
    request: Request,
    credentials: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user = await crud_user.get_by_email(db, credentials.email.lower())
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos."
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Conta desativada."
        )

    token = create_access_token(user.id)
    set_auth_cookie(response, token)
    return TokenResponse()


@router.post("/logout", response_model=TokenResponse)
async def logout(response: Response):
    clear_auth_cookie(response)
    return TokenResponse(message="Sessão encerrada.")


@router.get("/me", response_model=UserRead)
async def read_current_user(
    user_id=Depends(get_current_user_id), db: AsyncSession = Depends(get_db)
):
    user = await crud_user.get(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
    return user
