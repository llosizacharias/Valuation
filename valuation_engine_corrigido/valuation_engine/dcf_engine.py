import numpy as np


def build_dcf(
    fcff_series,
    wacc,
    terminal_growth=0.03
):
    fcff_series = fcff_series.dropna()

    if len(fcff_series) == 0:
        raise ValueError("Série FCFF vazia")

    if wacc <= terminal_growth:
        raise ValueError("WACC deve ser maior que terminal_growth")

    fcff = fcff_series.values
    periods = len(fcff)

    # ✅ MELHORIA: vetorização com numpy — mais rápido que loop Python puro
    t_array = np.arange(1, periods + 1)
    discount_factors = (1 + wacc) ** t_array
    pv_fcf = np.sum(fcff / discount_factors)

    terminal_value = (
        fcff[-1] * (1 + terminal_growth)
        / (wacc - terminal_growth)
    )

    pv_terminal = terminal_value / ((1 + wacc) ** periods)

    enterprise_value = pv_fcf + pv_terminal

    return {
        "pv_fcf": pv_fcf,
        "terminal_value": terminal_value,
        "pv_terminal": pv_terminal,
        "enterprise_value": enterprise_value
    }
