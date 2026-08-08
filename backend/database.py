"""Engine assíncrona do PostgreSQL — sempre em regime NullPool.

Este projeto roda em Vercel Functions (serverless): cada invocação é um
processo efêmero, então manter um `QueuePool` local não ajuda (ele morre
junto com a invocação) e MULTIPLICA conexões abertas no Postgres a cada cold
start, estourando o `max_connections` do banco ("too many connections").
Por isso o engine usa incondicionalmente:

  - `poolclass=NullPool`: nenhuma conexão fica ociosa entre invocações; cada
    request abre e fecha a sua. `DATABASE_URL` deve apontar para um pooler
    externo em modo transaction (PgBouncer do Neon/Supabase, RDS Proxy etc.),
    que absorve o fan-out de conexões de múltiplas invocações concorrentes.
  - `statement_cache_size=0` no asyncpg: poolers em modo transaction podem
    trocar a conexão física subjacente entre statements da mesma sessão
    lógica, o que quebra prepared statements cacheados pelo lado do cliente
    (`asyncpg.exceptions.DuplicatePreparedStatementError`).

Uma versão anterior alternava entre QueuePool/NullPool detectando o
ambiente (VERCEL=1 etc.), mas essa detecção se mostrou pouco confiável em
produção — nunca ativava o NullPool mesmo com o sinal presente. Como o
único alvo de deploy real é serverless, e NullPool funciona perfeitamente
bem (só um pouco menos eficiente) também em um container/VM local, manter
um único regime sempre ativo elimina essa classe inteira de bug.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

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


engine: AsyncEngine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.DB_ECHO,
    future=True,
    poolclass=NullPool,
    connect_args={"statement_cache_size": 0},
)

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
