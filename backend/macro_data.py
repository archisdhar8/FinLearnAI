"""
Macro Data Client — FRED API integration with local caching.

Fetches key macroeconomic indicators from the Federal Reserve Economic
Data (FRED) API for macro regime classification and expected return modelling:

  - Treasury yields (10Y, 3M, 2Y) → discount rate and yield curve analysis
  - CPI (monthly level) → Year-over-Year inflation and inflation trend
  - Unemployment rate → business cycle positioning
  - NFCI (Chicago Fed) → financial stress measurement
  - BAA-10Y spread → credit conditions

Theory:
  The discount rate channel (rates → equity valuations) and business-cycle
  positioning drive sector-level expected-return adjustments.  An inverted
  yield curve is the single best recession predictor (Estrella & Mishkin 1996).

Design:
  - Simple HTTP GET to FRED REST API (no external FRED library required).
  - Local JSON cache (backend/cache/fred_cache.json) with configurable TTL
    to avoid rate limits (FRED allows 120 requests/min on free keys).
  - Graceful fallback: FRED → disk cache → hardcoded defaults.
  - Deterministic output given the same inputs.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List, Any

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

DEFAULT_CACHE_DIR = Path(__file__).parent / "cache"
CACHE_FILENAME = "fred_cache.json"
DEFAULT_CACHE_TTL_HOURS = 24

# Series configuration: how many observations to pull for each
FRED_SERIES = {
    "DGS10":    {"description": "10-Year Treasury Yield",                       "limit": 5},
    "DGS3MO":   {"description": "3-Month Treasury Yield",                      "limit": 5},
    "DGS2":     {"description": "2-Year Treasury Yield",                        "limit": 5},
    "CPIAUCSL": {"description": "Consumer Price Index (All Urban, monthly)",    "limit": 25},
    "UNRATE":   {"description": "Unemployment Rate (monthly)",                  "limit": 10},
    "NFCI":     {"description": "Chicago Fed National Financial Conditions",    "limit": 5},
    "BAA10Y":   {"description": "Moody's BAA Corporate Bond - 10Y Spread",     "limit": 5},
}

# Default macro values when FRED is entirely unavailable.
# These represent a "neutral Expansion" baseline circa early 2026.
DEFAULTS: Dict[str, float] = {
    "dgs10":          4.30,
    "dgs3mo":         4.20,
    "dgs2":           4.10,
    "cpi_yoy":        3.00,
    "cpi_yoy_6m_ago": 3.20,
    "unrate":         4.00,
    "unrate_6m_ago":  3.80,
    "nfci":          -0.20,   # Negative = loose conditions
    "baa10y":         1.80,
}


# ---------------------------------------------------------------------------
# MacroSnapshot — point-in-time data object
# ---------------------------------------------------------------------------

@dataclass
class MacroSnapshot:
    """
    Point-in-time snapshot of macroeconomic indicators.

    All yields and rates are in **percentage points** (e.g. 4.3 = 4.3 %).
    Derived properties (yield_curve_slope, etc.) are computed on-the-fly.
    """
    dgs10: float            # 10-Year Treasury yield (%)
    dgs3mo: float           # 3-Month Treasury yield (%)
    dgs2: float             # 2-Year Treasury yield (%)
    cpi_yoy: float          # Current CPI Year-over-Year (%)
    cpi_yoy_6m_ago: float   # CPI YoY 6 months ago (%)
    unrate: float           # Current unemployment rate (%)
    unrate_6m_ago: float    # Unemployment rate 6 months ago (%)
    nfci: Optional[float]   = None    # National Financial Conditions Index
    baa10y: Optional[float] = None    # BAA-10Y credit spread (%)
    timestamp: str          = ""
    data_source: str        = "defaults"   # "fred" | "cache" | "defaults"

    # -- Derived features ----------------------------------------------------

    @property
    def yield_curve_slope(self) -> float:
        """10Y − 3M.  Negative ⟹ inverted curve (recession signal)."""
        return self.dgs10 - self.dgs3mo

    @property
    def term_spread_2s10s(self) -> float:
        """10Y − 2Y.  Classic recession predictor."""
        return self.dgs10 - self.dgs2

    @property
    def inflation_trend(self) -> float:
        """Change in CPI YoY over last 6 months.  Positive ⟹ rising inflation."""
        return self.cpi_yoy - self.cpi_yoy_6m_ago

    @property
    def unemployment_trend(self) -> float:
        """Change in unemployment over last 6 months.  Positive ⟹ rising."""
        return self.unrate - self.unrate_6m_ago

    @property
    def real_rate(self) -> float:
        """Rough Fisher real rate: 10Y nominal − CPI YoY."""
        return self.dgs10 - self.cpi_yoy

    def to_dict(self) -> dict:
        """Serialise including computed properties."""
        d = asdict(self)
        d["yield_curve_slope"]  = round(self.yield_curve_slope, 3)
        d["term_spread_2s10s"]  = round(self.term_spread_2s10s, 3)
        d["inflation_trend"]    = round(self.inflation_trend, 3)
        d["unemployment_trend"] = round(self.unemployment_trend, 3)
        d["real_rate"]          = round(self.real_rate, 3)
        return d


# ---------------------------------------------------------------------------
# FredClient
# ---------------------------------------------------------------------------

class FredClient:
    """
    Lightweight FRED API client with disk-based JSON caching.

    Usage::

        client = FredClient(api_key="your_key")
        snapshot = client.get_snapshot()          # FRED → cache → defaults
        snapshot = client.get_snapshot(force_refresh=True)  # skip cache
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        cache_ttl_hours: int = DEFAULT_CACHE_TTL_HOURS,
    ):
        self.api_key = api_key or os.environ.get("FRED_API_KEY", "")
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.cache_file = self.cache_dir / CACHE_FILENAME

        if not self.api_key:
            logger.warning(
                "No FRED API key provided.  Will use disk cache or defaults."
            )

    # -- low-level helpers ---------------------------------------------------

    def _fetch_series(self, series_id: str, limit: int = 5) -> List[Dict[str, str]]:
        """GET one FRED series, returning a list of {date, value} dicts."""
        if not self.api_key:
            return []

        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        }
        try:
            resp = requests.get(FRED_BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return [
                {"date": obs["date"], "value": obs["value"]}
                for obs in data.get("observations", [])
                if obs.get("value") and obs["value"] != "."
            ]
        except requests.RequestException as exc:
            logger.warning("FRED fetch failed for %s: %s", series_id, exc)
            return []

    @staticmethod
    def _parse_latest(obs: List[Dict], default: float) -> float:
        """Return the most recent numeric value, or *default*."""
        if not obs:
            return default
        try:
            return float(obs[0]["value"])
        except (ValueError, KeyError, IndexError):
            return default

    def _compute_cpi_yoy(self, obs: List[Dict]) -> tuple:
        """
        From *descending*-date CPI observations, compute:
          (current_yoy%, yoy_6_months_ago%)

        CPI is a price **level** so YoY = (latest / 12-months-ago − 1) × 100.
        """
        if len(obs) < 13:
            logger.warning("Insufficient CPI data (%d obs). Using defaults.", len(obs))
            return DEFAULTS["cpi_yoy"], DEFAULTS["cpi_yoy_6m_ago"]

        try:
            vals = [float(o["value"]) for o in obs]
            current_yoy = (vals[0] / vals[12] - 1) * 100

            if len(vals) >= 19:
                yoy_6m_ago = (vals[6] / vals[18] - 1) * 100
            else:
                yoy_6m_ago = current_yoy  # fallback: no trend data
            return round(current_yoy, 2), round(yoy_6m_ago, 2)
        except (ValueError, ZeroDivisionError, IndexError) as exc:
            logger.warning("CPI YoY computation failed: %s", exc)
            return DEFAULTS["cpi_yoy"], DEFAULTS["cpi_yoy_6m_ago"]

    def _compute_unrate_trend(self, obs: List[Dict]) -> tuple:
        """Return (current_unrate, unrate_6_months_ago) from descending obs."""
        if len(obs) < 7:
            logger.warning("Insufficient UNRATE data (%d obs). Using defaults.", len(obs))
            return DEFAULTS["unrate"], DEFAULTS["unrate_6m_ago"]
        try:
            vals = [float(o["value"]) for o in obs]
            return vals[0], vals[6]
        except (ValueError, IndexError) as exc:
            logger.warning("UNRATE parsing failed: %s", exc)
            return DEFAULTS["unrate"], DEFAULTS["unrate_6m_ago"]

    # -- cache ---------------------------------------------------------------

    def _load_cache(self) -> Optional[MacroSnapshot]:
        """Load snapshot from disk if the file exists and is fresh."""
        if not self.cache_file.exists():
            return None
        try:
            with open(self.cache_file, "r") as fh:
                data = json.load(fh)
            cached_time = datetime.fromisoformat(data.get("timestamp", "2000-01-01"))
            if datetime.now() - cached_time > self.cache_ttl:
                logger.info("FRED cache expired (age > %s).", self.cache_ttl)
                return None  # expired
            data["data_source"] = "cache"
            fields = {k for k in MacroSnapshot.__dataclass_fields__}
            return MacroSnapshot(**{k: v for k, v in data.items() if k in fields})
        except Exception as exc:
            logger.warning("Failed to load FRED cache: %s", exc)
            return None

    def _load_expired_cache(self) -> Optional[MacroSnapshot]:
        """Load cache even if expired (last-resort before defaults)."""
        if not self.cache_file.exists():
            return None
        try:
            with open(self.cache_file, "r") as fh:
                data = json.load(fh)
            data["data_source"] = "cache_expired"
            fields = {k for k in MacroSnapshot.__dataclass_fields__}
            logger.warning("Using expired FRED cache as fallback.")
            return MacroSnapshot(**{k: v for k, v in data.items() if k in fields})
        except Exception:
            return None

    def _save_cache(self, snapshot: MacroSnapshot):
        """Persist snapshot to disk."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            data = asdict(snapshot)
            data["timestamp"] = datetime.now().isoformat()
            with open(self.cache_file, "w") as fh:
                json.dump(data, fh, indent=2)
            logger.info("FRED cache saved to %s", self.cache_file)
        except Exception as exc:
            logger.warning("Failed to save FRED cache: %s", exc)

    # -- public API ----------------------------------------------------------

    def get_snapshot(self, force_refresh: bool = False) -> MacroSnapshot:
        """
        Return a **MacroSnapshot** with current macro indicators.

        Resolution order:  FRED API → fresh disk cache → expired cache → defaults.

        Args:
            force_refresh:  If *True*, skip cache and hit FRED directly.
        """
        # 1) Try fresh cache
        if not force_refresh:
            cached = self._load_cache()
            if cached is not None:
                logger.info("Using cached FRED data (source=cache).")
                return cached

        # 2) Try FRED API
        if self.api_key:
            logger.info("Fetching fresh data from FRED API …")
            raw: Dict[str, List[Dict]] = {}
            for sid, cfg in FRED_SERIES.items():
                raw[sid] = self._fetch_series(sid, limit=cfg["limit"])

            has_data = any(len(v) > 0 for v in raw.values())
            if has_data:
                dgs10  = self._parse_latest(raw["DGS10"],  DEFAULTS["dgs10"])
                dgs3mo = self._parse_latest(raw["DGS3MO"], DEFAULTS["dgs3mo"])
                dgs2   = self._parse_latest(raw["DGS2"],   DEFAULTS["dgs2"])
                nfci   = self._parse_latest(raw["NFCI"],   DEFAULTS["nfci"])
                baa10y = self._parse_latest(raw["BAA10Y"], DEFAULTS["baa10y"])

                cpi_yoy, cpi_yoy_6m_ago = self._compute_cpi_yoy(raw["CPIAUCSL"])
                unrate, unrate_6m_ago   = self._compute_unrate_trend(raw["UNRATE"])

                snapshot = MacroSnapshot(
                    dgs10=dgs10, dgs3mo=dgs3mo, dgs2=dgs2,
                    cpi_yoy=cpi_yoy, cpi_yoy_6m_ago=cpi_yoy_6m_ago,
                    unrate=unrate, unrate_6m_ago=unrate_6m_ago,
                    nfci=nfci, baa10y=baa10y,
                    timestamp=datetime.now().isoformat(),
                    data_source="fred",
                )
                self._save_cache(snapshot)
                return snapshot
            else:
                logger.warning("FRED returned no data for any series.")

        # 3) Expired cache
        expired = self._load_expired_cache()
        if expired is not None:
            return expired

        # 4) Hardcoded defaults
        logger.warning(
            "Using hardcoded default macro values.  "
            "Expected-return estimates may be less accurate."
        )
        return MacroSnapshot(
            **DEFAULTS,
            timestamp=datetime.now().isoformat(),
            data_source="defaults",
        )
