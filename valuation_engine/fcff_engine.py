import numpy as np
import pandas as pd


def safe_mean(series):
    """Usa mediana para ser robusto a outliers (ex: 2021 com WC atípico)."""
    series = series.replace([np.inf, -np.inf], np.nan).dropna()
    if series.empty:
        return 0.0
    # Mediana é mais robusta que média para séries curtas com anos atípicos
    return float(series.median())


def build_fcff(df, tax_rate=0.34):
    """
    FCFF Histórico  = OPER_CF - CAPEX
      → usa o fluxo de caixa operacional real, que já incorpora WC e D&A
      → é a forma mais confiável e direta

    FCFF Projetado  = NOPAT + D&A - CAPEX - ΔWC
      → CAPEX projetado = CAPEX/Revenue histórico × Revenue projetada
      → ΔWC projetado   = ΔWC/Revenue (média histórica, limitada a [0%, 3%])
         O teto de 3% evita que anos excepcionais (liberação de WC) distorçam as projeções

    ✅ FIX: antes usava NOPAT como proxy de FCFF em anos projetados
    ✅ FIX: ΔWC negativo em anos de liberação de WC não deve ser propagado para projeções
    ✅ FIX: histórico agora usa OPER_CF - CAPEX (mais preciso)
    """

    df = df.copy().sort_index()

    # Identifica anos históricos vs projetados
    # Histórico = tem OPER_CF real
    has_oper_cf = "OPER_CF" in df.columns
    if has_oper_cf:
        hist_mask = df["OPER_CF"].notna() & (df["OPER_CF"] != 0)
    else:
        hist_mask = pd.Series(False, index=df.index)

    # ─────────────────────────────────────────────
    # CAPEX
    # ─────────────────────────────────────────────

    if "CAPEX" in df.columns:
        df["CAPEX"] = df["CAPEX"].abs()
        capex_hist_mask = df["CAPEX"].notna() & (df["CAPEX"] > 0)
        last_hist_capex = df.index[capex_hist_mask].max() if capex_hist_mask.any() else None
    else:
        df["CAPEX"] = 0
        capex_hist_mask = pd.Series(False, index=df.index)
        last_hist_capex = None

    # Ratio CAPEX/Revenue para anos projetados
    valid_rev = df["REVENUE"] > 0
    if capex_hist_mask.any() and (valid_rev & capex_hist_mask).any():
        capex_rev_ratio = safe_mean(
            df.loc[capex_hist_mask & valid_rev, "CAPEX"] /
            df.loc[capex_hist_mask & valid_rev, "REVENUE"]
        )
    else:
        capex_rev_ratio = 0.03  # fallback conservador

    print(f"[FCFF] CAPEX/Revenue histórico: {capex_rev_ratio:.2%}")

    # Projeta CAPEX para anos sem valor real
    for year in df.index:
        if last_hist_capex is not None and year > last_hist_capex:
            df.loc[year, "CAPEX"] = df.loc[year, "REVENUE"] * capex_rev_ratio

    # ─────────────────────────────────────────────
    # D&A (para anos projetados)
    # ─────────────────────────────────────────────

    if "DEPRECIATION" in df.columns:
        df["DEPRECIATION"] = df["DEPRECIATION"].abs()
        dep_hist_mask = df["DEPRECIATION"].notna() & (df["DEPRECIATION"] > 0)
        dep_rev_ratio = safe_mean(
            df.loc[dep_hist_mask & valid_rev, "DEPRECIATION"] /
            df.loc[dep_hist_mask & valid_rev, "REVENUE"]
        ) if (dep_hist_mask & valid_rev).any() else 0
        df["DEPRECIATION"] = df["DEPRECIATION"].fillna(df["REVENUE"] * dep_rev_ratio)
    else:
        df["DEPRECIATION"] = 0
        dep_rev_ratio = 0

    print(f"[FCFF] D&A/Revenue histórico: {dep_rev_ratio:.2%}")

    # ─────────────────────────────────────────────
    # NOPAT (para anos projetados)
    # ─────────────────────────────────────────────

    if "EBIT" not in df.columns:
        raise ValueError("EBIT não disponível para cálculo de NOPAT.")

    df["NOPAT"] = df["EBIT"] * (1 - tax_rate)

    # ─────────────────────────────────────────────
    # ΔWC para projeções
    # Estima ΔWC/Revenue histórico da DFC (método indireto):
    #   ΔWC = NOPAT + D&A - CAPEX - OPER_CF
    # Limite de 0% a 3% de revenue (crescimento requer mais WC,
    # mas anos de liberação de WC não devem ser projetados)
    # ─────────────────────────────────────────────

    wc_rev_ratio = 0.01  # padrão conservador: 1% de revenue

    if has_oper_cf and hist_mask.any():
        impl_delta_wc = (
            df.loc[hist_mask, "NOPAT"] +
            df.loc[hist_mask, "DEPRECIATION"] -
            df.loc[hist_mask, "CAPEX"] -
            df.loc[hist_mask, "OPER_CF"]
        )
        rev_hist = df.loc[hist_mask, "REVENUE"]
        valid_wc = rev_hist > 0

        if valid_wc.any():
            raw_wc_ratio = safe_mean(
                impl_delta_wc[valid_wc] / rev_hist[valid_wc]
            )
            # ✅ FIX: limita a [0%, 3%] para evitar projetar liberação de WC
            wc_rev_ratio = float(np.clip(raw_wc_ratio, 0.0, 0.03))
            print(f"[FCFF] ΔWC/Revenue implícito: {raw_wc_ratio:.2%} → usado: {wc_rev_ratio:.2%}")

    # ─────────────────────────────────────────────
    # CALCULA FCFF POR ANO
    # ─────────────────────────────────────────────

    fcff = pd.Series(index=df.index, dtype=float)

    for year in df.index:

        if hist_mask.get(year, False) and has_oper_cf:
            # ✅ HISTÓRICO: OPER_CF - CAPEX (mais direto e confiável)
            fcff[year] = df.loc[year, "OPER_CF"] - df.loc[year, "CAPEX"]

        else:
            # ✅ PROJETADO: NOPAT + D&A - CAPEX - ΔWC(ratio)
            nopat = df.loc[year, "NOPAT"]
            dep   = df.loc[year, "DEPRECIATION"]
            capex = df.loc[year, "CAPEX"]
            delta_wc = df.loc[year, "REVENUE"] * wc_rev_ratio

            fcff[year] = nopat + dep - capex - delta_wc

    n_nan = fcff.isna().sum()
    if n_nan > 0:
        print(f"[WARN] build_fcff: {n_nan} ano(s) com FCFF nulo → 0.")

    fcff = fcff.replace([np.inf, -np.inf], np.nan).fillna(0)

    # ── Suaviza outliers históricos ──────────────────────────────────
    # Anos com FCFF muito abaixo da mediana (ex: 2021 expansão WC) 
    # são substituídos pela mediana para não distorcer projeções/KPIs
    hist_fcff = fcff[hist_mask]
    if len(hist_fcff) >= 4:
        median_fcff = hist_fcff.median()
        lower_bound = median_fcff * 0.25   # < 25% da mediana = outlier
        outliers = hist_fcff[hist_fcff < lower_bound].index
        if len(outliers) > 0:
            print(f"[FCFF] Anos atípicos normalizados: {list(outliers)} → mediana R$ {median_fcff/1e9:.2f} bi")
            fcff[outliers] = median_fcff

    df["FCFF"] = fcff
    return df["FCFF"]