"""
companies_config.py
────────────────────
Registro central de empresas do sistema de valuation.

Para adicionar uma nova empresa:
1. Abra o site de RI da empresa (ex: ri.cogna.com.br)
2. Abra o DevTools (F12) → aba Network → filtre por "apicatalog.mziq.com"
3. Copie o company_id da URL da requisição
4. Adicione o bloco abaixo seguindo o padrão

Parâmetros do valuation podem ser sobrescritos por empresa.
Valores não informados herdam os defaults de DEFAULT_PARAMS.
"""

# ─────────────────────────────────────────────────────────────
# DEFAULTS GLOBAIS (usados quando não sobrescritos por empresa)
# ─────────────────────────────────────────────────────────────

DEFAULT_PARAMS = {
    "cost_of_debt":     0.12,
    "terminal_growth":  0.04,
    "forecast_years":   6,
    "tax_rate":         0.34,
    "min_year":         2019,
}

# ─────────────────────────────────────────────────────────────
# REGISTRO DE EMPRESAS
# ─────────────────────────────────────────────────────────────

COMPANIES = {

    # ── Industriais ──────────────────────────────────────────

    "COGNA": {
        "ticker":       "COGN3.SA",
        "nome":         "Cogna Educação S.A.",
        "setor":        "Educação",
        "ri_url":       "https://ri.cogna.com.br",
        "company_id_mz":"e1110a12-6e58-4cb0-be24-ed1d5f18049a",
        "cvm_code":     "17973",   # código CVM correto (19615 = Grendene!)
        "shares_out":   1_833_167_226,
        "terminal_growth": 0.035,
        "cost_of_debt":    0.14,
    },

    "WEG": {
        "ticker":       "WEGE3.SA",
        "nome":         "WEG S.A.",
        "setor":        "Industrial",
        "ri_url":       "https://ri.weg.net",
        "company_id_mz":"50c1bd3e-8ac6-42d9-884f-b9d69f690602",
        "cvm_code":     "5410",    # código CVM WEG
        "shares_out":   4_197_317_998,
        "terminal_growth": 0.04,
        "cost_of_debt":    0.12,
    },

    # ── Templates para adicionar futuras empresas ─────────────

    # "VALE": {
    #     "ticker":       "VALE3.SA",
    #     "nome":         "Vale S.A.",
    #     "setor":        "Mineração",
    #     "ri_url":       "https://www.vale.com/pt/investors",
    #     "company_id_mz":"???",   # ← buscar via DevTools
    #     "shares_out":   4_500_000_000,
    #     "terminal_growth": 0.03,
    #     "cost_of_debt":    0.11,
    # },

    # "ITUB": {
    #     "ticker":       "ITUB4.SA",
    #     "nome":         "Itaú Unibanco S.A.",
    #     "setor":        "Financeiro",
    #     "ri_url":       "https://www.itau.com.br/relacoes-com-investidores",
    #     "company_id_mz":"???",
    #     "shares_out":   9_800_000_000,
    #     "terminal_growth": 0.05,
    #     "cost_of_debt":    0.10,
    # },
}


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def get_company(name: str) -> dict:
    """
    Retorna config completa de uma empresa, com defaults preenchidos.
    """
    if name not in COMPANIES:
        raise ValueError(
            f"Empresa '{name}' não encontrada. "
            f"Disponíveis: {list(COMPANIES.keys())}"
        )

    cfg = {**DEFAULT_PARAMS, **COMPANIES[name]}
    return cfg


def list_companies() -> list:
    """Retorna lista de empresas cadastradas."""
    return list(COMPANIES.keys())