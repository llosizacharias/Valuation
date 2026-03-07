import yfinance as yf


def fetch_current_price(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1d")

    # ✅ CORREÇÃO BUG: yfinance pode retornar DataFrame vazio se mercado fechado
    # ou ticker inválido — sem essa verificação o código quebra com IndexError
    if hist.empty:
        raise ValueError(
            f"Não foi possível obter preço para o ticker '{ticker}'. "
            "Verifique se o ticker está correto (ex: 'WEGE3.SA')."
        )

    return hist["Close"].iloc[-1]


def calculate_margin_of_safety(
    intrinsic_value,
    market_price
):
    """
    Margem de segurança percentual.
    Positiva = desconto (ação barata).
    Negativa = prêmio (ação cara).
    """
    # ✅ CORREÇÃO BUG: proteção contra divisão por zero
    if market_price <= 0:
        raise ValueError("Preço de mercado inválido (zero ou negativo)")

    return (intrinsic_value / market_price) - 1


def generate_decision(
    intrinsic_value,
    ticker,
    required_margin=0.25
):
    """
    required_margin = margem mínima exigida (ex: 0.25 = 25%)
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
