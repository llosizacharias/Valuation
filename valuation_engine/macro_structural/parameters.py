import numpy as np

# ============================================================
# CONFIGURAÇÃO GLOBAL
# ============================================================

TIME_HORIZON = 10
G_PERPETUITY = 0.0188
N_SIMULATIONS_DEFAULT = 10000

# ============================================================
# REGIMES
# ============================================================

REGIME_NORMAL = 0
REGIME_STRESS = 1

REGIME_TRANSITION_MATRIX = np.array([
    [0.90, 0.10],
    [0.40, 0.60],
])

# ============================================================
# FATORES PRIMÁRIOS
# Ordem: [PIB, JUROS, COMMODITIES, CAMBIO]
# ============================================================

FACTOR_MEANS_NORMAL = np.array([0.02, 0.05, 0.00, 0.00])
FACTOR_STDS_NORMAL  = np.array([0.015, 0.01, 0.10, 0.08])

FACTOR_MEANS_STRESS = np.array([-0.03, 0.07, -0.20, 0.15])
FACTOR_STDS_STRESS  = np.array([0.03, 0.02, 0.15, 0.12])

CORRELATION_MATRIX_NORMAL = np.array([
    [1.0, -0.3,  0.2, -0.2],
    [-0.3, 1.0, -0.1,  0.3],
    [0.2, -0.1,  1.0, -0.4],
    [-0.2, 0.3, -0.4,  1.0],
])

CORRELATION_MATRIX_STRESS = np.array([
    [1.0, -0.6,  0.4, -0.5],
    [-0.6, 1.0, -0.3,  0.6],
    [0.4, -0.3,  1.0, -0.8],
    [-0.5, 0.6, -0.8,  1.0],
])

# ============================================================
# CRÉDITO DERIVADO
# ============================================================

CREDIT_ALPHA_PIB = 0.6
CREDIT_ALPHA_JUROS = -0.8

CREDIT_NOISE_STD_NORMAL = 0.01
CREDIT_NOISE_STD_STRESS = 0.02

# ============================================================
# REESTRUTURAÇÃO
# ============================================================

MAX_RESTRUCTURINGS = 3
ROIC_PENALTY_PER_EVENT = 0.02
GROWTH_PENALTY_PER_EVENT = 0.01
SPREAD_PENALTY_PER_EVENT = 0.01
IDIO_MULTIPLIER_AFTER_RESTRUCT = 1.3

# ============================================================
# SEGURANÇA NUMÉRICA
# ============================================================

MIN_DISCOUNT_RATE = 0.01
MAX_DISCOUNT_RATE = 0.25
MIN_TERMINAL_SPREAD = 0.005