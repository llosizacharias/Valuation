from data_layer.storage.financial_repository import FinancialRepository
from valuation_engine.wacc_model import build_wacc_structural_brazil
from valuation_engine.two_stage_dcf import build_two_stage_dcf
from valuation_engine.equity_valuation import (
    calculate_equity_value,
    calculate_fair_value_per_share
)
from valuation_engine.decision_engine import generate_decision


def main():

    # =====================================================
    # 1) LOAD DATA
    # =====================================================

    repo = FinancialRepository()

    dre_data = repo.get_annual_data(company_id=1)
    balance_data = repo.get_annual_balance(company_id=1)

    if not dre_data:
        raise Exception("DRE não encontrada")

    print("\n==============================")
    print(" DADOS FUNDAMENTAIS")
    print("==============================")

    print("\nÚltimo DRE:")
    print(dre_data[-1])

    print("\nÚltimo Balanço:")
    print(balance_data[-1] if balance_data else "Sem balanço")

    # =====================================================
    # 2) WACC ESTRUTURAL (NTNB LONGA)
    # =====================================================

    wacc_data = build_wacc_structural_brazil(
        ticker_symbol="WEGE3.SA",
        cost_of_debt=0.10,
        debt_weight=0.3,
        equity_weight=0.7,
        expected_inflation=0.04,
        anbima_token=None  # coloque token se tiver
    )

    print("\n==============================")
    print(" WACC ESTRUTURAL")
    print("==============================")

    print(f"Risk Free Real: {wacc_data['risk_free_real']:.2%}")
    print(f"Risk Free Nominal: {wacc_data['risk_free_nominal']:.2%}")
    print(f"Beta: {wacc_data['beta']:.3f}")
    print(f"Cost of Equity: {wacc_data['cost_of_equity']:.2%}")
    print(f"After-Tax Cost of Debt: {wacc_data['after_tax_cost_of_debt']:.2%}")
    print(f"WACC: {wacc_data['wacc']:.2%}")

    # =====================================================
    # 3) DCF
    # =====================================================

    dcf_result = build_two_stage_dcf(
        annual_data=dre_data,
        wacc=wacc_data["wacc"],
        explicit_years=5,
        growth_adjustment=1.0,
        terminal_growth=0.0188
    )

    print("\n==============================")
    print(" DCF RESULT")
    print("==============================")

    print(f"Historical Growth: {dcf_result['historical_growth']:.2%}")
    print(f"Projected Growth: {dcf_result['projected_growth']:.2%}")
    print(f"Average Margin: {dcf_result['avg_margin']:.2%}")
    print(f"Enterprise Value (mi): {dcf_result['enterprise_value']:,.2f}")

    # =====================================================
    # 4) EQUITY ADJUSTMENT
    # =====================================================

    net_debt = 0

    if balance_data:
        latest_balance = balance_data[-1]

        net_debt = (
            latest_balance.get("short_term_debt", 0)
            + latest_balance.get("long_term_debt", 0)
            - latest_balance.get("cash", 0)
        )

    enterprise_value_absolute = dcf_result["enterprise_value"] * 1_000_000
    net_debt_absolute = net_debt * 1_000_000

    equity_value = calculate_equity_value(
        enterprise_value_absolute,
        net_debt_absolute
    )

    shares_outstanding = 4_200_000_000

    fair_value = calculate_fair_value_per_share(
        equity_value,
        shares_outstanding
    )

    print("\n==============================")
    print(" EQUITY VALUATION")
    print("==============================")

    print(f"Enterprise Value (R$): {enterprise_value_absolute:,.0f}")
    print(f"Net Debt (R$): {net_debt_absolute:,.0f}")
    print(f"Equity Value (R$): {equity_value:,.0f}")
    print(f"Fair Value per Share (R$): {fair_value:.2f}")

    # =====================================================
    # 5) DECISION ENGINE
    # =====================================================

    decision = generate_decision(
        intrinsic_value=fair_value,
        ticker="WEGE3.SA",
        required_margin=0.25
    )

    print("\n==============================")
    print(" DECISION ANALYSIS")
    print("==============================")

    print(f"Market Price: R$ {decision['market_price']:.2f}")
    print(f"Margin of Safety: {decision['margin_of_safety'] * 100:.2f}%")
    print(f"Decision: {decision['decision']}")

    repo.close()


if __name__ == "__main__":
    main()