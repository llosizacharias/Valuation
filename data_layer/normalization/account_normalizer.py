ACCOUNT_MAPPING = {
    # Receita
    "Receita Líquida": "REVENUE",
    "Net Revenue": "REVENUE",

    # EBIT
    "EBIT": "EBIT",
    "Resultado Operacional": "EBIT",

    # Lucro
    "Lucro Líquido": "NET_INCOME",
    "Net Income": "NET_INCOME",

    # Caixa
    "Caixa e Equivalentes": "CASH",
    "Cash and Cash Equivalents": "CASH",

    # Dívida CP
    "Empréstimos CP": "SHORT_TERM_DEBT",
    "Dívida Curto Prazo": "SHORT_TERM_DEBT",

    # Dívida LP
    "Empréstimos LP": "LONG_TERM_DEBT",
    "Dívida Longo Prazo": "LONG_TERM_DEBT",
}


def normalize_accounts(df):
    df = df.copy()

    new_columns = {}

    for col in df.columns:
        if col in ACCOUNT_MAPPING:
            new_columns[col] = ACCOUNT_MAPPING[col]

    df = df.rename(columns=new_columns)

    return df