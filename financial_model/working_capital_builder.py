import pandas as pd


def build_working_capital_projection(dre_projection, historical_wc):

    last_year = historical_wc.index.max()

    revenue_last = historical_wc.loc[last_year, "REVENUE"]
    cogs_last    = historical_wc.loc[last_year, "COGS"] \
                   if "COGS" in historical_wc.columns else None

    # ✅ CORREÇÃO BUG: divisão por zero se receita ou COGS forem zero
    # Sem essa verificação → ZeroDivisionError travava silenciosamente

    if revenue_last is None or revenue_last <= 0:
        raise ValueError(
            f"Receita inválida no último ano histórico ({last_year}): {revenue_last}. "
            "Não é possível calcular DSO."
        )

    if cogs_last is None or cogs_last <= 0:
        print("[WARN] COGS inválido ou ausente — DIO e DPO serão zerados.")
        cogs_last = None

    # ✅ CORREÇÃO BUG: colunas podem não existir no histórico
    # Acesso direto causaria KeyError

    ar = historical_wc.get("ACCOUNTS_RECEIVABLE")
    inv = historical_wc.get("INVENTORY")
    sup = historical_wc.get("SUPPLIERS")

    dso = (ar.loc[last_year] / revenue_last * 365) if ar is not None else 0
    dio = (inv.loc[last_year] / cogs_last * 365)   if (inv is not None and cogs_last) else 0
    dpo = (sup.loc[last_year] / cogs_last * 365)   if (sup is not None and cogs_last) else 0

    projection = dre_projection.copy()

    projection["ACCOUNTS_RECEIVABLE"] = projection["REVENUE"] * dso / 365
    projection["INVENTORY"]           = projection["REVENUE"] * dio / 365  # ✅ usa REVENUE como proxy se COGS ausente
    projection["SUPPLIERS"]           = projection["REVENUE"] * dpo / 365

    projection["WORKING_CAPITAL"] = (
        projection["ACCOUNTS_RECEIVABLE"]
        + projection["INVENTORY"]
        - projection["SUPPLIERS"]
    )

    # ✅ MELHORIA: conecta ao último WC histórico para ΔWC correto no 1º ano
    last_hist_wc = (
        historical_wc["WORKING_CAPITAL"].iloc[-1]
        if "WORKING_CAPITAL" in historical_wc.columns
        else 0
    )

    wc_full = pd.concat([
        pd.Series([last_hist_wc], index=[last_year]),
        projection["WORKING_CAPITAL"]
    ])

    projection["ΔWC"] = wc_full.diff().iloc[1:]

    return projection
