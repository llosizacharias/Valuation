import numpy as np


def project_revenue(base_revenue, growth_rate, years):
    # ✅ MELHORIA: vetorizado com numpy — mais rápido que loop
    t_array = np.arange(1, years + 1)
    return base_revenue * ((1 + growth_rate) ** t_array)


def calculate_terminal_value(last_fcf, wacc, terminal_growth):

    # ✅ CORREÇÃO: raise ValueError em vez de raise Exception (mais preciso)
    if wacc <= terminal_growth:
        raise ValueError(
            f"WACC ({wacc:.1%}) deve ser maior que crescimento na perpetuidade ({terminal_growth:.1%})"
        )

    return (last_fcf * (1 + terminal_growth)) / (wacc - terminal_growth)


def discount_cash_flows(cash_flows, wacc):
    # ✅ MELHORIA: vetorizado com numpy
    cash_flows = np.array(cash_flows)
    t_array = np.arange(1, len(cash_flows) + 1)
    return cash_flows / ((1 + wacc) ** t_array)


def build_two_stage_dcf(
    annual_data,
    wacc,
    explicit_years=5,
    growth_adjustment=0.8,
    terminal_growth=0.05
):
    """
    annual_data: lista de dicts ordenada por ano ASC.
    Cada dict deve conter: 'receita' e 'lucro_liquido'.
    """

    if len(annual_data) < 3:
        raise ValueError("Histórico insuficiente para DCF (mínimo 3 anos)")

    # ✅ CORREÇÃO BUG: verificação de chave 'lucro_liquido' antes de usar
    # Sem isso, KeyError quebra o programa silenciosamente
    for i, row in enumerate(annual_data):
        if "receita" not in row:
            raise ValueError(f"Campo 'receita' ausente no ano index {i}")
        if "lucro_liquido" not in row:
            raise ValueError(f"Campo 'lucro_liquido' ausente no ano index {i}")

    # -------------------------
    # Limpeza de dados inválidos
    # -------------------------

    annual_data = [
        x for x in annual_data
        if x["receita"] is not None and x["receita"] > 0
    ]

    if len(annual_data) < 3:
        raise ValueError("Receitas históricas insuficientes ou inválidas para DCF")

    # -------------------------
    # Dados base
    # -------------------------

    base_revenue = annual_data[-1]["receita"]
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
        raise ValueError("Não foi possível calcular crescimento histórico")

    historical_growth = np.mean(growth_rates)
    projected_growth = historical_growth * growth_adjustment

    # -------------------------
    # Margem média (proxy FCF)
    # -------------------------

    margins = [
        x["lucro_liquido"] / x["receita"]
        for x in annual_data
        if x["receita"] > 0
    ]

    avg_margin = np.mean(margins)

    # -------------------------
    # Projeção Estágio 1
    # -------------------------

    projected_revenues = project_revenue(
        base_revenue,
        projected_growth,
        explicit_years
    )

    projected_fcfs = projected_revenues * avg_margin

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

    enterprise_value = np.sum(discounted_stage1) + discounted_terminal

    return {
        "historical_growth": historical_growth,
        "projected_growth": projected_growth,
        "avg_margin": avg_margin,
        "enterprise_value": enterprise_value
    }
