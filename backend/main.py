"""Ponto de entrada da aplicação FastAPI."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.core.config import settings
from backend.core.rate_limit import limiter
from backend.database import dispose_engine
from backend.routers import admin, auth, comments, leaderboard, questions, users

logging.basicConfig(level=logging.INFO if not settings.DEBUG else logging.DEBUG)
logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando %s [%s]", settings.APP_NAME, settings.ENVIRONMENT)
    yield
    logger.info("Encerrando aplicação — liberando pool de conexões.")
    await dispose_engine()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url=None,
)

# --- Rate Limiting (SlowAPI + Redis) ---
# Sem SlowAPIMiddleware de propósito: seu dispatch() lê
# request.state.view_rate_limit incondicionalmente ao montar a resposta,
# o que quebra (AttributeError) quando swallow_errors=True pula a checagem
# de limite por Redis indisponível. Os decorators @limiter.limit(...) nas
# rotas sensíveis (login, resposta, IA) funcionam via Depends do FastAPI,
# independente deste middleware — só o limite padrão global implícito
# (default_limits, sem decorator explícito) deixa de ser aplicado.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORS ---
# `allow_origins` cobre domínios fixos (dev local, domínio de produção
# customizado); `allow_origin_regex` casa automaticamente qualquer preview ou
# produção da Vercel (*.vercel.app) sem precisar reconfigurar a cada deploy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,  # necessário para o cookie HttpOnly de auth
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# --- Cabeçalhos de segurança adicionais ---
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Normaliza erros de validação do Pydantic sem vazar detalhes internos."""
    return JSONResponse(
        status_code=422,
        content={"detail": "Dados de entrada inválidos.", "errors": exc.errors()},
    )


# --- Routers ---
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(questions.router, prefix=settings.API_V1_PREFIX)
app.include_router(comments.router, prefix=settings.API_V1_PREFIX)
app.include_router(leaderboard.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
