"""
ComDinheiro API client v2.

Endpoint: https://api.comdinheiro.com.br/v1/ep1/import-data
Custo: 1 pageview por call.
Auth: form-urlencoded (username, password, URL, format).
"""
import os
import json
import time
import requests
from urllib.parse import quote
from pathlib import Path
from datetime import datetime


# Carrega .env manualmente (sem depender de python-dotenv)
def _load_env(path="/opt/shipyard/.env"):
    if not Path(path).exists():
        return
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

_load_env()


ENDPOINT = "https://api.comdinheiro.com.br/v1/ep1/import-data"
USER = os.environ.get("COMDINHEIRO_USER")
PASS = os.environ.get("COMDINHEIRO_PASSWORD")

if not USER or not PASS:
    raise RuntimeError(
        "COMDINHEIRO_USER ou COMDINHEIRO_PASSWORD ausentes em /opt/shipyard/.env"
    )


# Log de pageviews consumidos (auditoria)
PAGEVIEW_LOG = "/opt/shipyard/comdinheiro_v2/pageview_log.jsonl"


def _log_pageview(url, status, elapsed_ms, err=None):
    """Anexa 1 linha por chamada — auditoria de quota consumida."""
    rec = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "url": url[:120],
        "status": status,
        "elapsed_ms": elapsed_ms,
        "err": err,
    }
    with open(PAGEVIEW_LOG, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def call(tool_url, fmt="json3", timeout=60):
    """
    Faz 1 chamada à API ComDinheiro.

    Args:
        tool_url: URL da ferramenta SEM https://www.comdinheiro.com.br/
                  Ex: 'StockScreenerCadastral001.php?papel=OPCT3&...'
        fmt: 'json3' (default) ou 'xml2'
        timeout: segundos

    Returns:
        dict (se fmt=json3) ou str (xml)

    Custo: 1 pageview consumido por chamada.
    """
    if tool_url.startswith("https://"):
        # Remove prefixo se vier completo
        tool_url = tool_url.replace("https://www.comdinheiro.com.br/", "")
    if tool_url.startswith("/"):
        tool_url = tool_url[1:]

    payload = {
        "username": USER,
        "password": PASS,
        "URL": tool_url,
        "format": fmt,
    }

    headers = {
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    t0 = time.time()
    try:
        resp = requests.post(ENDPOINT, data=payload, headers=headers, timeout=timeout)
        elapsed_ms = int((time.time() - t0) * 1000)
        _log_pageview(tool_url, resp.status_code, elapsed_ms)

        if resp.status_code != 200:
            raise RuntimeError(
                f"HTTP {resp.status_code}: {resp.text[:200]}"
            )

        text = resp.text
        if fmt == "json3":
            return json.loads(text)
        return text

    except requests.RequestException as e:
        elapsed_ms = int((time.time() - t0) * 1000)
        _log_pageview(tool_url, 0, elapsed_ms, err=str(e))
        raise


def count_pageviews_today():
    """Quantas pageviews consumimos hoje? (lendo log local)"""
    today = datetime.now().strftime("%Y-%m-%d")
    if not Path(PAGEVIEW_LOG).exists():
        return 0
    n = 0
    with open(PAGEVIEW_LOG) as f:
        for line in f:
            try:
                rec = json.loads(line)
                if rec.get("ts", "").startswith(today):
                    n += 1
            except Exception:
                pass
    return n


if __name__ == "__main__":
    # Smoke test: 1 call StockScreenerCadastral001 + OPCT3
    print("=== Smoke test ComDinheiro v2 ===")
    print(f"Endpoint: {ENDPOINT}")
    print(f"User: {USER}")
    print(f"Password: {'*' * len(PASS) if PASS else '<missing>'}")
    print(f"Pageviews consumidos hoje (log local): {count_pageviews_today()}")
    print()

    # URL exata que você gerou no portal
    tool_url = (
        "StockScreenerCadastral001.php?"
        "&papel=OPCT3"
        "&data_analise=05052026"
        "&num_casas=2"
        "&enviar_email=0"
        "&periodicidade=diaria"
        "&cabecalho_excel=modo1"
        "&classes_ativos=acoes"
    )

    print(f"Chamando: {tool_url[:80]}...")
    print()

    try:
        result = call(tool_url, fmt="json3")
        print(f"✓ Resposta recebida (tipo: {type(result).__name__})")
        print()
        print(f"Estrutura top-level (chaves): {list(result.keys()) if isinstance(result, dict) else 'NOT DICT'}")
        print()
        print("=== Conteúdo (primeiros 2000 chars do JSON formatado) ===")
        formatted = json.dumps(result, ensure_ascii=False, indent=2)
        print(formatted[:2000])
        if len(formatted) > 2000:
            print(f"\n... [truncado, total {len(formatted)} chars]")
    except Exception as e:
        print(f"✗ FALHA: {type(e).__name__}: {e}")
        raise

    print()
    print(f"=== Pageviews consumidos hoje (após este teste): {count_pageviews_today()}")
