"""
comdinheiro_client.py — Shipyard | Vela Capital
Cliente da API ComDinheiro (Nelogica)

Endpoint: POST https://www.comdinheiro.com.br/Clientes/API/EndPoint001.php
Docs:     https://www.comdinheiro.com.br/ManualImportacaoAPI001.php
"""

import os
import json
import requests
import pandas as pd
from functools import lru_cache
from datetime import datetime, timedelta

# ── Configuração ──────────────────────────────────────────────────
API_URL  = "https://www.comdinheiro.com.br/Clientes/API/EndPoint001.php"
CD_USER  = os.getenv("COMDINHEIRO_USER", "vela.capital")
CD_PASS  = os.getenv("COMDINHEIRO_PASS", "Vela.capital1!")
TIMEOUT  = 30

HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}


# ══════════════════════════════════════════════════════════════════
# FUNÇÃO BASE — requisição genérica
# ══════════════════════════════════════════════════════════════════
def _request(url_consulta: str, fmt: str = "JSON3") -> dict:
    """
    Faz POST na API ComDinheiro e retorna dict JSON.
    url_consulta: caminho SEM o prefixo https://www.comdinheiro.com.br/
    """
    payload = (
        f"username={CD_USER}"
        f"&password={CD_PASS}"
        f"&URL={requests.utils.quote(url_consulta, safe='=&?/')}"
        f"&format={fmt}"
    )
    resp = requests.request(
        "POST", API_URL,
        data=payload,
        headers=HEADERS,
        params={"code": "import_data"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def test_connection() -> dict:
    """Testa a conexão com a API. Retorna {'ok': bool, 'msg': str}"""
    try:
        # Usa ferramenta leve: histórico de cotação de 1 dia
        hoje = datetime.today()
        d = (hoje - timedelta(days=5)).strftime("%d%m%Y")
        d2 = hoje.strftime("%d%m%Y")
        url = (
            f"HistoricoCotacao002.php?&x=WEGE3"
            f"&data_ini={d}&data_fim={d2}&pagina=1&cabecalho_excel=modo1"
        )
        data = _request(url)
        if "tabela" in str(data) or "erro" not in str(data).lower():
            return {"ok": True, "msg": "Conexão OK"}
        return {"ok": False, "msg": str(data)[:200]}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


# ══════════════════════════════════════════════════════════════════
# 1. MÚLTIPLOS HISTÓRICOS
# Ferramenta: IndicadoresFundamentalistas001
# ══════════════════════════════════════════════════════════════════
def get_multiplos_historicos(papel: str, anos: int = 5) -> pd.DataFrame:
    """
    Retorna DataFrame com múltiplos históricos trimestrais:
    P/L, EV/EBITDA, P/VPA, EV/EBIT, Div.Yield, ROE, ROIC
    papel: ex "WEGE3" (sem .SA)
    """
    hoje = datetime.today()
    d_fim = hoje.strftime("%d%m%Y")
    d_ini = (hoje - timedelta(days=365 * anos)).strftime("%d%m%Y")

    indicadores = (
        "pl+ev_ebitda+pvpa+ev_ebit+dy+roe+roic+"
        "lucro_liquido+ebitda+receita_liquida+divida_liquida"
    )

    url = (
        f"IndicadoresFundamentalistas001.php?"
        f"&papel={papel}"
        f"&data_ini={d_ini}&data_fim={d_fim}"
        f"&indicadores={indicadores}"
        f"&periodicidade=trimestral"
        f"&cabecalho_excel=modo1"
    )

    try:
        data = _request(url)
        return _parse_indicadores(data, papel)
    except Exception as e:
        return pd.DataFrame({"Erro": [str(e)]})


def _parse_indicadores(data: dict, papel: str) -> pd.DataFrame:
    """Parseia JSON3 da ComDinheiro para DataFrame."""
    try:
        # JSON3 structure: {"tabela": {"lin": [...], "col": [...]}}
        if isinstance(data, dict):
            tabela = data.get("tabela") or data.get("data") or data
            if isinstance(tabela, dict):
                lins = tabela.get("lin", [])
                cols = tabela.get("col", [])
                if lins and cols:
                    rows = []
                    for lin in lins:
                        row = {}
                        for i, col in enumerate(cols):
                            vals = lin.get("cel", [])
                            row[col] = vals[i] if i < len(vals) else None
                        rows.append(row)
                    return pd.DataFrame(rows)
            # Tenta estrutura alternativa
            if isinstance(tabela, list):
                return pd.DataFrame(tabela)
        return pd.DataFrame({"raw": [str(data)[:500]]})
    except Exception as e:
        return pd.DataFrame({"parse_erro": [str(e)]})


# ══════════════════════════════════════════════════════════════════
# 2. CONSENSO DE ANALISTAS
# Ferramenta: ComparaEmpresas001 com indicadores de consenso
# ══════════════════════════════════════════════════════════════════
def get_consenso(papel: str) -> dict:
    """
    Retorna dict com preço-alvo consenso, recomendação e nº analistas.
    """
    url = (
        f"ComparaEmpresas001.php?"
        f"&lista_papel={papel}"
        f"&indicadores=preco_alvo_consenso+recomendacao_consenso+num_analistas_consenso+preco_alvo_minimo+preco_alvo_maximo"
        f"&data_ini=&data_fim="
        f"&cabecalho_excel=modo1"
    )
    try:
        data = _request(url)
        df = _parse_indicadores(data, papel)
        if df.empty or "Erro" in df.columns:
            return {}
        row = df.iloc[0].to_dict() if not df.empty else {}
        return {
            "preco_alvo":   _to_float(row.get("preco_alvo_consenso")),
            "preco_min":    _to_float(row.get("preco_alvo_minimo")),
            "preco_max":    _to_float(row.get("preco_alvo_maximo")),
            "recomendacao": row.get("recomendacao_consenso", "—"),
            "n_analistas":  _to_int(row.get("num_analistas_consenso")),
        }
    except Exception as e:
        return {"erro": str(e)}


# ══════════════════════════════════════════════════════════════════
# 3. PROVENTOS E DIVIDENDOS
# Ferramenta: AgendaProventos001
# ══════════════════════════════════════════════════════════════════
def get_proventos(papel: str, anos: int = 5) -> pd.DataFrame:
    """
    Retorna histórico de proventos (dividendos + JCP) dos últimos N anos.
    """
    hoje = datetime.today()
    d_fim = hoje.strftime("%d%m%Y")
    d_ini = (hoje - timedelta(days=365 * anos)).strftime("%d%m%Y")

    url = (
        f"AgendaProventos001.php?"
        f"&papel={papel}"
        f"&data_ini={d_ini}&data_fim={d_fim}"
        f"&tipo_provento=todos"
        f"&cabecalho_excel=modo1"
    )
    try:
        data = _request(url)
        return _parse_indicadores(data, papel)
    except Exception as e:
        return pd.DataFrame({"Erro": [str(e)]})


# ══════════════════════════════════════════════════════════════════
# 4. DRE SINTÉTICA
# Ferramenta: BalancosSinteticos001
# ══════════════════════════════════════════════════════════════════
def get_dre_sintetica(papel: str, anos: int = 5) -> pd.DataFrame:
    """
    Retorna DRE sintética (receita, EBITDA, EBIT, lucro líquido) histórica.
    """
    hoje = datetime.today()
    d_fim = hoje.strftime("%d%m%Y")
    d_ini = (hoje - timedelta(days=365 * anos)).strftime("%d%m%Y")

    url = (
        f"BalancosSinteticos001.php?"
        f"&papel={papel}"
        f"&data_ini={d_ini}&data_fim={d_fim}"
        f"&tipo=dre"
        f"&periodicidade=anual"
        f"&cabecalho_excel=modo1"
    )
    try:
        data = _request(url)
        return _parse_indicadores(data, papel)
    except Exception as e:
        return pd.DataFrame({"Erro": [str(e)]})


# ══════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════
def _to_float(v) -> float | None:
    try:
        return float(str(v).replace(",", ".").replace("%", "").strip())
    except Exception:
        return None


def _to_int(v) -> int | None:
    try:
        return int(float(str(v).strip()))
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════
# TESTE RÁPIDO (rodar direto no VPS)
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=== Teste ComDinheiro API ===")
    print("\n1. Conexão:")
    r = test_connection()
    print(f"   {'✅' if r['ok'] else '❌'} {r['msg']}")

    print("\n2. Múltiplos WEGE3 (2 anos):")
    df = get_multiplos_historicos("WEGE3", anos=2)
    print(df.head(3).to_string())

    print("\n3. Consenso WEGE3:")
    c = get_consenso("WEGE3")
    print(f"   {c}")

    print("\n4. Proventos WEGE3 (3 anos):")
    dp = get_proventos("WEGE3", anos=3)
    print(dp.head(5).to_string())