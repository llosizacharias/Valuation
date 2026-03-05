"""
Company Structural Model
Representa o DNA econômico de uma empresa
para o modelo macro-estrutural estocástico.
"""

import numpy as np
from .parameters import (
    MAX_RESTRUCTURINGS,
    ROIC_PENALTY_PER_EVENT,
    GROWTH_PENALTY_PER_EVENT,
    SPREAD_PENALTY_PER_EVENT,
    IDIO_MULTIPLIER_AFTER_RESTRUCT,
)


class CompanyStructural:

    def __init__(
        self,
        name: str,
        revenue_0: float,
        margin_base: float,
        roic_base: float,
        growth_base: float,
        wacc_base: float,
        spread_base: float,
        debt: float,
        beta_pib: float,
        beta_juros: float,
        beta_commodities: float,
        beta_cambio: float,
        beta_credit_spread: float,
        beta_credit_reinv: float,
        sigma_idio: float,
    ):

        self.name = name

        # -------- Estrutura Base --------
        self.revenue_0 = revenue_0
        self.margin_base = margin_base
        self.roic_base = roic_base
        self.growth_base = growth_base
        self.wacc_base = wacc_base
        self.spread_base = spread_base
        self.debt_0 = debt

        # -------- Betas --------
        self.beta_pib = beta_pib
        self.beta_juros = beta_juros
        self.beta_commodities = beta_commodities
        self.beta_cambio = beta_cambio
        self.beta_credit_spread = beta_credit_spread
        self.beta_credit_reinv = beta_credit_reinv

        # -------- Risco --------
        self.sigma_idio_base = sigma_idio

        # -------- Estado Dinâmico --------
        self.reset_state()

    # ============================================================
    # Reset para nova simulação
    # ============================================================

    def reset_state(self):
        self.revenue = self.revenue_0
        self.debt = self.debt_0
        self.roic = self.roic_base
        self.growth = self.growth_base
        self.spread = self.spread_base
        self.sigma_idio = self.sigma_idio_base
        self.restruct_count = 0

    # ============================================================
    # Atualização dos drivers com base nos fatores
    # ============================================================

    def update_drivers(self, factors, credit):

        pib, juros, commodities, cambio = factors

        # Crescimento
        self.growth = (
            self.growth_base
            + self.beta_pib * pib
        )

        # Margem
        self.margin = (
            self.margin_base
            + self.beta_commodities * commodities
        )

        # Spread
        self.spread = (
            self.spread_base
            - self.beta_credit_spread * credit
        )

        # WACC
        self.wacc = (
            self.wacc_base
            + self.beta_juros * juros
            + self.spread
        )

    # ============================================================
    # Projeta FCF de um ano
    # ============================================================

    def project_one_year(self):

        # Atualiza receita
        self.revenue *= (1 + self.growth)

        # EBIT aproximado
        ebit = self.revenue * self.margin

        # Reinvestimento via ROIC
        reinvestment_rate = max(self.growth / max(self.roic, 1e-6), 0)

        reinvestment = ebit * reinvestment_rate

        fcf = ebit - reinvestment

        return fcf, ebit

    # ============================================================
    # Testa reestruturação
    # ============================================================

    def check_restructuring(self, enterprise_value, ebit):

        interest_expense = self.debt * self.spread

        icr = ebit / max(interest_expense, 1e-6)

        if (
            (enterprise_value < self.debt or icr < 1.0)
            and self.restruct_count < MAX_RESTRUCTURINGS
        ):
            self.apply_restructuring(enterprise_value)

    # ============================================================
    # Aplica reestruturação
    # ============================================================

    def apply_restructuring(self, enterprise_value):

        self.restruct_count += 1

        # Severidade baseada em EV/Dívida
        ratio = enterprise_value / max(self.debt, 1e-6)
        haircut = 1 - ratio
        haircut = np.clip(haircut, 0.3, 0.9)

        # Reduz dívida
        self.debt *= 0.6

        # Penalidades permanentes
        self.roic -= ROIC_PENALTY_PER_EVENT
        self.growth -= GROWTH_PENALTY_PER_EVENT
        self.spread += SPREAD_PENALTY_PER_EVENT
        self.sigma_idio *= IDIO_MULTIPLIER_AFTER_RESTRUCT

    # ============================================================
    # Risco idiossincrático
    # ============================================================

    def apply_idiosyncratic_shock(self):
        shock = np.random.normal(0, self.sigma_idio)
        return shock