import pandas as pd
import numpy as np


# ===============================
# CAGR
# ===============================

def compute_cagr(series):
    series = series.dropna()
    if len(series) < 2:
        return np.nan

    start = series.iloc[0]
    end = series.iloc[-1]
    years = len(series) - 1

    if start <= 0:
        return np.nan

    return (end / start) ** (1 / years) - 1


# ===============================
# ROIC médio
# ===============================

def compute_average_roic(df):
    if "ROIC" not in df.columns:
        return np.nan
    return df["ROIC"].dropna().mean()


# ===============================
# Dívida Líquida / FCO
# ===============================

def compute_leverage(df):
    if "NET_DEBT" not in df.columns or "OPERATING_CASH_FLOW" not in df.columns:
        return np.nan

    latest_debt = df["NET_DEBT"].dropna().iloc[-1]
    avg_fco = df["OPERATING_CASH_FLOW"].dropna().mean()

    if avg_fco == 0:
        return np.nan

    return latest_debt / avg_fco


# ===============================
# % anos com FCO positivo
# ===============================

def compute_cashflow_consistency(df):
    if "OPERATING_CASH_FLOW" not in df.columns:
        return np.nan

    fco = df["OPERATING_CASH_FLOW"].dropna()

    if len(fco) == 0:
        return np.nan

    positive_years = (fco > 0).sum()
    return positive_years / len(fco)


# ===============================
# Margem média
# ===============================

def compute_average_margin(df):
    if "EBIT" not in df.columns or "REVENUE" not in df.columns:
        return np.nan

    margin = df["EBIT"] / df["REVENUE"]
    return margin.dropna().mean()

# ===============================
# Transformar métricas em percentil
# ===============================

def compute_percentile_rank(series):
    return series.rank(pct=True) * 100


# ===============================
# Shipyard Score
# ===============================

def compute_shipyard_score(metrics_df):

    score_df = metrics_df.copy()

    for col in score_df.columns:
        score_df[col] = compute_percentile_rank(score_df[col])

    score_df["SHIPYARD_SCORE"] = score_df.mean(axis=1)

    return score_df.sort_values("SHIPYARD_SCORE", ascending=False)