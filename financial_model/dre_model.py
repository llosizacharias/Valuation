import numpy as np
import pandas as pd


def calculate_cagr(series: pd.Series, window: int = None) -> float:
    """
    Calcula CAGR da série de receita.
    window: se fornecido, usa apenas os últimos N anos.
    """
    series = series.dropna()

    if window and len(series) > window:
        series = series.iloc[-window:]

    if len(series) < 2:
        raise ValueError("Série precisa de pelo menos 2 anos para calcular CAGR.")

    start, end = series.iloc[0], series.iloc[-1]
    periods    = len(series) - 1

    if start <= 0:
        raise ValueError(f"Receita inicial inválida para CAGR: {start:.0f}.")

    return (end / start) ** (1 / periods) - 1


def _weighted_margin(margin_series: pd.Series, recent_years: int = 3) -> float:
    """
    Margem ponderada priorizando anos recentes.
    - Se os últimos N anos forem consistentes (todos pos/neg): pesos lineares crescentes.
    - Caso contrário: pesos exponenciais com remoção de outliers (>2σ).
    """
    s = margin_series.dropna()

    if len(s) == 0:
        return 0.0
    if len(s) == 1:
        return float(s.iloc[0])

    recent       = s.iloc[-recent_years:] if len(s) >= recent_years else s
    all_positive = (recent > 0).all()
    all_negative = (recent < 0).all()

    if all_positive or all_negative:
        weights = np.arange(1, len(recent) + 1, dtype=float)
        return float(np.average(recent, weights=weights))

    std_m   = s.std()
    s_clean = s[np.abs(s - s.mean()) <= 2 * std_m] if std_m > 0 else s
    if len(s_clean) == 0:
        s_clean = s

    n       = len(s_clean)
    weights = np.array([1.5 ** i for i in range(n)], dtype=float)
    return float(np.average(s_clean, weights=weights))


def build_dre_projection(
    df,
    forecast_years: int = 6,
    terminal_growth: float = 0.03,
    tax_rate: float = 0.34,
    cagr_window: int = 4,
    margin_window: int = 3,
    # ── Overrides forward-looking ──────────────────────────────
    revenue_growth_override: float = None,
    ebit_margin_override: float = None,
):
    """
    Projeta DRE para `forecast_years` anos.

    Parâmetros de override (ambos opcionais):
      revenue_growth_override : substitui o CAGR blended calculado.
                                Use quando dados históricos não refletem
                                tendência atual (ex: empresa em turnaround).
      ebit_margin_override    : substitui a margem EBIT ponderada calculada.
                                Use quando a margem recente é mais representativa.

    Quando ativos, o modelo imprime aviso explícito para rastreabilidade.
    """
    df = df.sort_index()

    last_year    = df.index.max()
    last_revenue = df["REVENUE"].iloc[-1]

    if "EBIT" not in df.columns:
        raise ValueError("Coluna EBIT ausente no histórico.")

    if "DEPRECIATION" not in df.columns:
        print("[WARN] DEPRECIATION ausente — usando 0 na projeção.")
        df["DEPRECIATION"] = 0

    valid = df[df["REVENUE"] > 0].copy()

    ebit_margins = valid["EBIT"] / valid["REVENUE"]
    dep_margins  = valid["DEPRECIATION"] / valid["REVENUE"]

    # ── Margem EBIT ───────────────────────────────────────────
    if ebit_margin_override is not None:
        last_ebit_margin = ebit_margin_override
        print(f"[DRE] ⚠️  Margem EBIT OVERRIDE aplicado  : {last_ebit_margin:.1%}")
        print(f"[DRE]    (calculado histórico seria      : {_weighted_margin(ebit_margins, recent_years=margin_window):.1%})")
    else:
        last_ebit_margin = _weighted_margin(ebit_margins, recent_years=margin_window)
        print(f"[DRE] Margem EBIT usada na projeção     : {last_ebit_margin:.1%}")

    last_dep_margin = _weighted_margin(dep_margins.clip(lower=0), recent_years=margin_window)
    print(f"[DRE] Margem D&A  usada na projeção     : {last_dep_margin:.1%}")

    print(f"[DRE] Margens por ano:")
    for yr, em, dm in zip(valid.index, ebit_margins, dep_margins):
        print(f"       {yr}: EBIT {em:.1%}  |  D&A {dm:.1%}")

    # ── CAGR / crescimento de receita ─────────────────────────
    revenue_series = valid["REVENUE"].dropna()

    if revenue_growth_override is not None:
        cagr_used = revenue_growth_override
        cagr_full   = np.clip(calculate_cagr(revenue_series, window=None),   -0.30, 0.50)
        cagr_recent = np.clip(calculate_cagr(revenue_series, window=cagr_window), -0.30, 0.50)
        print(f"[DRE] ⚠️  CAGR Receita OVERRIDE aplicado  : {cagr_used:.1%}")
        print(f"[DRE]    (histórico completo seria       : {cagr_full:.1%})")
        print(f"[DRE]    (últimos {cagr_window} anos seria          : {cagr_recent:.1%})")
    else:
        cagr_full   = np.clip(calculate_cagr(revenue_series, window=None),       -0.30, 0.50)
        cagr_recent = np.clip(calculate_cagr(revenue_series, window=cagr_window), -0.30, 0.50)
        cagr_used   = np.clip(0.6 * cagr_recent + 0.4 * cagr_full,               -0.30, 0.50)
        print(f"[DRE] CAGR Receita — histórico completo : {cagr_full:.1%}")
        print(f"[DRE] CAGR Receita — últimos {cagr_window} anos  : {cagr_recent:.1%}")
        print(f"[DRE] CAGR Receita — usado (blended)    : {cagr_used:.1%}")

    # ── Projeção ──────────────────────────────────────────────
    decay_factors   = [0.85, 0.75, 0.65, 0.55, 0.45, 0.35]
    projections     = []
    current_revenue = last_revenue

    for i in range(forecast_years):
        growth = cagr_used * decay_factors[i] if i < len(decay_factors) else terminal_growth

        current_revenue = current_revenue * (1 + growth)
        ebit            = current_revenue * last_ebit_margin
        depreciation    = current_revenue * last_dep_margin
        nopat           = ebit * (1 - tax_rate)

        projections.append({
            "year":         last_year + i + 1,
            "REVENUE":      current_revenue,
            "EBIT":         ebit,
            "DEPRECIATION": depreciation,
            "NOPAT":        nopat,
        })

    projection_df = pd.DataFrame(projections)
    projection_df.set_index("year", inplace=True)
    return projection_df