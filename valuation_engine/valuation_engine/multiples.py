def compute_multiples(
    enterprise_value,
    df
):
    """
    Calcula múltiplos principais.
    Usa último ano disponível.
    """

    last_year = df.index.max()
    multiples = {}

    # ✅ CORREÇÃO BUG: df.get() não funciona em DataFrame — retorna sempre None
    # A forma correta é verificar se a coluna existe antes de acessar

    if "EBITDA" in df.columns:
        ebitda_val = df["EBITDA"].loc[last_year]
        if ebitda_val and ebitda_val != 0:
            multiples["EV/EBITDA"] = enterprise_value / ebitda_val

    if "REVENUE" in df.columns:
        revenue_val = df["REVENUE"].loc[last_year]
        if revenue_val and revenue_val != 0:
            multiples["EV/Revenue"] = enterprise_value / revenue_val

    return multiples
