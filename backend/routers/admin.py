"""Endpoints administrativos internos — hoje, apenas o gatilho HTTP do scraper
usado pela Vercel Cron. Não usar como caminho principal de scraping: funções
serverless têm limite de duração (10-60s no Hobby/Pro, ~800s com Fluid
Compute), então lotes grandes devem rodar via `scripts/run_scraper.py` em um
worker/container dedicado ou pipeline agendado fora da Vercel (GitHub Actions,
Railway, etc.). Este endpoint serve para lotes pequenos/incrementais.
"""
from fastapi import APIRouter, Header, HTTPException, status

from backend.core.config import settings
from backend.services.scraper_service import scraper_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/scraper/run")
async def trigger_scraper(authorization: str | None = Header(default=None)):
    """Disparado pela Vercel Cron (GET agendado). A Vercel injeta
    automaticamente `Authorization: Bearer <CRON_SECRET>` quando a variável
    de ambiente CRON_SECRET está configurada no projeto — validamos esse
    header para que o endpoint não fique publicamente acionável."""
    if not settings.CRON_SECRET or authorization != f"Bearer {settings.CRON_SECRET}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autorizado.")

    source_urls = settings.scraper_source_urls
    if not source_urls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhuma fonte configurada em SCRAPER_SOURCE_URLS.",
        )

    result = await scraper_service.run(source_urls)
    return {
        "fetched": result.fetched,
        "parsed": result.parsed,
        "invalid": result.invalid,
        "duplicates_in_batch": result.duplicates_in_batch,
        "inserted": result.inserted,
    }
