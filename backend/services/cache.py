"""Camada de cache Redis (read-through) para proteger o PostgreSQL de consultas
pesadas repetidas — filtros de questões, detalhe de questões populares e leaderboard.
"""
import json
from typing import Any, Awaitable, Callable, TypeVar

import redis.asyncio as redis
from pydantic import BaseModel

from backend.core.config import settings

T = TypeVar("T")

redis_client: redis.Redis = redis.from_url(
    str(settings.REDIS_URL),
    encoding="utf-8",
    decode_responses=True,
    max_connections=50,
)


async def ping() -> bool:
    try:
        return await redis_client.ping()
    except redis.RedisError:
        return False


def _dumps(value: Any) -> str:
    if isinstance(value, BaseModel):
        return value.model_dump_json()
    return json.dumps(value, default=str)


async def get_json(key: str) -> Any | None:
    raw = await redis_client.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def set_json(key: str, value: Any, ttl: int) -> None:
    await redis_client.set(key, _dumps(value), ex=ttl)


async def delete(*keys: str) -> None:
    if keys:
        await redis_client.delete(*keys)


async def delete_by_prefix(prefix: str) -> None:
    """Invalida todas as chaves sob um prefixo (ex.: `questions:filter:*` após
    uma nova questão ser inserida pelo scraper)."""
    async for key in redis_client.scan_iter(match=f"{prefix}*"):
        await redis_client.delete(key)


async def read_through(
    key: str,
    ttl: int,
    loader: Callable[[], Awaitable[T]],
    serializer: Callable[[T], Any] | None = None,
    deserializer: Callable[[Any], T] | None = None,
) -> T:
    """Padrão read-through genérico: tenta o Redis primeiro; em cache miss,
    executa `loader` (a consulta ao Postgres), grava o resultado no Redis com
    TTL e só então retorna. Erros do Redis nunca derrubam a request — apenas
    fazem o fluxo cair de volta para o banco (fail-open)."""
    try:
        cached = await get_json(key)
    except redis.RedisError:
        cached = None

    if cached is not None:
        return deserializer(cached) if deserializer else cached

    value = await loader()

    try:
        payload = serializer(value) if serializer else value
        await set_json(key, payload, ttl)
    except redis.RedisError:
        pass  # cache indisponível não deve quebrar a resposta ao usuário

    return value
