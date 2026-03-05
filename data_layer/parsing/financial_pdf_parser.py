import re
import pdfplumber


class FinancialPDFParser:

    def __init__(self, file_path):
        self.file_path = file_path
        self.text = ""

    # ---------------------------------------------------
    # 🔹 Extrair texto completo
    # ---------------------------------------------------

    def extract(self):

        with pdfplumber.open(self.file_path) as pdf:
            for page in pdf.pages:
                self.text += page.extract_text() or ""

    # ---------------------------------------------------
    # 🔹 Normalizar número brasileiro
    # ---------------------------------------------------

    def _normalize_number(self, value_str):

        value_str = value_str.replace(".", "").replace(",", ".")
        return float(value_str)

    # ---------------------------------------------------
    # 🔹 Buscar padrão monetário
    # ---------------------------------------------------

    def _search_monetary_value(self, label_patterns):

        for pattern in label_patterns:

            regex = rf"{pattern}.*?R\$\s*([\d\.,]+)"

            match = re.search(regex, self.text, re.IGNORECASE | re.DOTALL)

            if match:
                return self._normalize_number(match.group(1))

        return 0.0

    # ---------------------------------------------------
    # 🔹 DRE
    # ---------------------------------------------------

    def extract_revenue(self):
        return self._search_monetary_value([
            r"Receita Operacional Líquida",
            r"Receita Líquida"
        ])

    def extract_ebitda(self):
        return self._search_monetary_value([
            r"EBITDA"
        ])

    def extract_net_income(self):

        return self._search_monetary_value([
            r"Lucro Líquido"
        ])

    # ---------------------------------------------------
    # 🔹 BALANÇO
    # ---------------------------------------------------

    def extract_cash(self):
        return self._search_monetary_value([
            r"Caixa e equivalentes de caixa",
            r"Caixa"
        ])

    def extract_short_term_debt(self):
        return self._search_monetary_value([
            r"Empréstimos.*?Circulante",
            r"Dívida.*?Curto Prazo"
        ])

    def extract_long_term_debt(self):
        return self._search_monetary_value([
            r"Empréstimos.*?Não Circulante",
            r"Dívida.*?Longo Prazo"
        ])

    # ---------------------------------------------------
    # 🔹 Método principal consolidado
    # ---------------------------------------------------

    def parse_financials(self):

        self.extract()

        return {
            # DRE
            "receita_milhoes": self.extract_revenue(),
            "ebitda_milhoes": self.extract_ebitda(),
            "lucro_liquido_milhoes": self.extract_net_income(),

            # Balanço
            "cash_milhoes": self.extract_cash(),
            "short_term_debt_milhoes": self.extract_short_term_debt(),
            "long_term_debt_milhoes": self.extract_long_term_debt(),
        }