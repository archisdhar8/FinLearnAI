"""
Genetic-Algorithm ETF Portfolio Optimizer (Option B)

Expanded version of the original ga_etf_allocator.py with:
  - 25 ETF universe (core + thematic)
  - Constraint-aware GA (required ETFs get minimum weight guarantees)
  - Monte Carlo simulation using a proper covariance matrix
  - Sharpe ratio in metrics

Public API:
  optimize_etf_portfolio(answers, required_etfs, simulate_params) -> dict
"""

import math
import random
from typing import Dict, List, Tuple, Any, Optional

import numpy as np


# ---------------------------------------------------------------------------
# Full ETF universe (25 ETFs matching the frontend)
# ---------------------------------------------------------------------------

ETF_UNIVERSE: List[Dict[str, Any]] = [
    # Core US equity
    {"ticker": "VTI",  "name": "Vanguard Total Stock Market",        "asset_class": "equity", "sub_class": "us_broad",  "category": "Core",       "exp_return": 0.105, "volatility": 0.155, "expense_ratio": 0.0003},
    {"ticker": "VOO",  "name": "Vanguard S&P 500",                   "asset_class": "equity", "sub_class": "us_large",  "category": "Core",       "exp_return": 0.102, "volatility": 0.148, "expense_ratio": 0.0003},
    {"ticker": "VUG",  "name": "Vanguard Growth",                    "asset_class": "equity", "sub_class": "us_growth", "category": "Core",       "exp_return": 0.121, "volatility": 0.182, "expense_ratio": 0.0004},
    {"ticker": "VTV",  "name": "Vanguard Value",                     "asset_class": "equity", "sub_class": "us_value",  "category": "Core",       "exp_return": 0.095, "volatility": 0.140, "expense_ratio": 0.0004},

    # Tech / Growth
    {"ticker": "QQQ",  "name": "Invesco Nasdaq 100",                 "asset_class": "equity", "sub_class": "us_tech",   "category": "Growth",     "exp_return": 0.145, "volatility": 0.205, "expense_ratio": 0.0020},

    # International
    {"ticker": "VXUS", "name": "Vanguard Total International",       "asset_class": "equity", "sub_class": "intl",      "category": "Core",       "exp_return": 0.068, "volatility": 0.160, "expense_ratio": 0.0007},
    {"ticker": "VEA",  "name": "Vanguard Developed Markets",         "asset_class": "equity", "sub_class": "intl_dev",  "category": "Core",       "exp_return": 0.072, "volatility": 0.155, "expense_ratio": 0.0005},
    {"ticker": "VWO",  "name": "Vanguard Emerging Markets",          "asset_class": "equity", "sub_class": "intl_em",   "category": "Core",       "exp_return": 0.085, "volatility": 0.220, "expense_ratio": 0.0008},

    # Bonds
    {"ticker": "BND",  "name": "Vanguard Total Bond",                "asset_class": "bond",   "sub_class": "us_agg",    "category": "Core",       "exp_return": 0.045, "volatility": 0.055, "expense_ratio": 0.0003},
    {"ticker": "AGG",  "name": "iShares Core US Aggregate Bond",     "asset_class": "bond",   "sub_class": "us_agg",    "category": "Core",       "exp_return": 0.043, "volatility": 0.052, "expense_ratio": 0.0003},
    {"ticker": "TLT",  "name": "iShares 20+ Year Treasury",          "asset_class": "bond",   "sub_class": "us_lt",     "category": "Core",       "exp_return": 0.052, "volatility": 0.140, "expense_ratio": 0.0015},
    {"ticker": "TIP",  "name": "iShares TIPS Bond",                  "asset_class": "bond",   "sub_class": "tips",      "category": "Inflation",  "exp_return": 0.040, "volatility": 0.065, "expense_ratio": 0.0019},

    # Thematic / Sector
    {"ticker": "ICLN", "name": "iShares Global Clean Energy",        "asset_class": "equity", "sub_class": "thematic",  "category": "Thematic",   "exp_return": 0.110, "volatility": 0.280, "expense_ratio": 0.0040},
    {"ticker": "VHT",  "name": "Vanguard Health Care",               "asset_class": "equity", "sub_class": "sector",    "category": "Thematic",   "exp_return": 0.115, "volatility": 0.145, "expense_ratio": 0.0010},
    {"ticker": "VNQ",  "name": "Vanguard Real Estate",               "asset_class": "equity", "sub_class": "reit",      "category": "Thematic",   "exp_return": 0.090, "volatility": 0.180, "expense_ratio": 0.0012},
    {"ticker": "SCHD", "name": "Schwab US Dividend Equity",          "asset_class": "equity", "sub_class": "dividend",  "category": "Thematic",   "exp_return": 0.108, "volatility": 0.135, "expense_ratio": 0.0006},
    {"ticker": "BOTZ", "name": "Global X Robotics & AI",             "asset_class": "equity", "sub_class": "thematic",  "category": "Thematic",   "exp_return": 0.135, "volatility": 0.250, "expense_ratio": 0.0068},
    {"ticker": "ARKK", "name": "ARK Innovation",                     "asset_class": "equity", "sub_class": "thematic",  "category": "Thematic",   "exp_return": 0.150, "volatility": 0.350, "expense_ratio": 0.0075},
    {"ticker": "XLF",  "name": "Financial Select Sector SPDR",       "asset_class": "equity", "sub_class": "sector",    "category": "Thematic",   "exp_return": 0.098, "volatility": 0.185, "expense_ratio": 0.0009},
    {"ticker": "XLE",  "name": "Energy Select Sector SPDR",          "asset_class": "equity", "sub_class": "sector",    "category": "Thematic",   "exp_return": 0.085, "volatility": 0.250, "expense_ratio": 0.0009},
    {"ticker": "SOXX", "name": "iShares Semiconductor",              "asset_class": "equity", "sub_class": "thematic",  "category": "Thematic",   "exp_return": 0.180, "volatility": 0.280, "expense_ratio": 0.0035},
    {"ticker": "IBB",  "name": "iShares Biotechnology",              "asset_class": "equity", "sub_class": "thematic",  "category": "Thematic",   "exp_return": 0.105, "volatility": 0.220, "expense_ratio": 0.0044},
    {"ticker": "TAN",  "name": "Invesco Solar",                      "asset_class": "equity", "sub_class": "thematic",  "category": "Thematic",   "exp_return": 0.120, "volatility": 0.320, "expense_ratio": 0.0067},
    {"ticker": "LIT",  "name": "Global X Lithium & Battery",         "asset_class": "equity", "sub_class": "thematic",  "category": "Thematic",   "exp_return": 0.140, "volatility": 0.300, "expense_ratio": 0.0075},
    {"ticker": "HACK", "name": "ETFMG Prime Cyber Security",         "asset_class": "equity", "sub_class": "thematic",  "category": "Thematic",   "exp_return": 0.125, "volatility": 0.200, "expense_ratio": 0.0060},
    {"ticker": "BLOK", "name": "Amplify Blockchain",                 "asset_class": "equity", "sub_class": "thematic",  "category": "Thematic",   "exp_return": 0.110, "volatility": 0.350, "expense_ratio": 0.0071},
]

