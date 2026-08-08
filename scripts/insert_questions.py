"""Executável standalone para inserir questões a partir de arquivos .json
locais direto no banco configurado em `backend/.env` (`DATABASE_URL`) —
inclusive o de produção, se apontado para lá. Roda fora do processo web,
sem limite de tempo de execução de função serverless, então é o caminho
recomendado para lotes grandes (a rota POST /questions/batch da API está
limitada a 200 itens por chamada, pensada para lotes pequenos via painel
admin ou automações leves).

Reaproveita a mesma lógica de deduplicação e resolução de taxonomia do
scraper (services/scraper_service.py) — o hash SHA256 de enunciado+
alternativas é a chave real de deduplicação, garantida por
`INSERT ... ON CONFLICT DO NOTHING` no banco.

Formato esperado do .json — uma lista de objetos, cada um seguindo o schema
RawQuestionPayload (backend/schemas/question.py):

    [
      {
        "content": "Enunciado da questão...",
        "options": {"A": "Alternativa A", "B": "Alternativa B"},
        "correct_option": "A",
        "board_name": "CEBRASPE",
        "subject_name": "Direito Constitucional",
        "organization": "TRF 3ª Região",
        "role": "Analista Judiciário",
        "year": 2024,
        "state_uf": "SP",
        "difficulty_level": "MEDIUM"
      }
    ]

`state_uf`, `role`, `source_url`, `difficulty_hint` e `difficulty_level` são
opcionais — sem `difficulty_level`, a dificuldade é classificada
automaticamente (mesma heurística do scraper).

Uso:
    cd meu-app-concursos
    .venv\\Scripts\\python.exe -m scripts.insert_questions questoes.json
    .venv\\Scripts\\python.exe -m scripts.insert_questions questoes1.json questoes2.json
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from backend.crud.crud_question import crud_question
from backend.database import dispose_engine, get_db_context
from backend.schemas.question import RawQuestionPayload
from backend.services import cache
from backend.services.cache import redis_client
from backend.services.scraper_service import (
    classify_difficulty,
    compute_content_hash,
    resolve_foreign_keys,
    sanitize_html,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("insert_questions")


def _load_payloads(path: Path) -> list[RawQuestionPayload]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{path}: o arquivo precisa conter uma lista JSON de questões.")

    payloads: list[RawQuestionPayload] = []
    for i, item in enumerate(raw):
        try:
            payloads.append(RawQuestionPayload(**item))
        except ValidationError as exc:
            logger.warning("%s: item %d inválido, pulando — %s", path.name, i, exc)
    return payloads


async def insert_all(payloads: list[RawQuestionPayload]) -> tuple[int, int, int]:
    """Retorna (inserido, duplicado, invalido)."""
    inserted = duplicates = invalid = 0
    seen_hashes: set[str] = set()
    rows: list[dict[str, Any]] = []

    async with get_db_context() as db:
        for payload in payloads:
            clean_content = sanitize_html(payload.content)
            clean_options = {k: sanitize_html(v) for k, v in payload.options.items()}
            content_hash = compute_content_hash(clean_content, clean_options)

            if content_hash in seen_hashes:
                duplicates += 1
                continue
            seen_hashes.add(content_hash)

            existing = await crud_question.get_by_content_hash(db, content_hash)
            if existing is not None:
                duplicates += 1
                continue

            fk_ids = await resolve_foreign_keys(db, payload)
            if fk_ids is None:
                invalid += 1
                logger.warning("Banca/matéria/órgão inválidos: %s...", clean_content[:60])
                continue

            rows.append(
                {
                    "content": clean_content,
                    "options": clean_options,
                    "correct_option": payload.correct_option,
                    "year": payload.year,
                    "difficulty_level": payload.difficulty_level or classify_difficulty(payload),
                    "content_hash": content_hash,
                    "source_url": payload.source_url,
                    **fk_ids,
                }
            )

        if rows:
            inserted = await crud_question.bulk_insert_questions(db, rows)
            duplicates += len(rows) - inserted

        if inserted > 0:
            await cache.delete_by_prefix("questions:filter:")
            # resolve_foreign_keys pode ter criado banca/matéria/órgão/estado
            # novos (get-or-create) — sem isso, /subjects, /boards e /states
            # continuam servindo a lista antiga do Redis por até 1h.
            await cache.delete("taxonomy:subjects", "taxonomy:boards", "taxonomy:states")

    return inserted, duplicates, invalid


async def main_async(paths: list[Path]) -> int:
    try:
        all_payloads: list[RawQuestionPayload] = []
        for path in paths:
            if not path.is_file():
                logger.error("Arquivo não encontrado: %s", path)
                return 1
            all_payloads.extend(_load_payloads(path))

        if not all_payloads:
            logger.error("Nenhuma questão válida encontrada nos arquivos informados.")
            return 1

        logger.info("Inserindo %d questão(ões) válida(s) do JSON...", len(all_payloads))
        inserted, duplicates, invalid = await insert_all(all_payloads)
        logger.info(
            "Resumo: recebidas=%d inserido=%d duplicadas=%d inválidas=%d",
            len(all_payloads), inserted, duplicates, invalid,
        )
        return 0
    finally:
        await dispose_engine()
        # Fecha a conexão do cliente Redis explicitamente — sem isso, o
        # finalizador dele roda durante o encerramento do interpretador,
        # depois do event loop já ter fechado (RuntimeError cosmético,
        # sem efeito no resultado, mas suja a saída do script).
        await redis_client.aclose()


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    paths = [Path(arg) for arg in sys.argv[1:]]
    return asyncio.run(main_async(paths))


if __name__ == "__main__":
    sys.exit(main())
