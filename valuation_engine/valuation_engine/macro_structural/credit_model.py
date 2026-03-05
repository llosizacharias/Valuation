"""
Credit Model
Deriva spreads de crédito a partir dos fatores macro e regime.

O crédito é modelado como uma função linear do PIB e dos juros,
com ruído proporcional ao regime (stress = mais volátil).
"""

import numpy as np

from .parameters import (
    TIME_HORIZON,
    CREDIT_ALPHA_PIB,
    CREDIT_ALPHA_JUROS,
    CREDIT_NOISE_STD_NORMAL,
    CREDIT_NOISE_STD_STRESS,
    REGIME_NORMAL,
)


class CreditModel:

    # ============================================================
    # Computa crédito para um único período
    # ============================================================

    def _compute_credit(self, factors: np.ndarray, regime: int) -> float:
        """
        factors: array de 4 valores [PIB, JUROS, COMMODITIES, CAMBIO]
        Retorna um escalar representando o spread de crédito do período.
        """
        pib = factors[0]
        juros = factors[1]

        noise_std = (
            CREDIT_NOISE_STD_NORMAL if regime == REGIME_NORMAL
            else CREDIT_NOISE_STD_STRESS
        )

        # Crédito piora com juros altos e melhora com PIB forte
        credit = (
            CREDIT_ALPHA_PIB * pib
            + CREDIT_ALPHA_JUROS * juros
            + np.random.normal(0, noise_std)
        )

        return credit

    # ============================================================
    # Computa trajetória de crédito para uma simulação
    # ============================================================

    def compute_path(
        self,
        factors_path: np.ndarray,
        regime_path: np.ndarray
    ) -> np.ndarray:
        """
        factors_path: matriz (TIME_HORIZON x 4)
        regime_path: array de tamanho TIME_HORIZON
        Retorna array de tamanho TIME_HORIZON com spread por período.
        """
        credit_path = np.zeros(TIME_HORIZON)

        for t in range(TIME_HORIZON):
            credit_path[t] = self._compute_credit(factors_path[t], regime_path[t])

        return credit_path

    # ============================================================
    # Computa múltiplas trajetórias
    # ============================================================

    def compute_multiple_paths(
        self,
        factor_tensor: np.ndarray,
        regime_paths: np.ndarray
    ) -> np.ndarray:
        """
        factor_tensor: (n_simulations x TIME_HORIZON x 4)
        regime_paths: (n_simulations x TIME_HORIZON)
        Retorna: (n_simulations x TIME_HORIZON)
        """
        n_simulations = factor_tensor.shape[0]
        credit_tensor = np.zeros((n_simulations, TIME_HORIZON))

        for i in range(n_simulations):
            credit_tensor[i] = self.compute_path(factor_tensor[i], regime_paths[i])

        return credit_tensor
