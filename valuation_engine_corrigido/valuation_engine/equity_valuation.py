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

    # ✅ MELHORIA: net_debt None → 0 (sem dívida líquida)
    if net_debt is None:
        net_debt = 0

    return enterprise_value - net_debt


def calculate_fair_value_per_share(
    equity_value,
    shares_outstanding
):
    # ✅ MELHORIA: mensagem de erro mais descritiva
    if shares_outstanding is None or shares_outstanding <= 0:
        raise ValueError(
            f"Número de ações inválido: {shares_outstanding}. "
            "Verifique se o dado foi carregado corretamente."
        )

    return equity_value / shares_outstanding
