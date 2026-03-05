import numpy as np
import pandas as pd


def calculate_cagr(series):

    start = series.iloc[0]
    end = series.iloc[-1]
    periods = len(series) - 1

    return (end / start) ** (1 / periods) - 1


def build_dre_projection(df, forecast_years=6, terminal_growth=0.03):

    df = df.sort_index()

    last_year = df.index.max()
    last_revenue = df["REVENUE"].iloc[-1]
    last_ebit_margin = (df["EBIT"] / df["REVENUE"]).mean()
    last_dep_margin = (df["DEPRECIATION"] / df["REVENUE"]).mean()

    revenue_series = df["REVENUE"]

    cagr = calculate_cagr(revenue_series)

    decay_factors = [0.85, 0.75, 0.65, 0.55, 0.45, 0.35]

    projections = []

    current_revenue = last_revenue

    for i in range(forecast_years):

        if i < len(decay_factors):
            growth = cagr * decay_factors[i]
        else:
            growth = terminal_growth

        current_revenue *= (1 + growth)

        ebit = current_revenue * last_ebit_margin
        depreciation = current_revenue * last_dep_margin
        nopat = ebit * (1 - 0.34)

        projections.append({
            "year": last_year + i + 1,
            "REVENUE": current_revenue,
            "EBIT": ebit,
            "DEPRECIATION": depreciation,
            "NOPAT": nopat
        })

    projection_df = pd.DataFrame(projections)
    projection_df.set_index("year", inplace=True)

    return projection_df