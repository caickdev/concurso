"""Executável standalone do pipeline de scraping — desacoplado do processo web.

Import apenas `backend.services.scraper_service` e `backend.database`, nunca
`backend.main`: isso mantém o worker livre de qualquer dependência do FastAPI
(SlowAPI, middlewares, etc.), então ele pode rodar em qualquer lugar sem subir
um servidor HTTP — crontab, GitHub Actions agendado, um container dedicado
(Railway/Render), ou manualmente para um backfill único.

O endpoint GET /api/v1/admin/scraper/run (routers/admin.py) cobre apenas
lotes pequenos disparáveis via Vercel Cron, por causa do limite de duração de
funções serverless; este script é o caminho recomendado para volumes maiores.

Uso:
    cd meu-app-concursos
    python -m scripts.run_scraper --url https://fonte.exemplo.com/questao/123
    python -m scripts.run_scraper --sources scripts/sources.txt

`sources.txt`: uma URL por linha; linhas em branco e iniciadas com `#` são ignoradas.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from backend.database import dispose_engine
from backend.services.scraper_service import ScrapeResult, scraper_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("run_scraper")


def _load_urls_from_file(path: str) -> list[str]:
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Arquivo de fontes não encontrado: {path}")
    lines = file_path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


async def run(urls: list[str]) -> ScrapeResult:
    try:
        return await scraper_service.run(urls)
    finally:
        # Processo de vida curta — libera as conexões do pool antes de sair.
        await dispose_engine()


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa o pipeline de scraping de questões.")
    parser.add_argument(
        "--url", action="append", default=[], dest="urls",
        help="URL individual de origem (pode repetir a flag para várias).",
    )
    parser.add_argument(
        "--sources", default=None,
        help="Arquivo texto com uma URL de origem por linha.",
    )
    args = parser.parse_args()

    urls = list(args.urls)
    if args.sources:
        urls.extend(_load_urls_from_file(args.sources))

    if not urls:
        logger.error("Nenhuma URL de origem informada (use --url ou --sources).")
        return 1

    logger.info("Iniciando scraping de %d fonte(s)...", len(urls))
    result = asyncio.run(run(urls))

    logger.info(
        "Resumo: fetched=%d parsed=%d invalid=%d duplicates=%d inserted=%d",
        result.fetched, result.parsed, result.invalid,
        result.duplicates_in_batch, result.inserted,
    )
    if result.errors:
        for err in result.errors:
            logger.warning("Erro durante o scraping: %s", err)

    return 0


if __name__ == "__main__":
    sys.exit(main())
