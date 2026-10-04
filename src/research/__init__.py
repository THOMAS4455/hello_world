"""Research helpers shared by daily recommendations and holding advice."""

from .decision_engine import analyze_holding, build_candidate_report

__all__ = ["analyze_holding", "build_candidate_report"]
