import numpy as np
import pandas as pd


def clean_historical_data(
    df_annual: pd.DataFrame,
    last_historical_year: int,
    min_years: int = 3
) -> pd.DataFrame:
    """
    Limpa e valida o histórico financeiro.

    Regras:
    - Mantém apenas anos <= last_historical_year
    - Remove receitas <= 0
    - Remove inf e NaN críticos
    - Exige mínimo de min_years anos válidos
    - Usa todo histórico disponível acima do mínimo
    """

    if df_annual.empty:
        raise ValueError("DataFrame anual está vazio.")

    # 1) Cortar anos futuros
    df = df_annual[df_annual.index <= last_historical_year].copy()

    if df.empty:
        raise ValueError("Nenhum dado histórico encontrado até o ano definido.")

    # 2) Garantir colunas essenciais
    required_cols = ["REVENUE", "EBIT", "DEPRECIATION"]

    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Coluna obrigatória ausente no histórico: {col}")

    # 3) Remover receitas inválidas
    df = df[df["REVENUE"] > 0]

    # 4) Remover infinitos
    df = df.replace([np.inf, -np.inf], np.nan)

    # 5) Remover linhas críticas ausentes (Revenue e EBIT)
    df = df.dropna(subset=["REVENUE", "EBIT"])

    # 6) Ordenar por ano
    df = df.sort_index()

    # 7) Verificar número mínimo de anos
    available_years = len(df)

    if available_years < min_years:
        raise ValueError(
            f"Histórico insuficiente após limpeza. "
            f"Mínimo exigido: {min_years} anos. "
            f"Disponível: {available_years} anos."
        )

    return df