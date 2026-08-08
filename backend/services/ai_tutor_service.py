"""Tutor IA: gera explicações estruturadas em Markdown para uma questão,
usando o enunciado, alternativas e gabarito oficial como contexto.
"""
import logging

from anthropic import AsyncAnthropic, APIError
from fastapi import HTTPException, status

from backend.core.config import settings
from backend.models.question import Question

logger = logging.getLogger("ai_tutor_service")

_SYSTEM_PROMPT = (
    "Você é um tutor especialista em preparação para concursos públicos brasileiros. "
    "Dado o enunciado, as alternativas e o gabarito oficial de uma questão, produza uma "
    "explicação didática em Markdown com esta estrutura:\n"
    "## Resolução\n<explicação direta do porquê a alternativa correta está certa>\n\n"
    "## Por que as outras alternativas estão erradas\n<lista com um item por alternativa incorreta>\n\n"
    "## Pontos-chave para memorizar\n<lista curta de conceitos a revisar>\n\n"
    "Seja objetivo, use linguagem clara e cite a base legal/teórica quando aplicável."
)


def _build_user_prompt(question: Question, user_selected_option: str | None) -> str:
    options_text = "\n".join(f"{letra}) {texto}" for letra, texto in question.options.items())
    lines = [
        f"Enunciado:\n{question.content}",
        f"\nAlternativas:\n{options_text}",
        f"\nGabarito oficial: {question.correct_option}",
    ]
    if user_selected_option:
        lines.append(f"\nAlternativa marcada pelo aluno: {user_selected_option}")
    return "\n".join(lines)


class AITutorService:
    def __init__(self) -> None:
        self._client: AsyncAnthropic | None = None

    def _get_client(self) -> AsyncAnthropic:
        if self._client is None:
            if not settings.AI_PROVIDER_API_KEY:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Tutor IA não configurado no servidor.",
                )
            self._client = AsyncAnthropic(api_key=settings.AI_PROVIDER_API_KEY)
        return self._client

    async def explain(self, question: Question, user_selected_option: str | None = None) -> str:
        client = self._get_client()
        try:
            response = await client.messages.create(
                model=settings.AI_MODEL_NAME,
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": _build_user_prompt(question, user_selected_option)}
                ],
                timeout=settings.AI_REQUEST_TIMEOUT,
            )
        except APIError as exc:
            logger.error("Falha na chamada ao Tutor IA: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Não foi possível gerar a explicação no momento. Tente novamente.",
            ) from exc

        text_blocks = [block.text for block in response.content if block.type == "text"]
        return "\n".join(text_blocks).strip()


ai_tutor_service = AITutorService()
