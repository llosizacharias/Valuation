import pandas as pd
import re


def consolidate_to_annual(df_long):
    """
    Consolida df no formato long (period, category, value) em DataFrame anual.

    Regras:
    - Se existirem dados anuais (ex: "2022"), usa eles diretamente
    - Se só existirem trimestrais (ex: "1T22"), soma os 4 trimestres
    - Nunca mistura os dois — evita dupla contagem
    """

    if df_long.empty:
        return pd.DataFrame()

    # ✅ CORREÇÃO BUG: sem verificação de colunas → KeyError se viesse df sem "category"
    required_cols = {"period", "category", "value"}
    missing = required_cols - set(df_long.columns)
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes em df_long: {missing}")

    df = df_long.copy()
    df = df[df["category"].notna()]

    if df.empty:
        return pd.DataFrame()

    df["period"] = df["period"].astype(str).str.strip()

    # Separar anuais vs trimestrais
    mask_annual    = df["period"].str.match(r"^20\d{2}$", na=False)
    mask_quarterly = df["period"].str.match(r"^[1-4][QT]\d{2}$", na=False)

    has_annual    = mask_annual.any()
    has_quarterly = mask_quarterly.any()

    if has_annual:
        # ✅ CORREÇÃO BUG CRÍTICO: se existem dados anuais E trimestrais,
        # o código original somava AMBOS → dupla contagem de todos os valores
        # Ex: receita 2022 aparecia duplicada (dado anual + soma dos 4 trimestres)
        if has_quarterly:
            print("[WARN] Dados anuais e trimestrais encontrados — usando apenas anuais.")
        df_use = df[mask_annual].copy()
        df_use["year"] = df_use["period"].astype(int)

    elif has_quarterly:
        df_use = df[mask_quarterly].copy()

        def quarter_to_year(period):
            match = re.search(r"(\d{2})$", period)
            return 2000 + int(match.group(1)) if match else None

        df_use["year"] = df_use["period"].apply(quarter_to_year)
        df_use = df_use[df_use["year"].notna()]
        df_use["year"] = df_use["year"].astype(int)

    else:
        # Fallback: qualquer formato com 4 dígitos de ano
        def extract_year(period):
            match = re.search(r"(20\d{2})", str(period))
            return int(match.group(1)) if match else None

        df_use = df.copy()
        df_use["year"] = df_use["period"].apply(extract_year)
        df_use = df_use[df_use["year"].notna()]
        df_use["year"] = df_use["year"].astype(int)

    if df_use.empty:
        return pd.DataFrame()

    annual = (
        df_use.groupby(["year", "category"])["value"]
        .sum()
        .unstack()
        .sort_index()
    )

    # Remove anos completamente zerados
    annual = annual.loc[(annual != 0).any(axis=1)]

    return annual