TICKERS = [etf["ticker"] for etf in ETF_UNIVERSE]
_TICKER_TO_IDX = {etf["ticker"]: i for i, etf in enumerate(ETF_UNIVERSE)}


# ---------------------------------------------------------------------------
# Heuristic correlation matrix (richer than original)
# ---------------------------------------------------------------------------

# Correlation tiers by sub_class pairs
_CORR_SAME_SUBCLASS = 0.85
_CORR_SAME_ASSET = 0.65
_CORR_EQUITY_THEMATIC = 0.55
_CORR_CROSS_ASSET = 0.15          # equity vs bond baseline
_CORR_BOND_REIT = 0.25
_CORR_DEFAULT = 0.40


def _build_covariance_matrix() -> np.ndarray:
    """Build a heuristic covariance matrix with richer correlation structure."""
    n = len(ETF_UNIVERSE)
    vols = np.array([etf["volatility"] for etf in ETF_UNIVERSE])
    corr = np.eye(n)

    asset_classes = [etf["asset_class"] for etf in ETF_UNIVERSE]
    sub_classes = [etf["sub_class"] for etf in ETF_UNIVERSE]

    for i in range(n):
        for j in range(i + 1, n):
            ac_i, ac_j = asset_classes[i], asset_classes[j]
            sc_i, sc_j = sub_classes[i], sub_classes[j]

            if sc_i == sc_j:
                rho = _CORR_SAME_SUBCLASS
            elif ac_i == ac_j == "equity":
                # Thematic ETFs correlate less with broad core
                if "thematic" in (sc_i, sc_j):
                    rho = _CORR_EQUITY_THEMATIC
                else:
                    rho = _CORR_SAME_ASSET
            elif ac_i == ac_j == "bond":
                rho = _CORR_SAME_ASSET
            elif ("reit" in (sc_i, sc_j)) and ("bond" == ac_i or "bond" == ac_j):
                rho = _CORR_BOND_REIT
            elif ac_i != ac_j:
                rho = _CORR_CROSS_ASSET
            else:
                rho = _CORR_DEFAULT

            corr[i, j] = corr[j, i] = rho

    return np.outer(vols, vols) * corr


