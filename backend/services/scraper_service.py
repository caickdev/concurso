"""Pipeline assíncrono de coleta e povoamento (ETL) de questões públicas.

Fluxo: extract() -> clean/transform() -> hash/dedupe() -> bulk load().

Notas de design:
- `httpx.AsyncClient` com concorrência limitada por `asyncio.Semaphore` evita
  martelar as fontes (boa cidadania de scraping) e limita uso de memória.
- Todo o parsing HTML é isolado em `_parse_question_page`, o único ponto que
  precisa mudar caso a estrutura de uma fonte específica mude.
- Nenhum `commit` por questão: os registros validados são acumulados em um
  buffer e persistidos via `crud_question.bulk_insert_questions`, que usa
  `INSERT ... ON CONFLICT DO NOTHING` em uma única viagem ao banco por lote.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

import bleach
import httpx
from bs4 import BeautifulSoup
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.crud.crud_question import crud_question
from backend.database import get_db_context
from backend.models.question import DifficultyLevel
from backend.schemas.question import RawQuestionPayload
from backend.services import cache

logger = logging.getLogger("scraper_service")

# Normaliza variações de nome da mesma banca para um único slug canônico.
BOARD_ALIASES: dict[str, str] = {
    "cespe": "cebraspe",
    "cebraspe": "cebraspe",
    "unb": "cebraspe",
    "unb/cespe": "cebraspe",
    "fundacao carlos chagas": "fcc",
    "fcc": "fcc",
    "fundacao getulio vargas": "fgv",
    "fgv": "fgv",
    "vunesp": "vunesp",
    "instituto access": "access",
}

# Nome por extenso de cada UF, usado para criar o registro de State sob demanda
# quando a fonte traz apenas a sigla e o estado ainda não existe no banco.
BRAZILIAN_STATE_NAMES: dict[str, str] = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
    "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
    "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina",
    "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins", "BR": "Federal",
}

_ALLOWED_HTML_TAGS = ["b", "i", "u", "sup", "sub", "br", "p"]


@dataclass
class ScrapeResult:
    fetched: int = 0
    parsed: int = 0
    invalid: int = 0
    duplicates_in_batch: int = 0
    inserted: int = 0
    errors: list[str] = field(default_factory=list)


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def sanitize_html(raw_html: str) -> str:
    """Remove scripts e qualquer marcação fora da allowlist do enunciado,
    prevenindo XSS armazenado a partir de conteúdo de terceiros."""
    return bleach.clean(
        raw_html, tags=_ALLOWED_HTML_TAGS, attributes={}, strip=True
    ).strip()


def normalize_board_name(raw_name: str) -> str:
    key = _strip_accents(raw_name.strip().lower())
    key = re.sub(r"\s+", " ", key)
    return BOARD_ALIASES.get(key, key)


def compute_content_hash(content: str, options: dict[str, str]) -> str:
    """SHA256 determinístico sobre enunciado + alternativas normalizados,
    usado para desduplicar entre fontes diferentes que publicam a mesma
    questão (ex.: dois agregadores citando a mesma prova de banca)."""
    normalized_content = _strip_accents(content.strip().lower())
    normalized_content = re.sub(r"\s+", " ", normalized_content)
    normalized_options = "|".join(
        f"{k.strip().upper()}:{_strip_accents(v.strip().lower())}"
        for k, v in sorted(options.items())
    )
    payload = f"{normalized_content}::{normalized_options}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def classify_difficulty(payload: RawQuestionPayload, correct_rate: float | None = None) -> DifficultyLevel:
    """Classifica a dificuldade com fallback em cascata:
    1) taxa de acerto histórica da fonte, se disponível;
    2) dica textual da própria fonte (ex.: "fácil"/"difícil");
    3) heurística pelo tamanho do enunciado como último recurso.
    """
    if correct_rate is not None:
        if correct_rate >= 0.7:
            return DifficultyLevel.EASY
        if correct_rate >= 0.4:
            return DifficultyLevel.MEDIUM
        return DifficultyLevel.HARD

    if payload.difficulty_hint:
        hint = _strip_accents(payload.difficulty_hint.strip().lower())
        if "facil" in hint:
            return DifficultyLevel.EASY
        if "dific" in hint or "hard" in hint:
            return DifficultyLevel.HARD
        if "medi" in hint:
            return DifficultyLevel.MEDIUM

    word_count = len(payload.content.split())
    if word_count < 60:
        return DifficultyLevel.EASY
    if word_count < 150:
        return DifficultyLevel.MEDIUM
    return DifficultyLevel.HARD


def _parse_question_page(html: str, source_url: str) -> RawQuestionPayload | None:
    """Ponto único de parsing HTML. Estrutura de exemplo genérica — adaptar os
    seletores CSS por fonte real mantendo o mesmo contrato de retorno."""
    soup = BeautifulSoup(html, "html.parser")

    statement_el = soup.select_one(".question-statement, .enunciado")
    if statement_el is None:
        return None

    options: dict[str, str] = {}
    for option_el in soup.select(".question-option, .alternativa"):
        letter = option_el.get("data-letter") or ""
        text = option_el.get_text(strip=True)
        if letter and text:
            options[letter.strip().upper()] = text

    correct_el = soup.select_one("[data-correct-option]")
    correct_option = (correct_el.get("data-correct-option") if correct_el else "") or ""

    meta = soup.select_one(".question-meta")
    board_name = meta.get("data-board", "") if meta else ""
    subject_name = meta.get("data-subject", "") if meta else ""
    organization = meta.get("data-org", "") if meta else ""
    role = meta.get("data-role") if meta else None
    year_raw = meta.get("data-year", "0") if meta else "0"
    state_uf = meta.get("data-uf") if meta else None
    difficulty_hint = meta.get("data-difficulty") if meta else None

    try:
        payload = RawQuestionPayload(
            content=sanitize_html(str(statement_el)),
            options={k: sanitize_html(v) for k, v in options.items()},
            correct_option=correct_option,
            board_name=board_name,
            subject_name=subject_name,
            organization=organization,
            role=role,
            year=int(year_raw) if str(year_raw).isdigit() else 0,
            state_uf=state_uf,
            source_url=source_url,
            difficulty_hint=difficulty_hint,
        )
    except ValidationError as exc:
        logger.warning("Payload inválido de %s: %s", source_url, exc)
        return None

    return payload


async def resolve_foreign_keys(
    db: AsyncSession, payload: RawQuestionPayload
) -> dict[str, Any] | None:
    """Resolve (ou cria) Board/Subject/Exam/State a partir dos nomes textuais
    do payload, retornando os IDs necessários para montar uma Question.
    Compartilhada por todos os caminhos de ingestão: scraper, POST
    /questions/batch e scripts/insert_questions.py."""
    from sqlalchemy import select

    from backend.models.taxonomy import Board, Exam, State, Subject

    board_slug = normalize_board_name(payload.board_name)
    if not board_slug or not payload.subject_name or not payload.organization:
        return None

    board = (
        await db.execute(select(Board).where(Board.slug == board_slug))
    ).scalar_one_or_none()
    if board is None:
        board = Board(name=payload.board_name.strip(), slug=board_slug, aliases=[board_slug])
        db.add(board)
        await db.flush()

    subject_slug = _strip_accents(payload.subject_name.strip().lower()).replace(" ", "-")
    subject = (
        await db.execute(select(Subject).where(Subject.slug == subject_slug))
    ).scalar_one_or_none()
    if subject is None:
        subject = Subject(name=payload.subject_name.strip(), slug=subject_slug)
        db.add(subject)
        await db.flush()

    exam = (
        await db.execute(
            select(Exam).where(
                Exam.organization == payload.organization,
                Exam.year == payload.year,
                Exam.role == payload.role,
            )
        )
    ).scalar_one_or_none()
    if exam is None:
        exam = Exam(
            name=f"{payload.organization} {payload.year}",
            organization=payload.organization.strip(),
            role=payload.role,
            year=payload.year,
        )
        db.add(exam)
        await db.flush()

    state_id = None
    if payload.state_uf:
        uf = payload.state_uf.strip().upper()
        state = (await db.execute(select(State).where(State.uf == uf))).scalar_one_or_none()
        if state is None and uf in BRAZILIAN_STATE_NAMES:
            state = State(name=BRAZILIAN_STATE_NAMES[uf], uf=uf)
            db.add(state)
            await db.flush()
        if state is not None:
            state_id = state.id

    return {
        "board_id": board.id,
        "subject_id": subject.id,
        "exam_id": exam.id,
        "state_id": state_id,
    }


class ScraperService:
    def __init__(self, concurrency: int | None = None):
        self._semaphore = asyncio.Semaphore(concurrency or settings.SCRAPER_CONCURRENCY)

    async def _fetch(self, client: httpx.AsyncClient, url: str) -> str | None:
        async with self._semaphore:
            try:
                response = await client.get(url, timeout=20.0)
                response.raise_for_status()
                return response.text
            except httpx.HTTPError as exc:
                logger.warning("Falha ao buscar %s: %s", url, exc)
                return None

    async def run(self, source_urls: list[str]) -> ScrapeResult:
        result = ScrapeResult()
        seen_hashes_in_batch: set[str] = set()
        buffer: list[dict[str, Any]] = []

        async with httpx.AsyncClient(
            headers={"User-Agent": settings.SCRAPER_USER_AGENT}, follow_redirects=True
        ) as client:
            fetch_tasks = [self._fetch(client, url) for url in source_urls]
            pages = await asyncio.gather(*fetch_tasks)

        result.fetched = sum(1 for p in pages if p is not None)

        async with get_db_context() as db:
            for url, html in zip(source_urls, pages):
                if html is None:
                    continue

                payload = _parse_question_page(html, url)
                if payload is None:
                    result.invalid += 1
                    continue
                result.parsed += 1

                content_hash = compute_content_hash(payload.content, payload.options)
                if content_hash in seen_hashes_in_batch:
                    result.duplicates_in_batch += 1
                    continue
                seen_hashes_in_batch.add(content_hash)

                existing = await crud_question.get_by_content_hash(db, content_hash)
                if existing is not None:
                    result.duplicates_in_batch += 1
                    continue

                fk_ids = await resolve_foreign_keys(db, payload)
                if fk_ids is None:
                    result.invalid += 1
                    continue

                buffer.append(
                    {
                        "content": payload.content,
                        "options": payload.options,
                        "correct_option": payload.correct_option,
                        "year": payload.year,
                        "difficulty_level": payload.difficulty_level or classify_difficulty(payload),
                        "content_hash": content_hash,
                        "source_url": payload.source_url,
                        **fk_ids,
                    }
                )

                if len(buffer) >= settings.SCRAPER_BATCH_SIZE:
                    result.inserted += await crud_question.bulk_insert_questions(db, buffer)
                    buffer.clear()

            if buffer:
                result.inserted += await crud_question.bulk_insert_questions(db, buffer)

        if result.inserted > 0:
            # Novas questões invalidam listagens filtradas em cache.
            await cache.delete_by_prefix("questions:filter:")

        logger.info(
            "Scrape finalizado: fetched=%d parsed=%d invalid=%d dup=%d inserted=%d",
            result.fetched, result.parsed, result.invalid,
            result.duplicates_in_batch, result.inserted,
        )
        return result


scraper_service = ScraperService()
