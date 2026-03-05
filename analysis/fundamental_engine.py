import math


class FundamentalEngine:

    def __init__(self, annual_data):
        """
        annual_data = lista de dict:
        [{'ano': 2014, 'receita': X, 'ebitda': Y, 'lucro_liquido': Z}, ...]
        """
        self.data = sorted(annual_data, key=lambda x: x["ano"])

    # -----------------------------------------
    # CAGR
    # -----------------------------------------

    def cagr(self, metric):
        start = self.data[0][metric]
        end = self.data[-1][metric]
        n = len(self.data) - 1

        if start <= 0 or n <= 0:
            return None

        return (end / start) ** (1 / n) - 1

    # -----------------------------------------
    # Margem EBITDA média
    # -----------------------------------------

    def avg_ebitda_margin(self):
        margins = []

        for row in self.data:
            if row["receita"] > 0:
                margins.append(row["ebitda"] / row["receita"])

        return sum(margins) / len(margins)

    # -----------------------------------------
    # Crescimento médio anual simples
    # -----------------------------------------

    def avg_growth(self, metric):
        growths = []

        for i in range(1, len(self.data)):
            prev = self.data[i - 1][metric]
            curr = self.data[i][metric]

            if prev > 0:
                growths.append((curr / prev) - 1)

        return sum(growths) / len(growths)

    # -----------------------------------------
    # Volatilidade do lucro
    # -----------------------------------------

    def lucro_volatility(self):
        growths = []

        for i in range(1, len(self.data)):
            prev = self.data[i - 1]["lucro_liquido"]
            curr = self.data[i]["lucro_liquido"]

            if prev > 0:
                growths.append((curr / prev) - 1)

        if not growths:
            return None

        mean = sum(growths) / len(growths)
        variance = sum((g - mean) ** 2 for g in growths) / len(growths)

        return math.sqrt(variance)

    # -----------------------------------------
    # Executar análise completa
    # -----------------------------------------

    def run_full_analysis(self):

        return {
            "cagr_receita": self.cagr("receita"),
            "cagr_lucro": self.cagr("lucro_liquido"),
            "margem_ebitda_media": self.avg_ebitda_margin(),
            "crescimento_medio_receita": self.avg_growth("receita"),
            "volatilidade_lucro": self.lucro_volatility()
        }