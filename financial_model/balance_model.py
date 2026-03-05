import pandas as pd
import numpy as np


def build_balance_projection(annual_data, dre_projection):

    df = annual_data.copy()
    df = df.sort_index()

    # ----------------------------
    # HISTÓRICO
    # ----------------------------

    hist = df.copy()

    # Capital de Giro histórico
    if "WORKING_CAPITAL" not in hist.columns:
        hist["WORKING_CAPITAL"] = np.nan

    # ----------------------------
    # PROJEÇÃO
    # ----------------------------

    proj = dre_projection.copy()

    last_wc = hist["WORKING_CAPITAL"].dropna()

    if len(last_wc) > 0:
        wc_ratio = (
            last_wc.iloc[-1] /
            hist.loc[last_wc.index[-1], "REVENUE"]
        )
    else:
        wc_ratio = 0

    proj["WORKING_CAPITAL"] = proj["REVENUE"] * wc_ratio

    # Variação do Capital de Giro
    proj["ΔWC"] = proj["WORKING_CAPITAL"].diff()

    # CAPEX já vem do DRE projetado
    if "CAPEX" not in proj.columns:
        proj["CAPEX"] = 0

    return proj
