import math


def project_revenue(base_revenue, growth_rate, years):
    revenues = []
    for t in range(1, years + 1):
        rev = base_revenue * ((1 + growth_rate) ** t)
        revenues.append(rev)
    return revenues


def calculate_terminal_value(last_fcf, wacc, terminal_growth):

    if wacc <= terminal_growth:
        raise Exception("WACC deve ser maior que crescimento na perpetuidade")

    return (last_fcf * (1 + terminal_growth)) / (wacc - terminal_growth)


def discount_cash_flows(cash_flows, wacc):

    discounted = []

    for t, cf in enumerate(cash_flows, start=1):
        pv = cf / ((1 + wacc) ** t)
        discounted.append(pv)

    return discounted


def build_two_stage_dcf(
    annual_data,
    wacc,
    explicit_years=5,
    growth_adjustment=0.8,
    terminal_growth=0.05
):
    """
    annual_data: lista ordenada por ano ASC
    """

    if len(annual_data) < 3:
        raise Exception("Histórico insuficiente para DCF")

    # -------------------------
    # Limpeza de dados inválidos
    # -------------------------

    annual_data = [
        x for x in annual_data
        if x["receita"] is not None and x["receita"] > 0
    ]

    if len(annual_data) < 3:
        raise Exception("Receitas históricas insuficientes ou inválidas para DCF")

    # -------------------------
    # Dados base
    # -------------------------

    latest = annual_data[-1]
    base_revenue = latest["receita"]

    revenues = [x["receita"] for x in annual_data]

    # -------------------------
    # Crescimento histórico médio
    # -------------------------

    growth_rates = []

    for i in range(1, len(revenues)):

        if revenues[i - 1] == 0:
            continue

        g = (revenues[i] / revenues[i - 1]) - 1
        growth_rates.append(g)

    if not growth_rates:
        raise Exception("Não foi possível calcular CAGR")

    historical_growth = sum(growth_rates) / len(growth_rates)

    projected_growth = historical_growth * growth_adjustment

    # -------------------------
    # Margem média (proxy FCF)
    # -------------------------

    margins = [
        x["lucro_liquido"] / x["receita"]
        for x in annual_data
        if x["receita"] > 0
    ]

    avg_margin = sum(margins) / len(margins)

    # -------------------------
    # Projeção Estágio 1
    # -------------------------

    projected_revenues = project_revenue(
        base_revenue,
        projected_growth,
        explicit_years
    )

    projected_fcfs = [rev * avg_margin for rev in projected_revenues]

    discounted_stage1 = discount_cash_flows(projected_fcfs, wacc)

    # -------------------------
    # Terminal Value
    # -------------------------

    terminal_value = calculate_terminal_value(
        projected_fcfs[-1],
        wacc,
        terminal_growth
    )

    discounted_terminal = terminal_value / ((1 + wacc) ** explicit_years)

    # -------------------------
    # Enterprise Value
    # -------------------------

    enterprise_value = sum(discounted_stage1) + discounted_terminal

    return {
        "historical_growth": historical_growth,
        "projected_growth": projected_growth,
        "avg_margin": avg_margin,
        "enterprise_value": enterprise_value
    }