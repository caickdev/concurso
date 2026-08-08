"""Configuração central do SlowAPI (rate limiting por IP/usuário, backend Redis)."""
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from backend.core.config import settings


def user_or_ip_key(request: Request) -> str:
    """Usa o user_id autenticado (via cookie) como chave quando disponível,
    caindo para o IP remoto para usuários anônimos. Isto evita que um único
    usuário autenticado contorne o limite trocando de IP/proxy."""
    token = request.cookies.get(settings.COOKIE_NAME)
    if token:
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            return f"user:{payload['sub']}"
        except (JWTError, KeyError):
            pass
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=user_or_ip_key,
    storage_uri=settings.RATE_LIMIT_STORAGE_URI or str(settings.REDIS_URL),
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    headers_enabled=True,
    swallow_errors=False,
)
