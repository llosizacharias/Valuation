import re
import pdfplumber


class FinancialPDFParser:

    def __init__(self, file_path):
        self.file_path = file_path
        self.text = ""

    def extract(self):
        # ✅ MELHORIA: pdfplumber usado como context manager — fecha automaticamente
        with pdfplumber.open(self.file_path) as pdf:
            for page in pdf.pages:
                self.text += page.extract_text() or ""

    def _normalize_number(self, value_str):
        value_str = value_str.strip().replace(".", "").replace(",", ".")

        # ✅ CORREÇÃO BUG: sem try/except — qualquer string inválida causava ValueError
        try:
            return float(value_str)
        except (ValueError, TypeError):
            return None

    def _search_monetary_value(self, label_patterns):

        for pattern in label_patterns:
            regex = rf"{pattern}.*?R\$\s*([\d\.,]+)"
            match = re.search(regex, self.text, re.IGNORECASE | re.DOTALL)

            if match:
                value = self._normalize_number(match.group(1))
                if value is not None:
                    return value

        # ✅ CORREÇÃO BUG: retornava 0.0 quando não encontrava o valor
        # Isso é perigoso — faz o sistema usar receita=0, EBITDA=0 silenciosamente
        # None é mais seguro pois permite ao chamador detectar a ausência
        return None

    def extract_revenue(self):
        return self._search_monetary_value([
            r"Receita Operacional Líquida",
            r"Receita Líquida",
            r"Receita de Vendas",
        ])

    def extract_ebitda(self):
        return self._search_monetary_value([r"EBITDA", r"LAJIDA"])

    def extract_net_income(self):
        return self._search_monetary_value([
            r"Lucro Líquido",
            r"Resultado Líquido do Período",
        ])

    def extract_cash(self):
        return self._search_monetary_value([
            r"Caixa e equivalentes de caixa",
            r"Caixa e Equivalentes",
            r"Caixa",
        ])

    def extract_short_term_debt(self):
        return self._search_monetary_value([
            r"Empréstimos.*?Circulante",
            r"Dívida.*?Curto Prazo",
        ])

    def extract_long_term_debt(self):
        return self._search_monetary_value([
            r"Empréstimos.*?Não Circulante",
            r"Dívida.*?Longo Prazo",
        ])

    def parse_financials(self):

        if not self.text:
            self.extract()

        # ✅ MELHORIA: avisa sobre campos não encontrados em vez de silenciar com 0
        result = {
            "receita_milhoes":        self.extract_revenue(),
            "ebitda_milhoes":         self.extract_ebitda(),
            "lucro_liquido_milhoes":  self.extract_net_income(),
            "cash_milhoes":           self.extract_cash(),
            "short_term_debt_milhoes": self.extract_short_term_debt(),
            "long_term_debt_milhoes": self.extract_long_term_debt(),
        }

        missing = [k for k, v in result.items() if v is None]
        if missing:
            print(f"[WARN] Campos não encontrados no PDF: {missing}")

        return result
