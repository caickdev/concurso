"""Entrypoint ASGI usado pelo runtime Python da Vercel.

A Vercel detecta automaticamente qualquer arquivo dentro de `/api` que
exponha uma variável ASGI chamada `app` e o serve como Serverless Function.
`vercel.json` reescreve todo tráfego de `/api/*` para este arquivo, que por
sua vez delega para a aplicação FastAPI real em `backend/main.py` — nenhuma
lógica de negócio mora aqui, apenas a ponte de deploy.
"""
from backend.main import app  # noqa: F401
