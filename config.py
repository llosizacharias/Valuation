"""
config.py — Carregamento centralizado de variaveis de ambiente.

Uso:
    from config import env, required_env

    BRAPI_TOKEN = required_env("BRAPI_TOKEN")
    EMAIL_FROM  = env("ALERT_EMAIL_FROM", default="")
"""
import os
from pathlib import Path
from dotenv import load_dotenv

_DOTENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(_DOTENV_PATH)


def env(name: str, default: str = None) -> str:
    """Retorna variavel de ambiente. Aceita default opcional."""
    return os.getenv(name, default)


def required_env(name: str) -> str:
    """Variavel obrigatoria. Levanta erro claro se ausente."""
    val = os.getenv(name)
    if val is None or val == "":
        raise RuntimeError(
            f"Variavel obrigatoria '{name}' nao definida em .env. "
            f"Verifique {_DOTENV_PATH}"
        )
    return val
