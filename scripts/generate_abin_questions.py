"""Executável standalone para gerar questões inéditas estilo CEBRASPE
(Certo/Errado), nível HARD, focadas no concurso da ABIN — cargo Oficial de
Inteligência, área de Tecnologia da Informação/Cibersegurança — via API da
Anthropic, e inseri-las em lote direto no banco configurado em
`backend/.env` (`DATABASE_URL`).

Reaproveita o mesmo pipeline de `scripts/insert_questions.py`: sanitização
(`sanitize_html`), dedup por hash (`compute_content_hash` + `content_hash`
UNIQUE no banco, com `INSERT ... ON CONFLICT DO NOTHING`) e resolução de
banca/matéria/órgão (`resolve_foreign_keys`). As questões geradas passam
pelo formato intermediário RawQuestionPayload (backend/schemas/question.py)
antes de virar linhas no banco — mesmo contrato usado pelo scraper e pela
rota POST /questions/batch.

Tópicos cobertos (ver SUBJECTS abaixo):
    1. Segurança de Redes e Criptografia — RSA, SHA-256, PKI/ICP-Brasil,
       Firewalls, IDS/IPS, Zero Trust, SIEM.
    2. Ataques e Forense Digital — Ransomware, APTs, Phishing, OWASP Top 10,
       Malware Analysis.
    3. Legislação e Governança — LGPD, Marco Civil da Internet, LAI, PNSI,
       ISO 27001, NIST.
    4. Português (CEBRASPE) — reescrita e sintaxe em textos de tecnologia e
       geopolítica.

Uso:
    cd meu-app-concursos
    .venv\\Scripts\\python.exe -m scripts.generate_abin_questions --count 10
    .venv\\Scripts\\python.exe -m scripts.generate_abin_questions --subject "Legislação e Governança" --count 5
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from anthropic import AsyncAnthropic, APIError

from backend.core.config import settings
from backend.crud.crud_question import crud_question
from backend.database import dispose_engine, get_db_context
from backend.models.question import DifficultyLevel
from backend.schemas.question import RawQuestionPayload
from backend.services import cache
from backend.services.cache import redis_client
from backend.services.scraper_service import resolve_foreign_keys, sanitize_html
from backend.services.scraper_service import compute_content_hash as _compute_content_hash

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("generate_abin_questions")

# --- Configuração fixa do concurso alvo ------------------------------------

BOARD_NAME = "CEBRASPE"
ORGANIZATION = "ABIN - Agência Brasileira de Inteligência"
ROLE = "Oficial de Inteligência - Área de Tecnologia da Informação"
DIFFICULTY = DifficultyLevel.HARD
# Todo item CEBRASPE é um julgamento Certo/Errado — nunca A-E.
CE_OPTIONS = {"C": "Certo", "E": "Errado"}

# Máximo de itens pedidos por chamada ao modelo — lotes menores reduzem risco
# de truncamento/malformação do JSON de resposta.
CHUNK_SIZE = 8


@dataclass(frozen=True)
class SubjectSpec:
    name: str
    keywords: list[str]
    guidance: str = ""


SUBJECTS: list[SubjectSpec] = [
    SubjectSpec(
        name="Segurança de Redes e Criptografia",
        keywords=[
            "Criptografia assimétrica RSA",
            "Função de hash SHA-256",
            "PKI/ICP-Brasil",
            "Firewalls",
            "IDS/IPS",
            "Arquitetura Zero Trust",
            "SIEM",
        ],
    ),
    SubjectSpec(
        name="Ataques e Forense Digital",
        keywords=[
            "Ransomware",
            "APT (Advanced Persistent Threat)",
            "Phishing e engenharia social",
            "OWASP Top 10",
            "Análise de malware (Malware Analysis)",
        ],
    ),
    SubjectSpec(
        name="Legislação e Governança",
        keywords=[
            "LGPD (Lei 13.709/2018)",
            "Marco Civil da Internet (Lei 12.965/2014)",
            "LAI (Lei 12.527/2011)",
            "PNSI (Política Nacional de Segurança da Informação)",
            "ISO/IEC 27001",
            "NIST Cybersecurity Framework",
        ],
    ),
    SubjectSpec(
        name="Português",
        keywords=["Reescrita de período", "Sintaxe", "Regência e concordância", "Coesão e coerência"],
        guidance=(
            "Baseie cada item em um trecho curto e autoral (3-5 linhas), redigido em registro "
            "formal, sobre tecnologia da informação, cibersegurança ou geopolítica internacional. "
            "Avalie exclusivamente aspectos linguísticos do trecho — reescrita mantendo o sentido "
            "original, regência, concordância, pontuação, coesão referencial/sequencial — nunca o "
            "conteúdo factual do texto."
        ),
    ),
]

_SYSTEM_PROMPT = (
    "Você é um elaborador de itens da banca CEBRASPE, especialista no concurso da ABIN "
    f"(cargo: {ROLE}). Produza itens INÉDITOS no formato Certo/Errado (julgamento), nível de "
    "dificuldade ALTO — exigem articulação entre conceitos, atenção a pegadinhas técnicas ou "
    "exceções, não apenas memorização direta. Nunca copie questões de provas reais; toda redação "
    "deve ser autoral. Responda SOMENTE com um array JSON válido, sem texto fora do JSON, no "
    'formato: [{"content": "<enunciado do item>", "correct_option": "C"|"E", '
    '"justification": "<1-2 frases justificando o gabarito>"}, ...].'
)


def _build_user_prompt(subject: SubjectSpec, count: int) -> str:
    lines = [
        f"Matéria: {subject.name}",
        f"Subtemas a cobrir (distribua os itens entre eles): {', '.join(subject.keywords)}",
        f"Gere exatamente {count} itens Certo/Errado inéditos, nível difícil.",
    ]
    if subject.guidance:
        lines.append(subject.guidance)
    return "\n".join(lines)


def _extract_json_array(text: str) -> list[dict[str, Any]]:
    """Extrai o array JSON da resposta do modelo, tolerando cercas de código
    (```json ... ```) ou texto acidental fora do array."""
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError("Nenhum array JSON encontrado na resposta do modelo.")
    # strict=False: o modelo às vezes emite quebras de linha literais (não
    # escapadas como \n) dentro de valores de string — comum em itens de
    # Português que citam um trecho de texto multilinha. json em modo
    # estrito rejeita esses caracteres de controle; strict=False os aceita.
    return json.loads(match.group(0), strict=False)


async def _generate_chunk(
    client: AsyncAnthropic, subject: SubjectSpec, count: int, year: int
) -> list[RawQuestionPayload]:
    try:
        response = await client.messages.create(
            model=settings.AI_MODEL_NAME,
            max_tokens=8192,
            # claude-sonnet-5 usa thinking adaptativo por padrão (diferente do
            # sonnet-4.6) e max_tokens é um teto sobre thinking + texto juntos —
            # sem desligar, o thinking pode consumir a maior parte do budget e
            # truncar o JSON antes do "]" de fechamento (stop_reason=max_tokens).
            # Geração de item Certo/Errado é formatação direta, não precisa de
            # raciocínio estendido.
            thinking={"type": "disabled"},
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(subject, count)}],
            timeout=120.0,
        )
    except APIError as exc:
        logger.error("Falha na chamada à API da Anthropic (%s): %s", subject.name, exc)
        return []

    text = "\n".join(block.text for block in response.content if block.type == "text")
    try:
        raw_items = _extract_json_array(text)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning("Resposta do modelo não pôde ser parseada (%s): %s", subject.name, exc)
        return []

    payloads: list[RawQuestionPayload] = []
    for item in raw_items:
        content = str(item.get("content", "")).strip()
        correct_option = str(item.get("correct_option", "")).strip().upper()
        if not content or correct_option not in CE_OPTIONS:
            logger.warning("Item inválido descartado (%s): %r", subject.name, item)
            continue
        payloads.append(
            RawQuestionPayload(
                content=content,
                options=CE_OPTIONS,
                correct_option=correct_option,
                board_name=BOARD_NAME,
                subject_name=subject.name,
                organization=ORGANIZATION,
                role=ROLE,
                year=year,
                difficulty_level=DIFFICULTY,
            )
        )
    return payloads


async def generate_questions(
    client: AsyncAnthropic, subject: SubjectSpec, count: int, year: int
) -> list[RawQuestionPayload]:
    """Gera `count` itens Certo/Errado inéditos sobre `subject` via API da
    Anthropic, em lotes de até CHUNK_SIZE por chamada."""
    payloads: list[RawQuestionPayload] = []
    remaining = count
    while remaining > 0:
        chunk_count = min(CHUNK_SIZE, remaining)
        payloads.extend(await _generate_chunk(client, subject, chunk_count, year))
        remaining -= chunk_count
    return payloads


async def insert_all(payloads: list[RawQuestionPayload]) -> tuple[int, int, int]:
    """Insere os itens gerados em lote, com verificação de duplicidade em
    duas camadas: (1) hash já visto neste lote, (2) hash já existente no
    banco. Retorna (inserido, duplicado, invalido)."""
    inserted = duplicates = invalid = 0
    seen_hashes: set[str] = set()
    rows: list[dict[str, Any]] = []

    async with get_db_context() as db:
        for payload in payloads:
            clean_content = sanitize_html(payload.content)
            clean_options = {k: sanitize_html(v) for k, v in payload.options.items()}
            content_hash = _compute_content_hash(clean_content, clean_options)

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
                    "difficulty_level": DIFFICULTY,
                    "content_hash": content_hash,
                    "source_url": None,
                    **fk_ids,
                }
            )

        if rows:
            inserted = await crud_question.bulk_insert_questions(db, rows)
            duplicates += len(rows) - inserted

        if inserted > 0:
            await cache.delete_by_prefix("questions:filter:")
            await cache.delete("taxonomy:subjects", "taxonomy:boards", "taxonomy:states")

    return inserted, duplicates, invalid


async def main_async(subjects: list[SubjectSpec], count_per_subject: int, year: int) -> int:
    if not settings.AI_PROVIDER_API_KEY:
        logger.error("AI_PROVIDER_API_KEY não configurada em backend/.env.")
        return 1

    client = AsyncAnthropic(api_key=settings.AI_PROVIDER_API_KEY)
    try:
        all_payloads: list[RawQuestionPayload] = []
        for subject in subjects:
            logger.info("Gerando %d questão(ões) sobre '%s'...", count_per_subject, subject.name)
            generated = await generate_questions(client, subject, count_per_subject, year)
            logger.info("  -> %d item(ns) gerado(s) e válido(s) para '%s'.", len(generated), subject.name)
            all_payloads.extend(generated)

        if not all_payloads:
            logger.error("Nenhuma questão válida foi gerada.")
            return 1

        logger.info("Inserindo %d questão(ões) geradas no banco...", len(all_payloads))
        inserted, duplicates, invalid = await insert_all(all_payloads)
        logger.info(
            "Resumo: geradas=%d inserido=%d duplicadas=%d inválidas=%d",
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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--subject", action="append", dest="subjects", choices=[s.name for s in SUBJECTS],
        help="Matéria específica (repetível). Sem isso, gera para todas as SUBJECTS.",
    )
    parser.add_argument("--count", type=int, default=10, help="Questões por matéria (padrão: 10).")
    parser.add_argument("--year", type=int, default=2025, help="Ano atribuído às questões geradas (padrão: 2025).")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    subjects = (
        [s for s in SUBJECTS if s.name in args.subjects] if args.subjects else SUBJECTS
    )
    return asyncio.run(main_async(subjects, args.count, args.year))


if __name__ == "__main__":
    raise SystemExit(main())
