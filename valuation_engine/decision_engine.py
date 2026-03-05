import yfinance as yf


def fetch_current_price(ticker):
    stock = yf.Ticker(ticker)
    price = stock.history(period="1d")["Close"].iloc[-1]
    return price


def calculate_margin_of_safety(
    intrinsic_value,
    market_price
):
    """
    Margem de segurança percentual.
    Positiva = desconto.
    Negativa = prêmio.
    """

    return (intrinsic_value / market_price) - 1


def generate_decision(
    intrinsic_value,
    ticker,
    required_margin=0.25
):
    """
    required_margin = margem mínima exigida (ex: 25%)
    """

    market_price = fetch_current_price(ticker)

    mos = calculate_margin_of_safety(
        intrinsic_value,
        market_price
    )

    if mos >= required_margin:
        decision = "COMPRA"
    elif mos >= 0:
        decision = "NEUTRO"
    else:
        decision = "CARO"

    return {
        "market_price": market_price,
        "intrinsic_value": intrinsic_value,
        "margin_of_safety": mos,
        "decision": decision
    }