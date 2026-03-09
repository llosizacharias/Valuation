"""
companies_config.py
────────────────────
Configuração central das empresas cobertas pelo sistema de valuation.

Campos obrigatórios:
  ticker          : ticker Yahoo Finance (ex: "WEGE3.SA")
  cvm_code        : código CVM sem zeros à esquerda (ex: "5410")
  shares_out      : número de ações emitidas (unidade: ações)
  terminal_growth : crescimento na perpetuidade (ex: 0.04 = 4%)
  cost_of_debt    : custo bruto da dívida (ex: 0.12 = 12% a.a.)

Campos opcionais — overrides forward-looking:
  revenue_growth_override : substitui o CAGR calculado pelo histórico.
                            Use quando a empresa está em aceleração/desaceleração
                            não capturada pelos dados históricos da CVM.
                            Ex: COGNA reportou +18.9% em 3T25 — histórico
                            de 2019-2024 não reflete essa tendência atual.

  ebit_margin_override    : substitui a margem EBIT calculada pelo histórico
                            ponderado. Use quando a margem mais recente é
                            mais representativa do futuro (ex: após turnaround).
                            Ex: COGNA 2024 = 21.2%, mas média ponderada
                            ainda é puxada por anos de impairment.

Quando um override é definido, o modelo printa um aviso claro para auditoria.
Para voltar ao cálculo automático, comente ou remova o campo.
"""

COMPANIES = {

    "WEG": {
        "ticker":        "WEGE3.SA",
        "cvm_code":      "5410",
        "company_id_mz": "50c1bd3e-8ac6-42d9-884f-b9d69f690602",
        "ri_url":        "https://ri.weg.net",
        "shares_out":    4_197_317_998,
        "terminal_growth": 0.04,
        "cost_of_debt":    0.12,
        # WEG: sem overrides — dados históricos CVM são representativos
    },

    "COGNA": {
        "ticker":        "COGN3.SA",
        "cvm_code":      "17973",
        "company_id_mz": "e1110a12-6e58-4cb0-be24-ed1d5f18049a",
        "ri_url":        "https://ri.cogna.com.br",
        "shares_out":    1_833_167_226,
        "terminal_growth": 0.035,
        "cost_of_debt":    0.14,

        # ── Override IFRS 16 (arrendamentos) ───────────────────
        # COGNA usa subconta .03 para arrendamentos (não .02 como WEG),
        # então DEBT_SHORT/LONG_FIN capta só empréstimos (~R$83M).
        # Usamos dívida total (2.01.04 + 2.02.01) menos este valor.
        # Fonte: 4T24 — dívida bruta financeira ~R$5.2bi, arrendamentos ~R$1.7bi.
        "ifrs16_lease_total": 1_700_000_000,

        # ── Overrides forward-looking ──────────────────────────
        # Fonte: resultado 3T25 (nov/2025) — receita +18.9% a/a no trimestre,
        #        +13% no acumulado 9M25. Dados CVM disponíveis até 2024.
        #        CAGR calculado do histórico 2019-2024 = -1.9% (distorcido
        #        pela queda pós-FIES e pandemia), blended = +5.4%.
        #        Mercado está precificando crescimento de ~12-15%.
        "revenue_growth_override": 0.13,   # +13% a/a (acumulado 9M25 vs 9M24)

        # Margem EBIT 2024 = 21.2%. Modelo histórico ponderado = 15.8%
        # (ainda arrastado por 2020 com -61%). Com overhead de ~2-3pp
        # de eficiência em 2025+, projetar 21% é conservador.
        "ebit_margin_override": 0.21,      # margem EBIT observada em 2024
    },

}

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def get_company(nome: str) -> dict:
    """Retorna config da empresa (case-insensitive). KeyError se não encontrada."""
    key = nome.upper()
    if key not in COMPANIES:
        raise KeyError(
            f"Empresa '{nome}' não encontrada. Disponíveis: {list(COMPANIES.keys())}"
        )
    return COMPANIES[key]


def list_companies() -> list[str]:
    return list(COMPANIES.keys())