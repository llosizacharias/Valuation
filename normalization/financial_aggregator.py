import pandas as pd
import re


def consolidate_to_annual(df_long):

    df = df_long.copy()

    # ---------------------------------------------------------
    # 1) REMOVER NÃO CLASSIFICADOS
    # ---------------------------------------------------------

    df = df[df["category"].notna()]

    # ---------------------------------------------------------
    # 2) EXTRAIR ANO
    # ---------------------------------------------------------

    def extract_year(period):

        period = str(period)

        match_year = re.search(r"(20\d{2})", period)

        if match_year:
            return int(match_year.group(1))

        return None

    df["year"] = df["period"].apply(extract_year)

    df = df[df["year"].notna()]
    df["year"] = df["year"].astype(int)

    # ---------------------------------------------------------
    # 3) CONSOLIDAR
    # ---------------------------------------------------------

    annual = (
        df.groupby(["year", "category"])["value"]
        .sum()
        .unstack()
    )

    annual = annual.sort_index()

    # ---------------------------------------------------------
    # 4) REMOVER ANOS COMPLETAMENTE ZERADOS
    # ---------------------------------------------------------

    annual = annual.loc[(annual != 0).any(axis=1)]

    return annual