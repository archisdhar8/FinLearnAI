"""
Tests for the macro-aware expected return model.

Verifies:
  1. Determinism (same input → same output)
  2. Output clamping
  3. Missing data fallbacks (no crashes)
  4. Macro regime validity (valid states, bounded risk_off)
  5. Multiple reversion sign correctness
  6. Portfolio return = weighted sum of stock returns
  7. Component breakdown consistency
  8. Sector yield ordering
  9. Factor overlay toggle
 10. Neutral stock ≈ market return

Run:
    cd backend
    python -m pytest tests/test_expected_return.py -v
  or:
    python tests/test_expected_return.py
"""

import unittest
import sys
from pathlib import Path

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from macro_data import MacroSnapshot, DEFAULTS
from macro_regime import classify_regime, MacroRegime
from market_return import compute_market_return
from expected_return_model import (
    ExpectedReturnModel,
    ExpectedReturnConfig,
    ExpectedReturnComponents,
    SECTOR_DIVIDEND_YIELD,
    SECTOR_EARNINGS_GROWTH,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_snapshot(**overrides) -> MacroSnapshot:
    """Create a MacroSnapshot from defaults, optionally overridden."""
    d = dict(DEFAULTS)
    d.update(overrides)
    d.setdefault("timestamp", "2025-01-01T00:00:00")
    d.setdefault("data_source", "test")
    return MacroSnapshot(**d)


def _make_stock(
    ticker="TEST",
    sector="Technology",
    valuation=50,
    fundamentals=50,
    sentiment=50,
    momentum=50,
    risk=50,
    composite_score=50.0,
    volatility_90d=20.0,
    **extra,
) -> dict:
    """Create a minimal stock dict for testing."""
    return {
        "ticker": ticker,
        "sector": sector,
        "factor_scores": {
            "valuation": valuation,
            "fundamentals": fundamentals,
            "sentiment": sentiment,
            "momentum": momentum,
            "risk": risk,
        },
        "composite_score": composite_score,
        "volatility_90d": volatility_90d,
        "current_price": extra.pop("current_price", 100.0),
        "market_cap": extra.pop("market_cap", 1e11),
        **extra,
    }


# ── Macro regime tests ──────────────────────────────────────────────────────

class TestMacroRegime(unittest.TestCase):
    """Test macro regime classification rules."""

    def test_expansion_default(self):
        """Normal/neutral conditions → Expansion."""
        snap = _make_snapshot(dgs10=4.3, dgs3mo=4.2, unrate=4.0, unrate_6m_ago=4.0)
        regime = classify_regime(snap)
        self.assertEqual(regime.state, "Expansion")
        self.assertLess(regime.risk_off_probability, 0.3)

    def test_recession_inverted_curve_rising_unemp(self):
        """Deeply inverted curve + rising unemployment → Recession."""
        snap = _make_snapshot(
            dgs10=3.5, dgs3mo=5.0,                    # −1.5 % inversion
            unrate=5.5, unrate_6m_ago=4.0,             # +1.5 pp
        )
        regime = classify_regime(snap)
        self.assertEqual(regime.state, "Recession")
        self.assertGreater(regime.risk_off_probability, 0.3)

    def test_recession_stress(self):
        """Severe NFCI tightening + rising unemployment → Recession."""
        snap = _make_snapshot(nfci=0.8, unrate=5.0, unrate_6m_ago=4.5)
        regime = classify_regime(snap)
        self.assertEqual(regime.state, "Recession")

    def test_late_cycle_high_inflation_restrictive(self):
        """High inflation + restrictive real rate → LateCycle."""
        snap = _make_snapshot(
            dgs10=7.0, dgs3mo=5.0,
            cpi_yoy=5.0, cpi_yoy_6m_ago=3.5,         # rising inflation
            unrate=4.0, unrate_6m_ago=3.8,
            nfci=-0.1,
        )
        regime = classify_regime(snap)
        self.assertEqual(regime.state, "LateCycle")

    def test_recovery(self):
        """High but stabilising unemployment + positive slope → Recovery."""
        snap = _make_snapshot(
            dgs10=3.0, dgs3mo=2.0,
            unrate=6.0, unrate_6m_ago=6.1,
        )
        regime = classify_regime(snap)
        self.assertEqual(regime.state, "Recovery")

    def test_all_states_valid(self):
        """Regime state is always one of the four valid labels."""
        scenarios = [
            {},
            {"dgs10": 2.0, "dgs3mo": 5.0, "unrate": 6.0, "unrate_6m_ago": 4.5},
            {"cpi_yoy": 6.0, "cpi_yoy_6m_ago": 3.0, "dgs10": 8.0},
            {"nfci": 1.0, "unrate": 5.5, "unrate_6m_ago": 5.0},
        ]
        valid = {"Expansion", "LateCycle", "Recession", "Recovery"}
        for kwargs in scenarios:
            snap = _make_snapshot(**kwargs)
            regime = classify_regime(snap)
            self.assertIn(regime.state, valid)
            self.assertGreaterEqual(regime.risk_off_probability, 0.0)
            self.assertLessEqual(regime.risk_off_probability, 1.0)

    def test_risk_off_bounded(self):
        """risk_off_probability must always be in [0, 1]."""
        # Extreme stress scenario
        snap = _make_snapshot(
            dgs10=2.0, dgs3mo=6.0,
            unrate=9.0, unrate_6m_ago=5.0,
            nfci=2.0, baa10y=6.0,
        )
        regime = classify_regime(snap)
        self.assertGreaterEqual(regime.risk_off_probability, 0.0)
        self.assertLessEqual(regime.risk_off_probability, 1.0)


# ── Market return tests ─────────────────────────────────────────────────────

class TestMarketReturn(unittest.TestCase):
    """Test the market expected return computation."""

    def test_basic_market_return(self):
        snap = _make_snapshot(dgs10=4.5)
        regime = MacroRegime(state="Expansion", risk_off_probability=0.0, features={})
        mr = compute_market_return(snap, regime, erp_base=0.05)
        self.assertAlmostEqual(mr.risk_free_rate, 0.045, places=3)
        self.assertGreater(mr.market_expected_return, 0.05)
        self.assertLess(mr.market_expected_return, 0.15)

    def test_stress_raises_erp(self):
        """Higher risk_off → higher ERP → higher market E[R]."""
        snap = _make_snapshot(dgs10=4.5)
        calm = compute_market_return(
            snap, MacroRegime("Expansion", 0.0, {}), erp_base=0.05,
        )
        stressed = compute_market_return(
            snap, MacroRegime("Recession", 0.8, {}), erp_base=0.05,
        )
        self.assertGreater(stressed.total_erp, calm.total_erp)

    def test_risk_free_clamped(self):
        """Unreasonable yield values should be clamped."""
        snap = _make_snapshot(dgs10=15.0)  # extremely high
        regime = MacroRegime("Expansion", 0.0, {})
        mr = compute_market_return(snap, regime)
        self.assertLessEqual(mr.risk_free_rate, 0.10)

        snap2 = _make_snapshot(dgs10=-1.0)  # negative
        mr2 = compute_market_return(snap2, regime)
        self.assertGreaterEqual(mr2.risk_free_rate, 0.005)


# ── Expected return model tests ─────────────────────────────────────────────

class TestExpectedReturnModel(unittest.TestCase):
    """Test the full expected return engine."""

    @classmethod
    def setUpClass(cls):
        """Create a model with default macro (no FRED API call)."""
        cls.config = ExpectedReturnConfig()
        cls.model = ExpectedReturnModel(config=cls.config, fred_api_key="")
        cls.model.refresh_macro()

    def test_determinism(self):
        """Same stock → identical E[R] on repeated calls."""
        stock = _make_stock(ticker="AAPL", sector="Technology", valuation=80)
        r1 = self.model.stock_expected_return(stock)
        r2 = self.model.stock_expected_return(stock)
        self.assertEqual(r1.total, r2.total)
        self.assertEqual(r1.market_return, r2.market_return)
        self.assertEqual(r1.multiple_reversion, r2.multiple_reversion)

    def test_clamping_high(self):
        """Extreme positive scores → E[R] ≤ clamp_max."""
        stock = _make_stock(
            valuation=100, fundamentals=100, sentiment=100,
            momentum=100, risk=0, composite_score=100, volatility_90d=50,
        )
        r = self.model.stock_expected_return(stock)
        self.assertLessEqual(r.total, self.config.clamp_max + 1e-9)

    def test_clamping_low(self):
        """Extreme negative scores → E[R] ≥ clamp_min."""
        stock = _make_stock(
            valuation=0, fundamentals=0, sentiment=0,
            momentum=0, risk=100, composite_score=0, volatility_90d=5,
        )
        r = self.model.stock_expected_return(stock)
        self.assertGreaterEqual(r.total, self.config.clamp_min - 1e-9)

    def test_missing_data_fallback(self):
        """Stock with only ticker + sector → no crash, valid output."""
        stock = {"ticker": "MISSING", "sector": "Other"}
        r = self.model.stock_expected_return(stock)
        self.assertIsInstance(r.total, float)
        self.assertGreaterEqual(r.total, self.config.clamp_min - 1e-9)
        self.assertLessEqual(r.total, self.config.clamp_max + 1e-9)

    def test_empty_stock(self):
        """Completely empty stock dict → no crash."""
        r = self.model.stock_expected_return({})
        self.assertIsInstance(r.total, float)

    def test_multiple_reversion_sign_cheap(self):
        """Cheap stock (high valuation score) → positive reversion."""
        stock = _make_stock(valuation=90, sector="Technology")
        r = self.model.stock_expected_return(stock)
        self.assertGreater(r.multiple_reversion, 0)

    def test_multiple_reversion_sign_expensive(self):
        """Expensive stock (low valuation score) → negative reversion."""
        stock = _make_stock(valuation=10, sector="Technology")
        r = self.model.stock_expected_return(stock)
        self.assertLess(r.multiple_reversion, 0)

    def test_multiple_reversion_zero_at_fair(self):
        """Fairly valued (score=50) → near-zero reversion."""
        stock = _make_stock(valuation=50, sector="Technology")
        r = self.model.stock_expected_return(stock)
        self.assertAlmostEqual(r.multiple_reversion, 0.0, places=4)

    def test_neutral_stock_near_market(self):
        """All-50 scores in a market-average sector → E[R] close to market return (within ±3 %).

        Note: sector must have growth/yield near market average.
        Technology (growth=12 %) would add ~5.5 % growth premium, so we use
        "Other" whose defaults are closest to market averages.
        """
        stock = _make_stock(sector="Other")
        r = self.model.stock_expected_return(stock)
        market = self.model._market.market_expected_return
        self.assertAlmostEqual(r.total, market, delta=0.03)

    def test_portfolio_weighted_sum(self):
        """Portfolio E[R] = Σ w_i × E[R_i]."""
        stocks = [
            _make_stock(ticker="A", sector="Technology", valuation=70),
            _make_stock(ticker="B", sector="Finance", valuation=40),
            _make_stock(ticker="C", sector="Healthcare", valuation=60),
        ]
        weights = {"A": 0.5, "B": 0.3, "C": 0.2}

        manual = sum(
            weights[s["ticker"]] * self.model.stock_expected_return(s).total
            for s in stocks
        )
        result = self.model.portfolio_expected_return(stocks, weights)
        self.assertAlmostEqual(result["total"], manual, places=5)

    def test_components_sum_to_total(self):
        """Sum of components = total (when not clamped)."""
        stock = _make_stock(ticker="IND", sector="Industrial", valuation=60)
        r = self.model.stock_expected_return(stock)

        component_sum = (
            r.market_return
            + r.cash_yield_premium
            + r.growth_premium
            + r.multiple_reversion
            + r.macro_adjustment
            + r.risk_adjustment
            + r.factor_tilt
        )
        # Only check when not clamped
        if self.config.clamp_min < component_sum < self.config.clamp_max:
            self.assertAlmostEqual(r.total, component_sum, places=6)

    def test_sector_yield_ordering(self):
        """Utilities (high yield) should have higher cash_yield_premium
        than Technology (low yield)."""
        util = _make_stock(ticker="UTIL", sector="Utilities")
        tech = _make_stock(ticker="TECH", sector="Technology")

        r_util = self.model.stock_expected_return(util)
        r_tech = self.model.stock_expected_return(tech)
        self.assertGreater(
            r_util.cash_yield_premium, r_tech.cash_yield_premium,
        )

    def test_factor_overlay_toggle(self):
        """Factor overlay can be disabled; tilt should be 0 when off."""
        cfg_on  = ExpectedReturnConfig(use_factor_overlay=True)
        cfg_off = ExpectedReturnConfig(use_factor_overlay=False)

        model_on  = ExpectedReturnModel(config=cfg_on, fred_api_key="")
        model_on.refresh_macro()
        model_off = ExpectedReturnModel(config=cfg_off, fred_api_key="")
        model_off.refresh_macro()

        stock = _make_stock(composite_score=80)
        r_on  = model_on.stock_expected_return(stock)
        r_off = model_off.stock_expected_return(stock)

        self.assertNotEqual(r_on.factor_tilt, 0.0)
        self.assertEqual(r_off.factor_tilt, 0.0)

    def test_high_score_beats_low_score(self):
        """A stock with uniformly high scores should have higher E[R]
        than a stock with uniformly low scores."""
        high = _make_stock(
            ticker="HI", valuation=85, fundamentals=80,
            sentiment=75, momentum=80, risk=30, composite_score=80,
        )
        low = _make_stock(
            ticker="LO", valuation=15, fundamentals=20,
            sentiment=25, momentum=20, risk=70, composite_score=20,
        )
        r_hi = self.model.stock_expected_return(high)
        r_lo = self.model.stock_expected_return(low)
        self.assertGreater(r_hi.total, r_lo.total)


# ── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
