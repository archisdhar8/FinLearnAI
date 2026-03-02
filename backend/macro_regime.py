"""
Macro Regime Classifier — rule-based business-cycle classification.

Classifies the economy into one of four regimes based on observable
macroeconomic indicators:

  Expansion   — Economy growing, financial conditions supportive of risk assets.
  LateCycle   — Growth decelerating, inflation / rates elevated, conditions
                tightening — typically precedes recession by 6-18 months.
  Recession   — Contraction underway, elevated unemployment, risk-off.
  Recovery    — Early rebound from recession, conditions improving.

Also produces a **continuous risk_off_probability ∈ [0, 1]** used to modulate
the equity risk premium in the expected-return model.

Theory & evidence:
  - Yield curve inversion (10Y < 3M) predicts recessions 6-18 months ahead
    (Estrella & Mishkin 1996; NY Fed probability model).
  - Rising unemployment ≥ 0.5 pp from cycle low triggers the "Sahm Rule"
    recession indicator (Sahm 2019).
  - NFCI > 0 indicates tighter-than-average financial conditions (Chicago Fed).
  - BAA-10Y spread > 3 % has historically accompanied credit stress.
  - High and rising inflation with restrictive real rates characterises late cycle.

Design:
  - Transparent, rule-based classification — every rule maps to an economic
    rationale documented inline.
  - Deterministic: same MacroSnapshot → same regime output.
  - No machine learning or stochastic elements.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MacroRegime:
    """
    Output of regime classification.

    Attributes
    ----------
    state : str
        One of ``"Expansion"``, ``"LateCycle"``, ``"Recession"``, ``"Recovery"``.
    risk_off_probability : float
        Continuous measure of financial-system stress, 0 (fully risk-on)
        to 1 (maximum risk-off).  Drives the equity risk premium adjustment.
    features : dict
        Input features used for classification (for logging / debugging).
    """
    state: str
    risk_off_probability: float
    features: dict

    def to_dict(self) -> dict:
        return {
            "state": self.state,
            "risk_off_probability": round(self.risk_off_probability, 4),
            "features": self.features,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_regime(snapshot) -> MacroRegime:
    """
    Classify the macro regime from a :class:`MacroSnapshot`.

    Decision rules are evaluated **in priority order** — the first matching
    rule wins.  See inline comments for the economic rationale of each rule.

    Parameters
    ----------
    snapshot : MacroSnapshot
        Point-in-time macro indicators (from :class:`FredClient`).

    Returns
    -------
    MacroRegime
    """
    # -- Extract features --------------------------------------------------
    slope           = snapshot.yield_curve_slope     # 10Y − 3M
    term_spread     = snapshot.term_spread_2s10s     # 10Y − 2Y
    inflation       = snapshot.cpi_yoy
    infl_trend      = snapshot.inflation_trend       # 6-month change
    unemp           = snapshot.unrate
    unemp_trend     = snapshot.unemployment_trend    # 6-month change
    real_rate       = snapshot.real_rate              # 10Y − CPI YoY
    nfci            = snapshot.nfci  if snapshot.nfci  is not None else -0.2
    baa10y          = snapshot.baa10y if snapshot.baa10y is not None else 1.8

    features = {
        "yield_curve_slope":    round(slope,       2),
        "term_spread_2s10s":    round(term_spread, 2),
        "inflation_cpi_yoy":    round(inflation,   2),
        "inflation_trend_6m":   round(infl_trend,  2),
        "unemployment":         round(unemp,       2),
        "unemployment_trend_6m":round(unemp_trend, 2),
        "real_rate":            round(real_rate,    2),
        "nfci":                 round(nfci,        2),
        "baa10y_spread":        round(baa10y,      2),
    }

    # =====================================================================
    # 1)  Risk-off probability  (continuous, 0–1)
    #     Combines multiple independent stress signals.
    # =====================================================================
    risk_off = 0.0

    # a) Inverted yield curve
    if slope < 0:
        risk_off += min(abs(slope) / 2.0, 0.30)   # up to 0.30 for deep inversion

    # b) Rising unemployment (Sahm-like)
    if unemp_trend > 0.3:
        risk_off += min(unemp_trend / 2.0, 0.25)  # up to 0.25

    # c) Tight financial conditions  (NFCI > 0 = tighter than average)
    if nfci > 0:
        risk_off += min(nfci / 1.5, 0.25)         # up to 0.25

    # d) Credit spread widening  (BAA-10Y > 2.5 % = elevated)
    if baa10y > 2.5:
        risk_off += min((baa10y - 2.5) / 3.0, 0.20)

    risk_off = min(risk_off, 1.0)

    # =====================================================================
    # 2)  State classification  (priority order — first match wins)
    # =====================================================================
    state = "Expansion"  # default

    # Rule 1  RECESSION — inverted curve  AND  rising unemployment
    #   Economic rationale: curve inversion signals future contraction;
    #   rising unemployment confirms it is underway.
    if slope < -0.2 and unemp_trend > 0.3:
        state = "Recession"

    # Rule 2  RECESSION — severe financial stress + rising unemployment
    elif nfci > 0.5 and unemp_trend > 0.2:
        state = "Recession"

    # Rule 3  RECESSION — very wide credit spreads + rising unemployment
    elif baa10y > 4.0 and unemp_trend > 0.3:
        state = "Recession"

    # Rule 4  LATE CYCLE — high / rising inflation + restrictive policy
    #   Economic rationale: Fed hiking to fight inflation compresses
    #   growth and punishes long-duration assets.
    elif (inflation > 4.0 or infl_trend > 1.0) and real_rate > 1.5:
        state = "LateCycle"

    # Rule 5  LATE CYCLE — tightening financial conditions + high rates
    elif nfci > 0.0 and real_rate > 1.0 and inflation > 3.0:
        state = "LateCycle"

    # Rule 6  RECOVERY — high unemployment but stabilising + positive slope
    #   Economic rationale: curve steepening from inversion + labour
    #   market bottoming signals early expansion.
    elif slope > -0.2 and unemp > 5.0 and abs(unemp_trend) < 0.3:
        state = "Recovery"

    # Rule 7  RECOVERY — risk-off receding + improving employment
    elif risk_off > 0.2 and unemp_trend < -0.2 and slope > 0:
        state = "Recovery"

    # Default → Expansion (no stress signals triggered)

    logger.info("Macro regime: %s  (risk_off=%.2f)", state, risk_off)

    return MacroRegime(
        state=state,
        risk_off_probability=risk_off,
        features=features,
    )
