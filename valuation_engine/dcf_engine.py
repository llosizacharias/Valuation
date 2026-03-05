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

    pv_fcf = sum(
        fcff[t] / ((1 + wacc) ** (t + 1))
        for t in range(periods)
    )

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