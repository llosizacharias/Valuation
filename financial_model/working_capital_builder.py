import pandas as pd

def build_working_capital_projection(dre_projection, historical_wc):

    last_year = historical_wc.index.max()

    # -------------------------
    # Extrair dias do último ano
    # -------------------------

    revenue_last = historical_wc.loc[last_year, "REVENUE"]
    cogs_last = historical_wc.loc[last_year, "COGS"]

    dso = historical_wc.loc[last_year, "ACCOUNTS_RECEIVABLE"] / revenue_last * 365
    dio = historical_wc.loc[last_year, "INVENTORY"] / cogs_last * 365
    dpo = historical_wc.loc[last_year, "SUPPLIERS"] / cogs_last * 365

    projection = dre_projection.copy()

    # -------------------------
    # Projeção
    # -------------------------

    projection["ACCOUNTS_RECEIVABLE"] = projection["REVENUE"] * dso / 365
    projection["INVENTORY"] = projection["COGS"] * dio / 365
    projection["SUPPLIERS"] = projection["COGS"] * dpo / 365

    projection["WORKING_CAPITAL"] = (
        projection["ACCOUNTS_RECEIVABLE"]
        + projection["INVENTORY"]
        - projection["SUPPLIERS"]
    )

    projection["ΔWC"] = projection["WORKING_CAPITAL"].diff()

    return projection
