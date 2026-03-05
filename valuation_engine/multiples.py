def compute_multiples(
    enterprise_value,
    df
):
    """
    Calcula múltiplos principais.
    Usa último ano disponível.
    """

    last_year = df.index.max()

    ebitda = df.get("EBITDA")
    revenue = df.get("REVENUE")

    multiples = {}

    if ebitda is not None and ebitda.loc[last_year] != 0:
        multiples["EV/EBITDA"] = (
            enterprise_value / ebitda.loc[last_year]
        )

    if revenue is not None and revenue.loc[last_year] != 0:
        multiples["EV/Revenue"] = (
            enterprise_value / revenue.loc[last_year]
        )

    return multiples