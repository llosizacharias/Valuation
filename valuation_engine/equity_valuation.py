def calculate_equity_value(
    enterprise_value,
    net_debt,
):
    """
    Equity Value = Enterprise Value - Dívida Líquida
    (Se caixa líquido, net_debt pode ser negativo)
    """

    if enterprise_value is None:
        raise ValueError("Enterprise Value inválido")

    if net_debt is None:
        net_debt = 0

    return enterprise_value - net_debt


def calculate_fair_value_per_share(
    equity_value,
    shares_outstanding
):

    if shares_outstanding is None or shares_outstanding <= 0:
        raise ValueError("Número de ações inválido")

    return equity_value / shares_outstanding