"""Moderação de comentários: bloqueio síncrono de profanidade + suporte à
ocultação automática por denúncias (o limiar em si vive em models/comment.py)."""
from fastapi import HTTPException, status

from backend.core.profanity import contains_profanity


def enforce_no_profanity(content: str) -> None:
    """Levanta HTTP 400 se o texto contiver palavrões em português.
    Chamado antes de qualquer persistência do comentário."""
    if contains_profanity(content):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seu comentário contém linguagem imprópria e não pode ser publicado.",
        )
