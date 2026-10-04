"""Central, documented tuning constants for the A-share daily screener.

This module is the single source of truth for every "magic number" used by the
screener. Constants are deliberate defaults, grouped by where their rationale
comes from:

1. Market structure    — fixed by exchange rules (cannot be tuned).
2. Risk management     — industry-standard conventions.
3. Technical analysis  — common default windows.
4. Relative weights    — prior beliefs (sum to 1); set by reasoning, then
                         sanity-checked against local backtest history.

EMPIRICAL NOTE (local backtest history, 34 runs):
    The ML ensemble's direction signal did NOT beat the majority-class baseline
    (mean improvement -2.25%, median 0.0, only 7/34 positive; baseline accuracy
    already ~68% because labels are imbalanced). Therefore the ranking LEADS
    with the transparent momentum/trend factor and treats the ML up-probability
    as a secondary confirmation — not the dominant signal.
"""

# ---------------------------------------------------------------------------
# rank_score weights (sum to 1) — "which signal matters most for rising picks"
# ---------------------------------------------------------------------------
# Factor score leads: momentum/trend is a documented A-share cross-sectional
# anomaly and is transparent/interpretable.
RANK_W_FACTOR = 0.55
# ML up-probability is demoted from a prior 0.5 because local backtests showed
# no edge over the majority-class baseline. Kept as a weak confirmation.
RANK_W_ENSEMBLE_UP = 0.30
# Confidence (direction strength + model agreement) is a quality signal, not
# independently predictive — smallest weight.
RANK_W_CONFIDENCE = 0.15

# ---------------------------------------------------------------------------
# factor score weights (sum to 1) — decision engine `_rank`
# ---------------------------------------------------------------------------
# Momentum is the strongest documented cross-sectional factor -> highest.
FACTOR_W_MOMENTUM = 0.35
# Trend (price above MA20/MA60) confirms direction -> second.
FACTOR_W_TREND = 0.30
# Liquidity guarantees tradability -> third.
FACTOR_W_LIQUIDITY = 0.20
# Stability penalizes volatility (low-vol premium) -> smallest.
FACTOR_W_STABILITY = 0.15

# ---------------------------------------------------------------------------
# universe prefilter — tradability / quality gates
# ---------------------------------------------------------------------------
PRE_MIN_PRICE = 3.0             # avoid penny / near-ST stocks (delisting risk, wide spreads)
PRE_MAX_PRICE = 300.0           # avoid names a small account cannot buy in 100-share lots
PRE_MIN_MARKET_CAP = 3_000_000_000.0  # 30亿; drop micro-caps (illiquid, manipulable)
PRE_ALLOWED_PREFIXES = ("60", "68", "00", "30")  # main board / STAR / ChiNext (exclude Beijing 8xx/4xx/92x)
PRE_EXCLUDE_NAME_TOKENS = ("ST", "退")           # delisting risk
PRE_MAX_POOL = 60               # shortlist size fed to the factor screen
PRE_QUICK_TURNOVER_SCALE = 10.0 # scale turnover (~0.01-0.05) to be comparable with change_percent
PRE_QUICK_TURNOVER_CAP = 0.05   # cap turnover contribution (avoid single ultra-hot name dominating)

# ---------------------------------------------------------------------------
# factor screen -> prediction coverage
# ---------------------------------------------------------------------------
FACTOR_MIN_SCORE = 0.55         # above-median quality threshold; drops weakest half, keeps enough candidates
FACTOR_TOP_N = 25               # candidates that get a full ML prediction (coverage vs compute)

# ---------------------------------------------------------------------------
# risk management (entry plan)
# ---------------------------------------------------------------------------
RISK_PER_TRADE = 0.01           # 1% rule: max capital at risk per position (fixed-fractional sizing)
MAX_POSITION_PCT = 0.05         # 5% per name -> 5 picks ~= 25% deployed
ATR_STOP_MULTIPLE = 2.0         # 2x ATR(14) stop: outside ~95% of normal daily noise
STOP_FLOOR_PCT = 0.08           # hard -8% floor, bounds loss even when ATR is tiny
LOT_SIZE = 100                  # A-share board lot
R_MULTIPLES = (1.0, 2.0, 3.0)   # take-profit ladder in units of per-share risk R

# ---------------------------------------------------------------------------
# prediction horizon
# ---------------------------------------------------------------------------
HORIZON = 5                     # 1 trading week (swing horizon)
UP_THRESHOLD = 0.02             # +2% counts as "up" (covers ~2x transaction costs)
