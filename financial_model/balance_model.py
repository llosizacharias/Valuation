import pandas as pd
import numpy as np


def build_balance_projection(annual_data, dre_projection):

    df = annual_data.copy().sort_index()
    hist = df.copy()

    if "WORKING_CAPITAL" not in hist.columns:
        hist["WORKING_CAPITAL"] = np.nan

    proj = dre_projection.copy()

    last_wc = hist["WORKING_CAPITAL"].dropna()

    if len(last_wc) > 0:
        last_year = last_wc.index[-1]
        revenue_last = hist.loc[last_year, "REVENUE"]

        # ✅ CORREÇÃO BUG: divisão por zero se receita for 0
        # Isso pode acontecer em anos com dados incompletos
        if revenue_last > 0:
            wc_ratio = last_wc.iloc[-1] / revenue_last
        else:
            print("[WARN] Receita zero no último ano com WC — usando wc_ratio=0.")
            wc_ratio = 0
    else:
        wc_ratio = 0

    proj["WORKING_CAPITAL"] = proj["REVENUE"] * wc_ratio

    # ✅ MELHORIA: primeiro ano da projeção conecta ao último ano histórico
    # para que o ΔWC do primeiro ano projetado faça sentido
    last_hist_wc = last_wc.iloc[-1] if len(last_wc) > 0 else 0

    wc_full = pd.concat([
        pd.Series([last_hist_wc], index=[hist.index.max()]),
        proj["WORKING_CAPITAL"]
    ])

    proj["ΔWC"] = wc_full.diff().iloc[1:]

    if "CAPEX" not in proj.columns:
        proj["CAPEX"] = 0

    return proj
