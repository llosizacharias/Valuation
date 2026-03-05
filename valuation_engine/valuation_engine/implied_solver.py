import yfinance as yf


def fetch_market_data(ticker):
    stock = yf.Ticker(ticker)
    price = stock.history(period="1d")["Close"].iloc[-1]
    shares = stock.info.get("sharesOutstanding")

    if shares is None:
        raise ValueError("Não foi possível obter número de ações")

    market_cap = price * shares

    return {
        "price": price,
        "shares": shares,
        "market_cap": market_cap
    }


def solve_implied_growth(
    dcf_function,
    annual_data,
    wacc,
    ticker,
    explicit_years=5,
    growth_adjustment=1.0,
    g_min=0.0,
    g_max=0.08,
    tolerance=1e-5
):
    """
    Resolve crescimento perpétuo implícito dado WACC.
    """

    market_data = fetch_market_data(ticker)
    target_value = market_data["market_cap"]

    low = g_min
    high = g_max

    for _ in range(100):
        mid = (low + high) / 2

        dcf_result = dcf_function(
            annual_data=annual_data,
            wacc=wacc,
            explicit_years=explicit_years,
            growth_adjustment=growth_adjustment,
            terminal_growth=mid
        )

        ev = dcf_result["enterprise_value"] * 1_000_000  # converter milhões

        if abs(ev - target_value) < tolerance * target_value:
            return mid

        if ev > target_value:
            high = mid
        else:
            low = mid

    return mid


def solve_implied_wacc(
    dcf_function,
    annual_data,
    terminal_growth,
    ticker,
    explicit_years=5,
    growth_adjustment=1.0,
    wacc_min=0.05,
    wacc_max=0.20,
    tolerance=1e-5
):
    """
    Resolve WACC implícito dado crescimento perpétuo.
    """

    market_data = fetch_market_data(ticker)
    target_value = market_data["market_cap"]

    low = wacc_min
    high = wacc_max

    for _ in range(100):
        mid = (low + high) / 2

        if mid <= terminal_growth:
            low = mid
            continue

        dcf_result = dcf_function(
            annual_data=annual_data,
            wacc=mid,
            explicit_years=explicit_years,
            growth_adjustment=growth_adjustment,
            terminal_growth=terminal_growth
        )

        ev = dcf_result["enterprise_value"] * 1_000_000

        if abs(ev - target_value) < tolerance * target_value:
            return mid

        if ev > target_value:
            low = mid
        else:
            high = mid

    return mid