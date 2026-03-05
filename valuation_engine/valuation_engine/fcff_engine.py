import numpy as np
import pandas as pd


def safe_mean(series):
    series = series.replace([np.inf, -np.inf], np.nan)
    return series.dropna().mean()


def build_fcff(df, tax_rate=0.34):

    df = df.copy().sort_index()

    if "EBIT" not in df.columns:
        raise ValueError("EBIT não disponível para cálculo de NOPAT")

    # ===============================
    # 1️⃣ NOPAT
    # ===============================

    df["NOPAT"] = df["EBIT"] * (1 - tax_rate)

    # ===============================
    # 2️⃣ Depreciação
    # ===============================

    if "DEPRECIATION" in df.columns:

        df["DEPRECIATION"] = df["DEPRECIATION"].abs()

        valid_revenue = df["REVENUE"] > 0

        if valid_revenue.any():
            dep_margin = safe_mean(
                df.loc[valid_revenue, "DEPRECIATION"] /
                df.loc[valid_revenue, "REVENUE"]
            )
        else:
            dep_margin = 0

        df["DEPRECIATION"] = df["DEPRECIATION"].fillna(
            df["REVENUE"] * dep_margin
        )

    else:
        df["DEPRECIATION"] = 0

    # ===============================
    # 3️⃣ CAPEX
    # ===============================

    if "CAPEX" in df.columns:

        df["CAPEX"] = df["CAPEX"].abs()

        last_historical_year = df.index[df["CAPEX"].notna()].max()

        for year in df.index:
            if year > last_historical_year:
                df.loc[year, "CAPEX"] = df.loc[year, "DEPRECIATION"]

    else:
        df["CAPEX"] = df["DEPRECIATION"]

    # ===============================
    # 4️⃣ Working Capital
    # ===============================

    if "WORKING_CAPITAL" in df.columns:

        df["DELTA_WC"] = df["WORKING_CAPITAL"].diff()

        valid_revenue = df["REVENUE"] > 0

        if valid_revenue.any():
            wc_ratio = safe_mean(
                df.loc[valid_revenue, "DELTA_WC"] /
                df.loc[valid_revenue, "REVENUE"]
            )
        else:
            wc_ratio = 0

        df["DELTA_WC"] = df["DELTA_WC"].fillna(
            df["REVENUE"] * wc_ratio
        )

    else:
        df["DELTA_WC"] = 0

    # ===============================
    # 5️⃣ FCFF FINAL
    # ===============================

    df["FCFF"] = (
        df["NOPAT"]
        + df["DEPRECIATION"]
        - df["CAPEX"]
        - df["DELTA_WC"]
    )

    # ✅ MELHORIA: NaN vira 0 somente após log de aviso
    # Isso evita mascarar silenciosamente anos com dados faltantes
    n_nan = df["FCFF"].isna().sum()
    if n_nan > 0:
        print(f"[WARN] build_fcff: {n_nan} ano(s) com FCFF nulo substituído(s) por 0. "
              "Verifique os dados de entrada.")

    df["FCFF"] = df["FCFF"].replace([np.inf, -np.inf], np.nan).fillna(0)

    return df["FCFF"]
