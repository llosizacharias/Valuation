import re


def extract_year_from_period(period):
    """
    Converte períodos como:
    1Q20 -> 2020
    2T21 -> 2021
    4Q31 -> 2031
    """

    if period is None:
        return None

    period_str = str(period)

    # Captura os últimos 2 dígitos
    match = re.search(r'(\d{2})$', period_str)

    if not match:
        return None

    year_2d = int(match.group(1))

    # Regra de século:
    # <= 30 → 2000+
    # > 30 → 1900+
    if year_2d <= 30:
        return 2000 + year_2d
    else:
        return 1900 + year_2d
