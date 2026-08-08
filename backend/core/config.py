"""Configuração central da aplicação via variáveis de ambiente (Pydantic Settings)."""
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

# Caminho absoluto para backend/.env — resolvido a partir deste arquivo, não
# do cwd do processo, para que `uvicorn backend.main:app` funcione igual seja
# invocado de dentro de backend/ ou da raiz do projeto (meu-app-concursos/).
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    APP_NAME: str = "Plataforma de Questões para Concursos"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # --- Banco de Dados ---
    # Em ambientes serverless (Vercel), aponte para a connection string com
    # PgBouncer do provedor (ex.: porta 6543 / host "-pooler" no Neon,
    # "Transaction" pooler no Supabase) — ver DB_FORCE_NULLPOOL abaixo.
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/concursos"
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 3600
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False
    # Força NullPool + desativa cache de prepared statements do asyncpg,
    # necessário atrás de um pooler externo (PgBouncer) em modo transaction.
    # Detectado automaticamente quando a variável VERCEL=1 está presente
    # (injetada pela própria Vercel em toda função); este flag permite
    # forçar o mesmo comportamento em outros ambientes serverless.
    DB_FORCE_NULLPOOL: bool = False

    # --- Redis / Cache ---
    REDIS_URL: RedisDsn = Field(default="redis://localhost:6379/0")
    CACHE_TTL_FILTERS: int = 300  # 5 min - listagens filtradas
    CACHE_TTL_QUESTION_DETAIL: int = 900  # 15 min - detalhe de questão
    CACHE_TTL_LEADERBOARD: int = 60  # 1 min - ranking muda rápido
    # Backend de armazenamento do SlowAPI. Por padrão usa o mesmo Redis (única
    # opção viável com múltiplos workers/instâncias). Em dev local sem Redis
    # disponível, defina RATE_LIMIT_STORAGE_URI=memory:// — válido apenas para
    # um único processo, nunca em produção com mais de um worker.
    RATE_LIMIT_STORAGE_URI: str | None = None

    # --- Segurança / JWT ---
    JWT_SECRET_KEY: str = Field(..., description="Chave secreta para assinatura do JWT")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    COOKIE_NAME: str = "access_token"
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "strict"
    COOKIE_DOMAIN: str | None = None

    # --- Redefinição de senha ---
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    # URL do frontend usada para montar o link enviado por e-mail
    # (ex.: https://concurso-mphb.vercel.app). Sem barra no final.
    FRONTEND_URL: str = "http://localhost:5173"

    # --- E-mail transacional (Resend) ---
    RESEND_API_KEY: str = Field(default="", description="Chave da API do Resend para envio de e-mails")
    EMAIL_FROM: str = "Plataforma de Concursos <onboarding@resend.dev>"

    # --- CORS ---
    # Armazenado como string bruta "a,b,c" — se declarado List[str] direto,
    # pydantic-settings tenta json.loads() no valor da env var antes de
    # qualquer validator rodar, e quebra porque o formato aqui não é JSON.
    # Use a property `cors_origins` (lista) no restante do código.
    CORS_ORIGINS: str = "http://localhost:5173"
    # Casa qualquer preview/produção da Vercel (ex.: meu-app-git-abc123.vercel.app)
    # sem precisar atualizar CORS_ORIGINS a cada deploy. Deixe None para desativar.
    CORS_ORIGIN_REGEX: str | None = r"https://.*\.vercel\.app$"

    # --- Rate Limiting ---
    RATE_LIMIT_ANSWERS: str = "10/15seconds"
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_LOGIN: str = "5/minute"

    # --- Tutor IA ---
    AI_PROVIDER_API_KEY: str = Field(default="", description="Chave da API do provedor LLM")
    AI_MODEL_NAME: str = "claude-sonnet-5"
    AI_REQUEST_TIMEOUT: int = 30

    # --- Scraper ---
    SCRAPER_BATCH_SIZE: int = 200
    SCRAPER_CONCURRENCY: int = 5
    SCRAPER_USER_AGENT: str = "ConcursosBot/1.0 (+https://example.com/bot)"
    # Fontes usadas pelo endpoint /admin/scraper/run (disparado pelo Vercel Cron),
    # mesma string "a,b,c" por env var — ver `scraper_source_urls` abaixo.
    # scripts/run_scraper.py, executado fora do processo web, aceita URLs via CLI
    # e não depende desta variável.
    SCRAPER_SOURCE_URLS: str = ""

    # --- Cron (Vercel Cron Jobs) ---
    # A Vercel injeta automaticamente `Authorization: Bearer <CRON_SECRET>` nas
    # chamadas agendadas quando esta variável está definida no projeto — o
    # endpoint só precisa validar o header recebido contra este valor.
    CRON_SECRET: str = ""

    @staticmethod
    def _split_comma_separated(raw: str) -> List[str]:
        return [item.strip() for item in raw.split(",") if item.strip()]

    @property
    def cors_origins(self) -> List[str]:
        return self._split_comma_separated(self.CORS_ORIGINS)

    @property
    def scraper_source_urls(self) -> List[str]:
        return self._split_comma_separated(self.SCRAPER_SOURCE_URLS)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
