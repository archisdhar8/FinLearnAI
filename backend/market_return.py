"""
Market Expected Return Model — discount rate channel + equity risk premium.

Computes the baseline expected return for the **equity market** as a whole:

    E[R_market]  =  risk_free_rate  +  equity_risk_premium (ERP)

Theory (Gordon / DDM / CAPM):
  - The equity market return decomposes into the risk-free rate plus
    compensation for bearing systematic (market) risk.
  - The ERP is **not** constant: it rises in stress / risk-off environments
    (increased uncertainty ⟹ investors demand more compensation) and
    compresses modestly in benign / risk-on conditions.

Risk-free rate:
  - We use the **10-Year Treasury yield** as the relevant risk-free rate
    for a 3-year equity investment horizon (duration matching).
  - Converted from percentage points to decimal.

ERP adjustment by regime:
  - ``ERP_base`` ≈ 5 % reflects the long-run average (Damodaran 2024).
  - In full risk-off (``risk_off_probability = 1``), ERP rises by
    ``erp_stress_add`` (default +2 %).  In 2008 and 2020 implied ERP
    rose 2-3 % above normal.
  - In full risk-on (``risk_off_probability = 0``), ERP compresses
    by ``erp_benign_compress`` (default −0.5 %).

This **market anchor** is the starting point; individual stock expected
returns deviate from it based on fundamentals, valuation, sector, and risk.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MarketReturnEstimate:
    """
    Breakdown of the market expected return.

    All values are **annualised decimals** (0.10 = 10 %).
    """
    risk_free_rate: float
    erp_base: float
    erp_stress_adjustment: float
    total_erp: float
    market_expected_return: float
    regime_state: str
    risk_off_probability: float


def compute_market_return(
    snapshot,
    regime,
    erp_base: float = 0.05,
    erp_stress_add: float = 0.02,
    erp_benign_compress: float = 0.005,
) -> MarketReturnEstimate:
    """
    Compute the expected market return from macro state.

    Parameters
    ----------
    snapshot : MacroSnapshot
        Must expose ``dgs10`` (10-Year yield in percentage points).
    regime : MacroRegime
        Must expose ``risk_off_probability`` ∈ [0, 1] and ``state``.
    erp_base : float
        Long-run equity risk premium (default 5.0 %).
    erp_stress_add : float
        Maximum ERP increase under full risk-off (default 2.0 %).
    erp_benign_compress : float
        ERP compression under fully benign conditions (default 0.5 %).

    Returns
    -------
    MarketReturnEstimate
    """
    # Risk-free rate = 10Y yield as decimal, clamped to [0.5 %, 10 %]
    risk_free = max(0.005, min(snapshot.dgs10 / 100.0, 0.10))

    # ERP adjustment: linear interpolation across risk_off_probability
    #   risk_off = 0  →  ERP = base − benign_compress  (slight compression)
    #   risk_off = 1  →  ERP = base + stress_add       (full stress premium)
    p = regime.risk_off_probability
    erp_adj = p * erp_stress_add - (1.0 - p) * erp_benign_compress
    total_erp = erp_base + erp_adj
    total_erp = max(0.02, total_erp)            # floor at 2 %

    market_return = risk_free + total_erp

    logger.info(
        "Market return: %.3f  (RF=%.3f + ERP=%.3f | regime=%s, p_riskoff=%.2f)",
        market_return, risk_free, total_erp, regime.state, p,
    )

    return MarketReturnEstimate(
        risk_free_rate=risk_free,
        erp_base=erp_base,
        erp_stress_adjustment=erp_adj,
        total_erp=total_erp,
        market_expected_return=market_return,
        regime_state=regime.state,
        risk_off_probability=p,
    )
