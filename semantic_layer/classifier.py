import unicodedata
import re
from rapidfuzz import fuzz  # ✅ MELHORIA: substituído SequenceMatcher por rapidfuzz
                             # rapidfuzz é 10-100x mais rápido e já está instalado no projeto


FINANCIAL_DICTIONARY = {
    "REVENUE": [
        "receita",
        "receita liquida",
        "receita liquida de vendas",
        "receita de vendas",
        "net revenue",
        "sales",
        "faturamento",
    ],
    "EBIT": [
        "ebit",
        "lucro operacional",
        "resultado operacional",
        "lucro operac",
        "resultado antes financeiro",
    ],
    "EBITDA": [
        "ebitda",
        "lucro antes juros imposto depreciacao",
        "lajida",
    ],
    "DEPRECIATION": [
        "depreciacao",
        "depreciacao e amortizacao",
        "amortizacao",
        "d&a",
    ],
    "CAPEX": [
        "capex",
        "aquisicao de imobilizado",
        "investimentos em imobilizado",
    ],
    # ✅ CORREÇÃO BUG CRÍTICO: FIXED_ASSETS ausente do dicionário
    # O capex_builder.py filtra por category == "FIXED_ASSETS"
    # mas o classificador nunca retornava essa categoria → CAPEX nunca era calculado
    "FIXED_ASSETS": [
        "imobilizado",
        "ativo imobilizado",
        "fixed assets",
        "property plant equipment",
        "ppe",
        "ativo permanente",
    ],
    "NET_DEBT": [
        "divida liquida",
        "net debt",
        "endividamento liquido",
    ],
    "WORKING_CAPITAL": [
        "capital de giro",
        "working capital",
        "capital circulante liquido",
        "ccl",
    ],
    # ✅ MELHORIA: adicionado NET_INCOME — usado em two_stage_dcf como lucro_liquido
    "NET_INCOME": [
        "lucro liquido",
        "resultado liquido",
        "net income",
        "net profit",
        "lucro do periodo",
        "resultado do exercicio",
    ],
}

# ✅ MELHORIA: threshold como constante nomeada — fácil de ajustar
FUZZY_THRESHOLD = 85  # score de 0 a 100 (rapidfuzz usa escala diferente do SequenceMatcher)


# =====================================================
# NORMALIZAÇÃO
# =====================================================

def normalize_text(text):
    text = str(text).lower()
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# =====================================================
# CLASSIFICADOR
# =====================================================

def classify_label(label, sheet=None, threshold=FUZZY_THRESHOLD):

    label_norm = normalize_text(label)
    sheet_norm = normalize_text(sheet) if sheet else ""

    # Bloquear linhas percentuais
    if "%" in label_norm or "margem" in label_norm:
        return None

    # Bloquear DRE em balanço patrimonial
    if "bp" in sheet_norm or "balanco" in sheet_norm:
        if any(term in label_norm for term in ["receita", "ebit"]):
            return None

    # =====================================================
    # MATCH DIRETO OU POR INÍCIO
    # =====================================================

    for category, keywords in FINANCIAL_DICTIONARY.items():
        for keyword in keywords:
            keyword_norm = normalize_text(keyword)
            if label_norm == keyword_norm or label_norm.startswith(keyword_norm):
                return category

    # =====================================================
    # FUZZY MATCH com rapidfuzz
    # =====================================================

    best_match = None
    best_score = 0

    for category, keywords in FINANCIAL_DICTIONARY.items():
        for keyword in keywords:
            keyword_norm = normalize_text(keyword)

            # ✅ partial_ratio funciona melhor para labels longos que contêm a palavra-chave
            score = fuzz.partial_ratio(keyword_norm, label_norm)

            if score > best_score:
                best_score = score
                best_match = category

    if best_score >= threshold:
        return best_match

    return None