_COV = _build_covariance_matrix()
_EXP_RETURNS = np.array([etf["exp_return"] for etf in ETF_UNIVERSE])
_EXPENSES = np.array([etf["expense_ratio"] for etf in ETF_UNIVERSE])
_IS_EQUITY = np.array([1.0 if etf["asset_class"] == "equity" else 0.0 for etf in ETF_UNIVERSE])


# ---------------------------------------------------------------------------
# Risk score from questionnaire
# ---------------------------------------------------------------------------

def _compute_risk_score(answers: Dict[str, Any]) -> float:
    """Map questionnaire answers to a continuous risk score in [0, 1]."""
    time_horizon = int(answers.get("time_horizon_years", 10))
    risk_tol = int(answers.get("risk_tolerance", 3))
    drawdown_tol = int(answers.get("drawdown_tolerance", risk_tol))
    knowledge = int(answers.get("investment_knowledge", 3))
    income_stability = int(answers.get("income_stability", 3))
    goal = str(answers.get("primary_goal", "balanced"))

    def norm(x: int, lo: int = 1, hi: int = 5) -> float:
        x = max(lo, min(hi, x))
        return (x - lo) / (hi - lo)

    risk_tol_n = norm(risk_tol)
    drawdown_n = norm(drawdown_tol)
    knowledge_n = norm(knowledge)
    income_stab_n = norm(income_stability)

    if time_horizon <= 3:
        horizon_n = 0.1
    elif time_horizon <= 5:
        horizon_n = 0.25
    elif time_horizon <= 10:
        horizon_n = 0.5
    elif time_horizon <= 20:
        horizon_n = 0.75
    else:
        horizon_n = 0.9

    goal_map = {
        "capital_preservation": 0.1,
        "income": 0.25,
        "balanced": 0.5,
        "growth": 0.75,
        "max_growth": 0.9,
    }
    goal_n = goal_map.get(goal, 0.5)

    score = (
        0.25 * risk_tol_n
        + 0.20 * drawdown_n
        + 0.20 * horizon_n
        + 0.15 * goal_n
        + 0.10 * knowledge_n
        + 0.10 * income_stab_n
    )
    return max(0.0, min(1.0, float(score)))


def _target_equity_weight(risk_score: float) -> float:
    """Conservative ~20% equity → Aggressive ~95% equity."""
    return 0.20 + 0.75 * risk_score


def _risk_profile_label(risk_score: float) -> str:
    if risk_score < 0.25:
        return "Conservative"
    elif risk_score < 0.45:
        return "Moderate"
    elif risk_score < 0.60:
        return "Balanced"
    elif risk_score < 0.78:
        return "Growth"
    else:
        return "Aggressive"


# ---------------------------------------------------------------------------
# GA internals
# ---------------------------------------------------------------------------

def _project_to_simplex(weights: np.ndarray) -> np.ndarray:
    """Project an arbitrary vector onto the probability simplex (sum=1, all>=0)."""
    if np.all(weights == 0):
        return np.ones_like(weights) / len(weights)
    v = np.sort(weights)[::-1]
    cssv = np.cumsum(v)
    rho = np.nonzero(v * np.arange(1, len(v) + 1) > (cssv - 1))[0][-1]
    theta = (cssv[rho] - 1) / (rho + 1.0)
    w = np.maximum(weights - theta, 0)
    s = w.sum()
    if s <= 0:
        return np.ones_like(w) / len(w)
    return w / s


