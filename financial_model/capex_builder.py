import pandas as pd
import re


def extract_year_from_period(period_str):
    """
    Converte:
    2020  -> 2020
    1Q20  -> 2020
    3T22  -> 2022
    2025E -> 2025
    """

    if pd.isna(period_str):
        return None

    period_str = str(period_str).upper().strip()

    # Caso ano completo
    if re.match(r"^20\d{2}$", period_str):
        return int(period_str)

    # Caso trimestre tipo 1Q20 ou 3T22
    match = re.match(r"^[1-4][QT](\d{2})$", period_str)
    if match:
        return 2000 + int(match.group(1))

    # Caso ano com letra (ex: 2025E)
    match = re.match(r"^(20\d{2})[A-Z]?$", period_str)
    if match:
        return int(match.group(1))

    return None


def build_capex_from_fixed_assets(df_long):

    df = df_long[df_long["category"] == "FIXED_ASSETS"].copy()

    if df.empty:
        return pd.Series(dtype=float)

    df["year"] = df["period"].apply(extract_year_from_period)
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)

    annual_assets = df.groupby("year")["value"].sum().sort_index()

    if len(annual_assets) < 2:
        print("[WARN] Menos de 2 anos de ativo imobilizado — CAPEX não pode ser calculado.")
        return pd.Series(dtype=float)

    # CAPEX = variação do ativo imobilizado
    capex = annual_assets.diff()

    # ✅ CORREÇÃO BUG: diff() pode gerar CAPEX negativo quando a empresa
    # vende ativos (desinvestimento). CAPEX negativo não faz sentido no FCF —
    # deve ser tratado como zero (sem investimento líquido naquele ano)
    capex = capex.clip(lower=0)

    # Remove o primeiro ano (sempre NaN após diff)
    capex = capex.dropna()

    return capex
