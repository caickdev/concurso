"""Engine assíncrona do PostgreSQL — dois regimes de pooling conforme o processo.

1) Processo long-lived (container/VM/worker dedicado): pool local da aplicação
   (`QueuePool`), com pool_size=20 / max_overflow=10 (até 30 conexões
   simultâneas por worker antes de enfileirar), pool_recycle=3600 (evita
   "server closed the connection unexpectedly" em conexões ociosas atrás de
   load balancers/NAT) e pool_pre_ping=True (evita erros de conexões mortas
   devolvidas pelo pool).

2) Serverless (Vercel Functions e similares): cada invocação é um processo
   efêmero — manter um QueuePool local não ajuda (ele morre com a invocação)
   e MULTIPLICA conexões abertas no Postgres a cada cold start, estourando o
   `max_connections` do banco ("too many connections"). Nesse regime:
     - `poolclass=NullPool`: nenhuma conexão fica ociosa entre invocações;
       cada request abre e fecha a sua.
     - `DATABASE_URL` deve apontar para um pooler externo em modo transaction
       (PgBouncer do Neon/Supabase, RDS Proxy etc.), que absorve o fan-out de
       conexões de múltiplas invocações concorrentes.
     - `statement_cache_size=0` no asyncpg: poolers em modo transaction podem
       trocar a conexão física subjacente entre statements da mesma sessão
       lógica, o que quebra prepared statements cacheados pelo asyncpg
       ("prepared statement ... does not exist").

O regime 2 é ativado automaticamente quando `VERCEL=1` (variável que a
própria Vercel injeta em toda função) ou explicitamente via DB_FORCE_NULLPOOL.
"""
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from backend.core.config import settings


class Base(DeclarativeBase):
    """Base declarativa compartilhada por todos os modelos ORM."""
    pass


# Checa múltiplos sinais de ambiente serverless em vez de depender de um só:
# VERCEL / VERCEL_ENV são injetadas automaticamente pela Vercel, mas exigem
# "Automatically expose System Environment Variables" habilitado no projeto
# para chegarem até a função Python — não confiável sozinho. Combina com
# AWS_LAMBDA_FUNCTION_NAME (a Vercel roda funções Python sobre Lambda) e o
# flag manual DB_FORCE_NULLPOOL como garantias adicionais.
IS_SERVERLESS = bool(
    os.environ.get("VERCEL")
    or os.environ.get("VERCEL_ENV")
    or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
    or settings.DB_FORCE_NULLPOOL
)

_engine_kwargs: dict[str, Any] = {
    "echo": settings.DB_ECHO,
    "future": True,
}

if IS_SERVERLESS:
    _engine_kwargs["poolclass"] = NullPool
    _engine_kwargs["connect_args"] = {"statement_cache_size": 0}
else:
    _engine_kwargs.update(
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_pre_ping=True,
    )

engine: AsyncEngine = create_async_engine(str(settings.DATABASE_URL), **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependência FastAPI: uma sessão por request, sempre fechada ao final."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager para uso fora do ciclo de request (ex.: scraper/jobs)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def dispose_engine() -> None:
    """Fecha o pool de conexões no shutdown da aplicação."""
    await engine.dispose()