def _enforce_constraints(
    w: np.ndarray,
    min_weights: Optional[np.ndarray] = None,
) -> np.ndarray:
    """
    Ensure minimum weight constraints then re-normalise to sum=1.

    For required ETFs the GA must allocate at least min_weights[i].
    The remaining budget is distributed among all positions proportionally.
    """
    if min_weights is None:
        return _project_to_simplex(w)

    w = np.maximum(w, 0.0)
    # Clip any position below its floor up to the floor
    w = np.maximum(w, min_weights)
    s = w.sum()
    if s <= 0:
        return np.ones_like(w) / len(w)
    return w / s


def _portfolio_metrics(w: np.ndarray) -> Tuple[float, float, float]:
    """Return (expected_return, volatility, expense_ratio)."""
    er = float(w @ _EXP_RETURNS)
    var = float(w @ _COV @ w)
    vol = math.sqrt(max(var, 0.0))
    exp_ratio = float(w @ _EXPENSES)
    return er, vol, exp_ratio


def _fitness(
    w: np.ndarray,
    risk_score: float,
    equity_target: float,
    min_weights: Optional[np.ndarray] = None,
    lambda_risk: float = 2.0,
    lambda_expense: float = 10.0,
    lambda_equity: float = 8.0,
    lambda_concentration: float = 1.5,
) -> float:
    """
    Fitness function — higher is better.

    Penalises:
      - Risk (volatility) scaled by risk aversion
      - High expense ratios
      - Deviation from target equity weight
      - Over-concentration (HHI)
    """
    w = _enforce_constraints(w, min_weights)
    er, vol, exp_ratio = _portfolio_metrics(w)

    equity_weight = float(w @ _IS_EQUITY)
    equity_penalty = abs(equity_weight - equity_target)

    risk_aversion = 1.5 - risk_score  # [0.5, 1.5]

    # Herfindahl–Hirschman Index penalises concentration
    hhi = float(np.sum(w ** 2))

    utility = (
        er
        - lambda_risk * risk_aversion * vol
        - lambda_expense * exp_ratio
        - lambda_equity * equity_penalty
        - lambda_concentration * hhi
    )
    return float(utility)


def _run_ga(
    risk_score: float,
    min_weights: Optional[np.ndarray] = None,
    population_size: int = 120,
    generations: int = 120,
    mutation_rate: float = 0.30,
    crossover_rate: float = 0.75,
    random_seed: int = 42,
) -> np.ndarray:
    """Run a real-valued GA to optimise ETF weights with optional constraints."""
    rng = np.random.RandomState(random_seed)
    py_rng = random.Random(random_seed)
    n = len(ETF_UNIVERSE)
    equity_target = _target_equity_weight(risk_score)

    # Bias initialisation toward core ETFs
    base_bias = np.array(
        [1.5 if etf["category"] == "Core" else 0.8 for etf in ETF_UNIVERSE],
        dtype=float,
    )

    def random_individual() -> np.ndarray:
        raw = rng.rand(n) * base_bias
        w = _project_to_simplex(raw)
        return _enforce_constraints(w, min_weights)

    population = [random_individual() for _ in range(population_size)]
    best_individual = None
    best_fitness = -1e9

    for _gen in range(generations):
        fitnesses = [
            _fitness(ind, risk_score, equity_target, min_weights) for ind in population
        ]

        for ind, fit in zip(population, fitnesses):
            if fit > best_fitness:
                best_fitness = fit
                best_individual = ind.copy()

        def select_one() -> np.ndarray:
            i, j = rng.randint(0, population_size, size=2)
            return population[i] if fitnesses[i] > fitnesses[j] else population[j]

        new_population: List[np.ndarray] = []

        while len(new_population) < population_size:
            p1 = select_one()
            p2 = select_one()

            if py_rng.random() < crossover_rate:
                alpha = rng.uniform(0.2, 0.8)
                c1 = alpha * p1 + (1 - alpha) * p2
                c2 = alpha * p2 + (1 - alpha) * p1
            else:
                c1, c2 = p1.copy(), p2.copy()

            for child in (c1, c2):
                if py_rng.random() < mutation_rate:
                    noise = rng.normal(0, 0.04, size=n)
                    child += noise
                child[:] = _enforce_constraints(child, min_weights)

            new_population.append(c1)
            if len(new_population) < population_size:
                new_population.append(c2)

        # Elitism
        if best_individual is not None:
            new_population[0] = best_individual.copy()

        population = new_population

    if best_individual is None:
        best_individual = population[0]
    return _enforce_constraints(best_individual, min_weights)


