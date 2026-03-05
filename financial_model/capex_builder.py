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

    # Caso trimestre tipo 1Q20
    match = re.match(r"^[1-4][QT](\d{2})$", period_str)
    if match:
        year_suffix = int(match.group(1))
        return 2000 + year_suffix

    # Caso ano com letra (ex: 2025E)
    match = re.match(r"^(20\d{2})[A-Z]?$", period_str)
    if match:
        return int(match.group(1))

    return None


def build_capex_from_fixed_assets(df_long):

    df = df_long[df_long["category"] == "FIXED_ASSETS"].copy()

    if df.empty:
        return pd.Series(dtype=float)

    # 🔥 Parser robusto
    df["year"] = df["period"].apply(extract_year_from_period)

    df = df.dropna(subset=["year"])

    df["year"] = df["year"].astype(int)

    # Agrupa por ano
    annual_assets = df.groupby("year")["value"].sum().sort_index()

    # CAPEX = variação do ativo imobilizado
    capex = annual_assets.diff()

    return capex
