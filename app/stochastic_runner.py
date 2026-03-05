from valuation_engine.macro_structural.company_structural import CompanyStructural
from valuation_engine.macro_structural.monte_carlo import MonteCarloEngine


def run_stochastic_single():

    company = CompanyStructural(
        name="EmpresaModelo",
        revenue_0=1000,
        margin_base=0.20,
        roic_base=0.18,
        growth_base=0.04,
        wacc_base=0.08,
        spread_base=0.02,
        debt=500,
        beta_pib=0.6,
        beta_juros=0.4,
        beta_commodities=0.1,
        beta_cambio=0.1,
        beta_credit_spread=0.5,
        beta_credit_reinv=0.3,
        sigma_idio=0.05
    )

    engine = MonteCarloEngine(company, n_simulations=3000)

    results = engine.run()
    stats = engine.summary_statistics(results)

    print("\n=== STOCHASTIC VALUATION ===")
    print("Statistics:", stats)
    print("CVaR 5%:", engine.cvar(results))

    return results