# ---------------------------------------------------------------------------
# Monte Carlo simulation (proper covariance)
# ---------------------------------------------------------------------------

def _run_monte_carlo(
    weights_pct: Dict[str, float],
    initial_investment: float = 10000,
    monthly_contribution: float = 500,
    years: int = 20,
    num_simulations: int = 1000,
    random_seed: int = 123,
) -> Dict[str, Any]:
    """
    Monte Carlo simulation using the full covariance matrix.

    Returns percentile paths (10/25/50/75/90) and probability milestones.
    """
    rng = np.random.RandomState(random_seed)

    # Build weight vector aligned with ETF_UNIVERSE
    n = len(ETF_UNIVERSE)
    w = np.zeros(n)
    for ticker, pct in weights_pct.items():
        idx = _TICKER_TO_IDX.get(ticker)
        if idx is not None:
            w[idx] = pct / 100.0

    # Portfolio expected return & volatility from covariance
    port_er = float(w @ _EXP_RETURNS)
    port_var = float(w @ _COV @ w)
    port_vol = math.sqrt(max(port_var, 0.0))

    # Simulate using GBM log-normal model
    all_paths = np.zeros((num_simulations, years + 1))
    all_paths[:, 0] = initial_investment

    annual_contribution = monthly_contribution * 12
    drift = port_er - 0.5 * port_vol ** 2

    for sim in range(num_simulations):
        value = initial_investment
        for yr in range(1, years + 1):
            z = rng.normal()
            annual_return = math.exp(drift + port_vol * z) - 1.0
            value = value * (1 + annual_return) + annual_contribution
            value = max(0.0, value)
            all_paths[sim, yr] = value

    # Compute percentiles at each year
    years_arr = list(range(years + 1))
    p10  = [float(np.percentile(all_paths[:, yr], 10)) for yr in years_arr]
    p25  = [float(np.percentile(all_paths[:, yr], 25)) for yr in years_arr]
    p50  = [float(np.percentile(all_paths[:, yr], 50)) for yr in years_arr]
    p75  = [float(np.percentile(all_paths[:, yr], 75)) for yr in years_arr]
    p90  = [float(np.percentile(all_paths[:, yr], 90)) for yr in years_arr]

    final_values = all_paths[:, -1]

    return {
        "years": years_arr,
        "percentile10": p10,
        "percentile25": p25,
        "median": p50,
        "percentile75": p75,
        "percentile90": p90,
        "final_median": round(p50[-1], 2),
        "final_p10": round(p10[-1], 2),
        "final_p90": round(p90[-1], 2),
        "probability_500k": round(float(np.mean(final_values >= 500_000) * 100), 1),
        "probability_1m": round(float(np.mean(final_values >= 1_000_000) * 100), 1),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

MAX_HOLDINGS = 5  # Maximum ETFs in the final portfolio (excluding required picks)


def optimize_etf_portfolio(
    answers: Dict[str, Any],
    required_etfs: Optional[List[str]] = None,
    simulate: Optional[Dict[str, Any]] = None,
    max_holdings: int = MAX_HOLDINGS,
) -> Dict[str, Any]:
    """
    Full pipeline: risk profile → GA optimization → metrics → optional Monte Carlo.

    Parameters
    ----------
    answers : dict
        Questionnaire responses (time_horizon_years, risk_tolerance, etc.)
    required_etfs : list[str], optional
        ETF tickers the user wants included (minimum 3% each).
    simulate : dict, optional
        {"initial_investment": 10000, "monthly_contribution": 500, "years": 20}
    max_holdings : int
        Maximum number of ETFs in the final portfolio.  Required ETFs always
        count toward this cap but are never dropped.

    Returns
    -------
    dict with keys: risk_score, profile, allocation, metrics, simulation (optional)
    """
    risk_score = _compute_risk_score(answers)
    profile = _risk_profile_label(risk_score)

    # Build minimum weight constraints for required ETFs
    n = len(ETF_UNIVERSE)
    min_weights = np.zeros(n)
    required_set = set((t.upper() for t in (required_etfs or [])))
    if required_etfs:
        min_per_required = max(0.03, 0.15 / max(len(required_etfs), 1))
        for ticker in required_etfs:
            idx = _TICKER_TO_IDX.get(ticker.upper())
            if idx is not None:
                min_weights[idx] = min_per_required

    # Run GA
    raw_weights = _run_ga(
        risk_score=risk_score,
        min_weights=min_weights if required_etfs else None,
    )

    # Convert to percentage dict
    raw_alloc = {t: float(w * 100.0) for t, w in zip(TICKERS, raw_weights)}

    # ── Cap to max_holdings ──────────────────────────────────────────────
    # 1. Always keep required ETFs
    # 2. Fill remaining slots with the highest-weighted ETFs from the GA
    sorted_by_weight = sorted(raw_alloc.items(), key=lambda x: x[1], reverse=True)

    kept: Dict[str, float] = {}
    for t in required_set:
        if t in raw_alloc:
            kept[t] = raw_alloc[t]

    remaining_slots = max_holdings - len(kept)
    for t, w in sorted_by_weight:
        if t in kept:
            continue
        if remaining_slots <= 0:
            break
        kept[t] = w
        remaining_slots -= 1

    # Re-normalise to 100%
    total = sum(kept.values())
    if total <= 0:
        equal = 100.0 / max_holdings
        kept = dict(sorted_by_weight[:max_holdings])
        total = sum(kept.values()) or 1.0

    allocation = {t: round((w / total) * 100.0, 2) for t, w in kept.items()}

    # Correct rounding drift
    drift = 100.0 - sum(allocation.values())
    if allocation and abs(drift) > 0.01:
        largest = max(allocation, key=allocation.get)  # type: ignore
        allocation[largest] = round(allocation[largest] + drift, 2)

    # Compute portfolio-level metrics
    w_vec = np.zeros(n)
    for t, pct in allocation.items():
        idx = _TICKER_TO_IDX.get(t)
        if idx is not None:
            w_vec[idx] = pct / 100.0

    er, vol, exp_ratio = _portfolio_metrics(w_vec)
    equity_pct = float(w_vec @ _IS_EQUITY) * 100.0
    sharpe = (er - 0.045) / vol if vol > 0 else 0.0  # risk-free ~4.5%

    result: Dict[str, Any] = {
        "risk_score": round(risk_score, 3),
        "profile": profile,
        "allocation": allocation,
        "metrics": {
            "expected_return": round(er * 100.0, 2),
            "volatility": round(vol * 100.0, 2),
            "expense_ratio": round(exp_ratio * 100.0, 3),
            "sharpe_ratio": round(sharpe, 3),
            "equity_pct": round(equity_pct, 1),
            "num_holdings": len(allocation),
        },
        "etf_details": {
            t: {
                "name": ETF_UNIVERSE[_TICKER_TO_IDX[t]]["name"],
                "asset_class": ETF_UNIVERSE[_TICKER_TO_IDX[t]]["asset_class"],
                "category": ETF_UNIVERSE[_TICKER_TO_IDX[t]]["category"],
                "exp_return": round(ETF_UNIVERSE[_TICKER_TO_IDX[t]]["exp_return"] * 100, 2),
                "volatility": round(ETF_UNIVERSE[_TICKER_TO_IDX[t]]["volatility"] * 100, 2),
                "expense_ratio": round(ETF_UNIVERSE[_TICKER_TO_IDX[t]]["expense_ratio"] * 100, 3),
            }
            for t in allocation
        },
    }

    # Optional Monte Carlo
    if simulate:
        result["simulation"] = _run_monte_carlo(
            weights_pct=allocation,
            initial_investment=simulate.get("initial_investment", 10000),
            monthly_contribution=simulate.get("monthly_contribution", 500),
            years=simulate.get("years", 20),
        )

    return result
