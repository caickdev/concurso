import logging

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
from backend.crud import crud_password_reset
from backend.crud.crud_user import crud_user
from backend.database import get_db
from backend.schemas.user import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserRead,
)
from backend.services.email_service import build_password_reset_email, send_email

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


async def _send_reset_email(email: str, raw_token: str) -> None:
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
    if settings.DEBUG:
        # Só em desenvolvimento: permite testar o fluxo completo sem precisar
        # de RESEND_API_KEY configurada. Nunca loga em produção (DEBUG=false).
        logging.getLogger("auth").info("[DEBUG] Link de redefinição: %s", reset_url)
    await send_email(
        to=email,
        subject="Redefinição de senha — Plataforma de Questões para Concursos",
        html=build_password_reset_email(reset_url=reset_url),
    )


@router.post("/forgot-password", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Sempre responde com sucesso genérico, exista ou não o e-mail — evita
    que a rota seja usada para descobrir quais e-mails estão cadastrados.

    O envio do e-mail é aguardado aqui mesmo (não via BackgroundTasks):
    em runtime serverless (Vercel Functions), a função pode ser congelada
    assim que a resposta HTTP é enviada, sem garantir que uma tarefa em
    segundo plano agendada para depois realmente chegue a rodar."""
    user = await crud_user.get_by_email(db, payload.email.lower())
    if user is not None and user.is_active:
        raw_token = await crud_password_reset.create_reset_token(db, user)
        await _send_reset_email(user.email, raw_token)

    return TokenResponse(
        message="Se o e-mail estiver cadastrado, você receberá um link de redefinição em instantes."
    )


@router.post("/reset-password", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    entry = await crud_password_reset.get_valid_token(db, payload.token)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link de redefinição inválido ou expirado. Solicite um novo.",
        )

    user = await crud_user.get(db, entry.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Link de redefinição inválido."
        )

    await crud_password_reset.consume_token_and_reset_password(
        db, entry, user, payload.new_password
    )
    return TokenResponse(message="Senha redefinida com sucesso. Faça login com a nova senha.")
