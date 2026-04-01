"""
Decision-quality models and utilities.

This package is intentionally backend-only for now – nothing is wired into the
FastAPI routes yet. It provides:

- Feature builders for ETF allocations
- A simple rule-based oracle for decision labels
- Offline training scripts to fit a small ML model (sklearn)
- A service helper that can be imported later by API endpoints
"""

