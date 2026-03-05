import unicodedata
import re
from difflib import SequenceMatcher


FINANCIAL_DICTIONARY = {
    "REVENUE": [
        "receita",
        "receita liquida",
        "receita liquida de vendas",
        "net revenue",
        "sales"
    ],
    "EBIT": [
        "ebit",
        "lucro operacional",
        "resultado operacional",
        "lucro operac"
    ],
    "DEPRECIATION": [
        "depreciacao",
        "depreciacao e amortizacao"
    ],
    "CAPEX": [
        "capex",
        "investimentos",
        "imobilizado"
    ],
    "NET_DEBT": [
        "divida liquida"
    ],
    "WORKING_CAPITAL": [
        "capital de giro"
    ]
}


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


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


# =====================================================
# CLASSIFICADOR
# =====================================================

def classify_label(label, sheet=None, threshold=0.90):

    label_norm = normalize_text(label)
    sheet_norm = normalize_text(sheet) if sheet else ""

    # 🔥 BLOQUEAR LINHAS PERCENTUAIS
    if "%" in label_norm:
        return None

    if "margem" in label_norm:
        return None

    # 🔥 BLOQUEAR DRE em BP
    if "bp" in sheet_norm or "balanco" in sheet_norm:
        if any(term in label_norm for term in ["receita", "ebit"]):
            return None

    # =====================================================
    # MATCH DIRETO OU POR INÍCIO
    # =====================================================

    for category, keywords in FINANCIAL_DICTIONARY.items():

        for keyword in keywords:

            keyword_norm = normalize_text(keyword)

            if label_norm == keyword_norm:
                return category

            if label_norm.startswith(keyword_norm):
                return category

    # =====================================================
    # FUZZY MATCH MAIS RESTRITIVO
    # =====================================================

    best_match = None
    best_score = 0

    for category, keywords in FINANCIAL_DICTIONARY.items():

        for keyword in keywords:

            keyword_norm = normalize_text(keyword)
            score = similarity(label_norm, keyword_norm)

            if score > best_score:
                best_score = score
                best_match = category

    if best_score >= threshold:
        return best_match

    return None