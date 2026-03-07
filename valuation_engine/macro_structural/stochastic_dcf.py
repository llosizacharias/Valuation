"""
Stochastic DCF Engine
Executa projeção estrutural estocástica de uma empresa
usando:
- fatores macro
- crédito derivado
- reestruturação dinâmica
- perpetuidade baseada em PIB histórico
"""

import numpy as np

from .parameters import (
    TIME_HORIZON,
    G_PERPETUITY,
    MIN_DISCOUNT_RATE,
    MAX_DISCOUNT_RATE,
    MIN_TERMINAL_SPREAD,
)
from .company_structural import CompanyStructural


class StochasticDCF:

    def __init__(self, company: CompanyStructural):
        self.company = company

    # ============================================================
    # Executa uma simulação completa (1 trajetória)
    # ============================================================

    def run_single_path(self, factors_path, credit_path):

        self.company.reset_state()

        discounted_fcfs = []
        discount_factors = []

        for t in range(TIME_HORIZON):

            # 1️⃣ Atualiza drivers
            self.company.update_drivers(
                factors_path[t],
                credit_path[t],
            )

            # Segurança numérica no WACC
            self.company.wacc = np.clip(
                self.company.wacc,
                MIN_DISCOUNT_RATE,
                MAX_DISCOUNT_RATE
            )

            # 2️⃣ Projeta FCF
            fcf, ebit = self.company.project_one_year()

            # 3️⃣ Desconto
            discount_factor = (1 + self.company.wacc) ** (t + 1)
            discounted_fcfs.append(fcf / discount_factor)
            discount_factors.append(discount_factor)

            # 4️⃣ Enterprise value parcial (para teste de default)
            enterprise_value_partial = sum(discounted_fcfs)

            # 5️⃣ Testa reestruturação
            self.company.check_restructuring(
                enterprise_value_partial,
                ebit
            )

        # ========================================================
        # Valor Terminal
        # ========================================================

        last_fcf = fcf

        terminal_spread = max(
            self.company.wacc - G_PERPETUITY,
            MIN_TERMINAL_SPREAD
        )

        terminal_value = (
            last_fcf * (1 + G_PERPETUITY)
        ) / terminal_spread

        terminal_discounted = terminal_value / discount_factors[-1]

        enterprise_value = sum(discounted_fcfs) + terminal_discounted

        # ========================================================
        # Equity Value
        # ========================================================

        equity_value = enterprise_value - self.company.debt

        equity_value = max(equity_value, 0)

        # ========================================================
        # Retorno Implícito
        # ========================================================

        if self.company.revenue_0 <= 0:
            return 0

        implied_return = (
            (equity_value / self.company.revenue_0) ** (1 / TIME_HORIZON)
            - 1
        )

        # ========================================================
        # Choque Idiossincrático
        # ========================================================

        implied_return += self.company.apply_idiosyncratic_shock()

        return implied_return