import numpy as np
import pandas as pd


def calculate_cagr(series):
    series = series.dropna()

    if len(series) < 2:
        raise ValueError("Série de receita precisa de pelo menos 2 anos para calcular CAGR.")

    start = series.iloc[0]
    end = series.iloc[-1]
    periods = len(series) - 1

    # ✅ CORREÇÃO BUG: start <= 0 causa raiz de número negativo → NaN ou erro
    # Isso acontece se a empresa teve receita zero ou negativa no primeiro ano
    if start <= 0:
        raise ValueError(
            f"Receita inicial inválida para CAGR: {start}. "
            "Verifique os dados históricos."
        )

    return (end / start) ** (1 / periods) - 1


def build_dre_projection(
    df,
    forecast_years=6,
    terminal_growth=0.03,
    tax_rate=0.34,           # ✅ MELHORIA: era hardcoded 0.34 dentro do loop
):

    df = df.sort_index()

    last_year = df.index.max()
    last_revenue = df["REVENUE"].iloc[-1]

    # ✅ CORREÇÃO BUG: DEPRECIATION pode não existir no histórico
    # Sem essa verificação → KeyError travava a projeção inteira
    if "EBIT" not in df.columns:
        raise ValueError("Coluna EBIT ausente no histórico.")

    if "DEPRECIATION" not in df.columns:
        print("[WARN] DEPRECIATION ausente — usando 0 na projeção.")
        df["DEPRECIATION"] = 0

    # ✅ MELHORIA: usa apenas anos com receita válida para calcular margens
    valid = df[df["REVENUE"] > 0]

    last_ebit_margin = (valid["EBIT"] / valid["REVENUE"]).mean()
    last_dep_margin  = (valid["DEPRECIATION"] / valid["REVENUE"]).mean()

    revenue_series = df["REVENUE"].dropna()
    cagr = calculate_cagr(revenue_series)

    # ✅ MELHORIA: CAGR limitado a intervalo razoável para evitar projeções absurdas
    # Ex: empresa com crescimento histórico de 200% não projeta 200% para frente
    cagr = np.clip(cagr, -0.30, 0.50)

    decay_factors = [0.85, 0.75, 0.65, 0.55, 0.45, 0.35]

    projections = []
    current_revenue = last_revenue

    for i in range(forecast_years):

        if i < len(decay_factors):
            growth = cagr * decay_factors[i]
        else:
            growth = terminal_growth

        current_revenue = current_revenue * (1 + growth)

        ebit        = current_revenue * last_ebit_margin
        depreciation = current_revenue * last_dep_margin
        nopat       = ebit * (1 - tax_rate)

        projections.append({
            "year":         last_year + i + 1,
            "REVENUE":      current_revenue,
            "EBIT":         ebit,
            "DEPRECIATION": depreciation,
            "NOPAT":        nopat
        })

    projection_df = pd.DataFrame(projections)
    projection_df.set_index("year", inplace=True)

    return projection_df
