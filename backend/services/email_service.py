"""Envio de e-mails transacionais via API do Resend (REST simples, sem SMTP).

Se `RESEND_API_KEY` não estiver configurada, os envios são apenas logados
(nunca falham a request que os disparou) — útil em desenvolvimento local
sem precisar de uma conta de e-mail configurada.
"""
import logging

import httpx

from backend.core.config import settings

logger = logging.getLogger("email_service")

_RESEND_API_URL = "https://api.resend.com/emails"


async def send_email(*, to: str, subject: str, html: str) -> bool:
    """Retorna True se o e-mail foi (ou seria, em modo log) enviado.
    Nunca levanta exceção — falhas de envio não devem derrubar o fluxo que
    disparou o e-mail (ex.: reset de senha continua "aparentando sucesso"
    mesmo se o provedor de e-mail estiver fora, por segurança/UX)."""
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY não configurada — e-mail para %s não enviado (modo log): %s", to, subject)
        return False

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                _RESEND_API_URL,
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                json={
                    "from": settings.EMAIL_FROM,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                },
            )
            response.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        logger.error("Falha ao enviar e-mail para %s: %s", to, exc)
        return False


def build_password_reset_email(*, reset_url: str) -> str:
    return f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
      <h2 style="color: #1e293b;">Redefinição de senha</h2>
      <p style="color: #475569;">
        Recebemos uma solicitação para redefinir a senha da sua conta na
        Plataforma de Questões para Concursos. Clique no botão abaixo para
        escolher uma nova senha:
      </p>
      <p style="text-align: center; margin: 24px 0;">
        <a href="{reset_url}"
           style="background: #2d57c9; color: white; padding: 12px 24px;
                  border-radius: 8px; text-decoration: none; font-weight: 600;">
          Redefinir senha
        </a>
      </p>
      <p style="color: #94a3b8; font-size: 13px;">
        Se você não solicitou isso, pode ignorar este e-mail com segurança —
        sua senha atual continua válida. Este link expira em
        {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutos.
      </p>
    </div>
    """
