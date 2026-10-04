#!/usr/bin/env python3
"""
Three-layer predictor used by the FastAPI prediction service.
Layer-1: baseline tree models
Layer-2: enhanced statistical/boosting models
Layer-3: regime-aware model routing
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
)
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

# Import trading constraints for PnL backtest simulation
try:
    from trading.constraints import TradingConstraints
except ImportError:
    TradingConstraints = None  # type: ignore[assignment]

# Import gradient boosting libraries (with fallback if not installed)
try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    import catboost as cb
    CATBOOST_AVAILABLE = True
except ImportError:
    CATBOOST_AVAILABLE = False

warnings.filterwarnings("ignore")


def _clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def purged_train_test_split(
    n_samples: int, test_size: float = 0.2, horizon: int = 0
) -> Tuple[int, int]:
    """Return (train_end_exclusive, test_start) with an embargo of `horizon` rows."""
    if n_samples <= 0:
        return 0, 0
    test_start = int(n_samples * (1 - test_size))
    test_start = max(1, min(test_start, n_samples - 1))
    train_end = max(0, test_start - max(0, int(horizon)))
    return train_end, test_start


def align_features_and_labels(
    features_df: pd.DataFrame, labels: pd.Series
) -> Tuple[pd.DataFrame, pd.Series]:
    valid = labels.notna()
    aligned_features = features_df.loc[valid].copy()
    aligned_labels = labels.loc[valid].astype(int)
    return aligned_features, aligned_labels


class ImprovedPredictor:
    def __init__(self, learn_weights: bool = True, feature_selection: bool = False) -> None:
        """
        Initialize ImprovedPredictor with weight learning and LSTM support

        Args:
            learn_weights: If True, learn ensemble weights from validation data (recommended).
                          If False, use fixed weights (0.35, 0.40, 0.25).
            feature_selection: If True, prune low-importance features BEFORE fitting.
                          Off by default: the previous post-fit pruning was dead code
                          (prepare_features() rewrote self.feature_columns on every
                          predict call, silently undoing it) and no ablation showed a
                          gain from it.
        """
        # Weight learning configuration
        self.learn_weights = learn_weights
        self.feature_selection = bool(feature_selection)
        # Columns actually used at inference. Set by train(), consumed by predict().
        self.inference_columns: List[str] = []
        self.within_layer_weights: Dict[str, Dict[str, float]] = {}
        self.learned_layer_weights: Dict[str, float] = {}
        
        # Try to import LSTM model
        self.lstm_model = None
        self.lstm_enabled = False
        try:
            from .lstm_model import LSTMPredictor, TENSORFLOW_AVAILABLE
            if TENSORFLOW_AVAILABLE:
                self.lstm_model = LSTMPredictor(
                    sequence_length=10,
                    units=64,
                    dropout_rate=0.3,
                    learning_rate=0.001
                )
                self.lstm_enabled = True
        except (ImportError, Exception):
            pass
        
        # Try to import weight optimizer
        try:
            from .weight_optimizer import hierarchical_weight_optimization
            self._hierarchical_weight_optimization = hierarchical_weight_optimization
            self.weight_optimizer_available = True
        except (ImportError, Exception):
            self.weight_optimizer_available = False
        
        # Balanced regularization: strong enough to avoid overfitting, but enough capacity to learn
        self.layer_models = {
            "baseline": {
                "rf": RandomForestClassifier(
                    n_estimators=150,
                    max_depth=12,
                    min_samples_split=10,
                    min_samples_leaf=5,
                    max_features='sqrt',
                    class_weight='balanced',
                    random_state=42,
                ),
                "gb": GradientBoostingClassifier(
                    n_estimators=120,
                    learning_rate=0.05,
                    max_depth=5,
                    min_samples_split=10,
                    min_samples_leaf=5,
                    subsample=0.75,
                    random_state=42,
                ),
            },
            "enhanced": {
                "extra_trees": ExtraTreesClassifier(
                    n_estimators=150,
                    max_depth=12,
                    min_samples_split=10,
                    min_samples_leaf=5,
                    max_features='sqrt',
                    class_weight='balanced',
                    random_state=42,
                ),
                "log_reg": LogisticRegression(
                    C=0.5,
                    class_weight='balanced',
                    max_iter=2000,
                    random_state=42,
                ),
                "svm": SVC(
                    kernel="rbf",
                    C=0.5,
                    gamma='scale',
                    class_weight='balanced',
                    probability=True,
                    random_state=42,
                ),
            },
        }

        if LIGHTGBM_AVAILABLE:
            self.layer_models["baseline"]["lgb"] = lgb.LGBMClassifier(
                n_estimators=150,
                learning_rate=0.05,
                max_depth=6,
                num_leaves=20,
                min_child_samples=20,
                subsample=0.75,
                colsample_bytree=0.75,
                reg_alpha=1.0,
                reg_lambda=2.0,
                class_weight='balanced',
                random_state=42,
                verbose=-1,
            )

        if XGBOOST_AVAILABLE:
            self.layer_models["enhanced"]["xgb"] = xgb.XGBClassifier(
                n_estimators=150,
                learning_rate=0.05,
                max_depth=5,
                min_child_weight=5,
                gamma=0.2,
                subsample=0.75,
                colsample_bytree=0.75,
                reg_alpha=1.0,
                reg_lambda=2.0,
                scale_pos_weight=2.0,
                random_state=42,
                eval_metric='logloss',
                use_label_encoder=False,
            )

        if CATBOOST_AVAILABLE:
            self.layer_models["enhanced"]["catboost"] = cb.CatBoostClassifier(
                iterations=150,
                learning_rate=0.05,
                depth=5,
                l2_leaf_reg=4.0,
                bagging_temperature=0.3,
                random_strength=0.2,
                min_data_in_leaf=10,
                auto_class_weights='Balanced',
                random_state=42,
                verbose=False,
                allow_writing_files=False,
            )
        
        self.regime_models = {
            "bull": LogisticRegression(max_iter=2000, random_state=42),
            "bear": LogisticRegression(max_iter=2000, random_state=42),
            "range": LogisticRegression(max_iter=2000, random_state=42),
            "high_vol": LogisticRegression(max_iter=2000, random_state=42),
        }
        self.scaler = StandardScaler()
        self.feature_columns: List[str] = []
        # Every feature produced by the last prepare_features() call. Kept separate
        # from feature_columns so inference/backtest code can never silently undo a
        # trained pruning decision.
        self.available_feature_columns: List[str] = []
        self.is_trained = False
        self.model_scores: Dict[str, Dict[str, float]] = {}
        self.layer_weights = {"baseline": 0.35, "enhanced": 0.4, "regime": 0.25}
        self.up_threshold = 0.02
        self.label_method: str = "fixed_horizon"
        self.stop_loss_pct: float | None = None
        self.trained_models: Dict[str, object] = {}
        self.trained_regime_models: Dict[str, object] = {}
        self.global_regime_fallback = LogisticRegression(max_iter=2000, random_state=42)
        self._train_vol_threshold: float = 0.0
        self.decision_threshold: float = 0.5
        self.probability_calibrator: LogisticRegression | None = None
        self.feature_importance_scores: Dict[str, float] = {}
        self.regime_decision_thresholds: Dict[str, float] = {}
        self.active_feature_columns: List[str] = []
        self.active_model_ids: set = set()
        self.regime_entry_gates: Dict[str, float] = {
            "bull": 0.33, "bear": 0.20, "range": 0.25, "high_vol": 0.28,
        }

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        features = df.copy()

        features["ma5"] = features["close_price"].rolling(window=5).mean()
        features["ma20"] = features["close_price"].rolling(window=20).mean()
        features["ma60"] = features["close_price"].rolling(window=60).mean()

        features["price_change"] = features["close_price"].pct_change()
        features["price_change_2d"] = features["close_price"].pct_change(2)
        features["price_change_5d"] = features["close_price"].pct_change(5)

        features["volatility"] = features["price_change"].rolling(window=10).std()
        features["volatility_30"] = features["price_change"].rolling(window=30).std()
        features["volume_ratio"] = (
            features["volume"] / features["volume"].rolling(window=20).mean()
        )

        delta = features["close_price"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, np.nan)
        features["rsi"] = 100 - (100 / (1 + rs))

        exp1 = features["close_price"].ewm(span=12).mean()
        exp2 = features["close_price"].ewm(span=26).mean()
        features["macd"] = exp1 - exp2
        features["macd_signal"] = features["macd"].ewm(span=9).mean()
        features["macd_histogram"] = features["macd"] - features["macd_signal"]

        rolling_std = features["close_price"].rolling(window=20).std()
        features["bb_upper"] = features["ma20"] + 2 * rolling_std
        features["bb_lower"] = features["ma20"] - 2 * rolling_std
        features["bb_position"] = (
            (features["close_price"] - features["bb_lower"])
            / (features["bb_upper"] - features["bb_lower"])
        )

        features["trend_strength"] = (
            (features["ma5"] - features["ma20"]) / features["ma20"]
        )
        features["ma60_gap"] = (features["close_price"] - features["ma60"]) / features["ma60"]

        # On-Balance Volume (OBV) — volume-price confirmation
        price_dir = np.sign(features["close_price"].diff())
        features["obv"] = (price_dir * features["volume"]).cumsum()
        features["obv_ratio"] = features["obv"] / features["obv"].rolling(window=20).mean()

        # Money Flow Index (MFI, 14-period) — volume-weighted RSI
        typical_price = (
            features["close_price"]
            + features.get("high_price", features["close_price"])
            + features.get("low_price", features["close_price"])
        ) / 3
        raw_mf = typical_price * features["volume"]
        tp_diff = typical_price.diff()
        pos_flow = raw_mf.where(tp_diff > 0, 0).rolling(window=14).sum()
        neg_flow = raw_mf.where(tp_diff < 0, 0).rolling(window=14).sum()
        features["mfi"] = 100 - (100 / (1 + pos_flow / neg_flow.replace(0, np.nan)))

        # Average True Range (ATR, 14-period) — volatility normalization
        prev_close = features["close_price"].shift(1)
        tr1 = features.get("high_price", features["close_price"]) - features.get("low_price", features["close_price"])
        tr2 = abs(features.get("high_price", features["close_price"]) - prev_close)
        tr3 = abs(features.get("low_price", features["close_price"]) - prev_close)
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        features["atr"] = tr.rolling(window=14).mean()
        features["atr_ratio"] = features["atr"] / features["close_price"]

        # Volatility-adjusted momentum (known alpha factor in A-shares)
        for n in [20, 60, 120]:
            mom = features["close_price"] / features["close_price"].shift(n) - 1.0
            vol_n = features["price_change"].rolling(window=n).std()
            features[f"vol_adj_mom_{n}"] = mom / (vol_n + 1e-9)

        # Add advanced features
        features = self._add_time_series_features(features)
        features = self._add_cross_features(features)
        features = self._add_microstructure_features(features)
        
        # Replace inf values with NaN
        features = features.replace([np.inf, -np.inf], np.nan)

        base_columns = [
            "ma5",
            "ma20",
            "ma60",
            "price_change",
            "price_change_2d",
            "price_change_5d",
            "volatility",
            "volatility_30",
            "volume_ratio",
            "rsi",
            "macd",
            "macd_signal",
            "macd_histogram",
            "bb_position",
            "trend_strength",
            "ma60_gap",
            "obv_ratio",
            "mfi",
            "atr_ratio",
            "vol_adj_mom_20",
            "vol_adj_mom_60",
            "vol_adj_mom_120",
        ]

        # Time-series features (9)
        time_series_cols = [
            "price_change_lag1", "price_change_lag5",
            "volume_lag1",
            "rolling_mean_20",
            "rolling_std_20", "rolling_skew_20",
            "ema20",
            "price_autocorr_1"
        ]
        
        # Cross features (13)
        cross_cols = [
            "price_change_x_volume_ratio", "volatility_x_volume", "rsi_x_volume_ratio",
            "macd_x_volume",
            "rsi_x_macd", "volatility_x_trend_strength", "volume_ratio_x_trend_strength",
            "rsi_x_bb_position", "macd_x_trend_strength",
            "volume_price_momentum", "volatility_regime",
            "technical_momentum", "composite_signal"
        ]
        
        # Microstructure features (15)
        microstructure_cols = [
            "high_low_spread", "open_close_spread", "intraday_range",
            "volume_price_impact", "large_trade_indicator",
            "buy_sell_imbalance_proxy", "tick_direction",
            "amihud_illiquidity", "turnover_rate", "bid_ask_spread_proxy",
            "realized_volatility", "garman_klass_volatility", "parkinson_volatility",
            "rogers_satchell_volatility", "yang_zhang_volatility"
        ]
        
        # Only include features that exist in the dataframe
        time_series_cols = [col for col in time_series_cols if col in features.columns]
        cross_cols = [col for col in cross_cols if col in features.columns]
        microstructure_cols = [col for col in microstructure_cols if col in features.columns]
        
        self.available_feature_columns = (
            base_columns + time_series_cols + cross_cols + microstructure_cols
        )

        # Fill NaN values in feature columns
        # Strategy: forward fill first, then backward fill, then fill with 0
        for col in self.available_feature_columns:
            if col in features.columns:
                features[col] = features[col].fillna(method='ffill').fillna(method='bfill').fillna(0)

        # Drop remaining rows where feature columns still have NaN (should be rare now)
        features = features.dropna(subset=self.available_feature_columns)
        
        return features

    def _add_time_series_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """Add time-series features (9 features) - Task 2.4"""
        # Lagged features (3)
        features["price_change_lag1"] = features["price_change"].shift(1)
        features["price_change_lag5"] = features["price_change"].shift(5)
        features["volume_lag1"] = features["volume"].shift(1)

        # Rolling statistics (3)
        features["rolling_mean_20"] = features["close_price"].rolling(window=20).mean()
        features["rolling_std_20"] = features["close_price"].rolling(window=20).std()
        features["rolling_skew_20"] = features["close_price"].rolling(window=20).skew()

        # Exponential moving average (1)
        features["ema20"] = features["close_price"].ewm(span=20, adjust=False).mean()

        # Autocorrelation (1)
        features["price_autocorr_1"] = features["price_change"].rolling(window=20).apply(
            lambda x: x.autocorr(lag=1) if len(x) > 1 else 0, raw=False
        )

        return features
    
    def _add_cross_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """Add cross-features (13 features) - Task 2.3"""
        # Technical × Volume (6)
        features["price_change_x_volume_ratio"] = features["price_change"] * features["volume_ratio"]
        features["volatility_x_volume"] = features["volatility"] * features["volume"]
        features["rsi_x_volume_ratio"] = features["rsi"] * features["volume_ratio"]
        features["macd_x_volume"] = features["macd"] * features["volume_ratio"]
        features["volume_ratio_x_trend_strength"] = features["volume_ratio"] * features["trend_strength"]
        features["volume_price_momentum"] = features["volume_ratio"] * features["price_change"]

        # Technical × Technical (4)
        features["rsi_x_bb_position"] = features["rsi"] * features["bb_position"]
        features["macd_x_trend_strength"] = features["macd"] * features["trend_strength"]
        features["rsi_x_macd"] = features["rsi"] * features["macd"]
        features["volatility_x_trend_strength"] = features["volatility"] * features["trend_strength"]

        # Composite indicators (3)
        features["volatility_regime"] = (features["volatility_30"] > features["volatility_30"].rolling(window=60).mean()).astype(float)
        features["technical_momentum"] = features["rsi"] * features["macd"] * features["trend_strength"]
        features["composite_signal"] = (features["rsi"] + features["macd"] * 10 + features["trend_strength"] * 100) / 3

        return features
    
    def _add_microstructure_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """Add microstructure features (15 features) - Task 2.5"""
        # Spread proxies (3)
        if "high_price" in features.columns and "low_price" in features.columns:
            features["high_low_spread"] = (features["high_price"] - features["low_price"]) / features["close_price"]
        else:
            features["high_low_spread"] = 0.01  # Default value
            
        if "open_price" in features.columns:
            features["open_close_spread"] = (features["close_price"] - features["open_price"]) / features["close_price"]
            features["intraday_range"] = abs(features["high_price"] - features["low_price"]) / features["open_price"] if "high_price" in features.columns else 0.01
        else:
            features["open_close_spread"] = 0.0
            features["intraday_range"] = 0.01
        
        # Price impact (2)
        features["volume_price_impact"] = features["price_change"] / (features["volume"] + 1e-6)
        features["large_trade_indicator"] = (features["volume"] > features["volume"].rolling(window=20).mean() * 1.5).astype(float)
        
        # Order flow (2)
        features["buy_sell_imbalance_proxy"] = features["price_change"] * features["volume"]
        features["tick_direction"] = np.sign(features["price_change"])
        
        # Liquidity (3)
        features["amihud_illiquidity"] = abs(features["price_change"]) / (features["volume"] + 1e-6)
        features["turnover_rate"] = features["volume"] / features["volume"].rolling(window=20).mean()
        features["bid_ask_spread_proxy"] = features["high_low_spread"]  # Proxy using high-low spread
        
        # Volatility patterns (5)
        if "high_price" in features.columns and "low_price" in features.columns and "open_price" in features.columns:
            # Realized volatility
            features["realized_volatility"] = features["price_change"].rolling(window=20).std() * np.sqrt(252)
            
            # Garman-Klass volatility
            hl = np.log(features["high_price"] / features["low_price"])
            co = np.log(features["close_price"] / features["open_price"])
            features["garman_klass_volatility"] = np.sqrt(0.5 * hl**2 - (2*np.log(2)-1) * co**2)
            
            # Parkinson volatility
            features["parkinson_volatility"] = np.sqrt(hl**2 / (4 * np.log(2)))
            
            # Rogers-Satchell volatility
            ho = np.log(features["high_price"] / features["open_price"])
            lo = np.log(features["low_price"] / features["open_price"])
            ch = np.log(features["close_price"] / features["high_price"])
            cl = np.log(features["close_price"] / features["low_price"])
            features["rogers_satchell_volatility"] = np.sqrt(ho * ch + lo * cl)
            
            # Yang-Zhang volatility (simplified)
            features["yang_zhang_volatility"] = features["realized_volatility"] * 1.1  # Simplified approximation
        else:
            # Use simplified volatility if OHLC not available
            features["realized_volatility"] = features["volatility"] * np.sqrt(252)
            features["garman_klass_volatility"] = features["volatility"]
            features["parkinson_volatility"] = features["volatility"]
            features["rogers_satchell_volatility"] = features["volatility"]
            features["yang_zhang_volatility"] = features["volatility"]
        
        return features

    def adopt_prepared_features(self) -> List[str]:
        """Adopt every feature produced by the last prepare_features() call.

        prepare_features() used to write self.feature_columns directly, which
        silently undid any trained pruning the moment predict() ran. Now callers
        opt in explicitly via this method.
        """
        available = list(getattr(self, "available_feature_columns", []) or [])
        if available:
            self.feature_columns = available
        return self.feature_columns

    def prepare_labels(
        self, df: pd.DataFrame, horizon: int = 5, up_threshold: float = 0.02,
        stop_loss_pct: float | None = None, label_method: str = "fixed_horizon",
    ) -> pd.Series:
        if label_method == "triple_barrier":
            return self._prepare_triple_barrier_labels(df, horizon, up_threshold, stop_loss_pct)

        future_return = df["close_price"].shift(-horizon) / df["close_price"] - 1
        labels = pd.Series(np.nan, index=df.index, dtype=float)
        valid = future_return.notna()
        labels.loc[valid] = (future_return.loc[valid] > up_threshold).astype(int)
        return labels

    def _prepare_triple_barrier_labels(
        self, df: pd.DataFrame, horizon: int, up_threshold: float, stop_loss_pct: float | None,
    ) -> pd.Series:
        closes = df["close_price"].values
        n = len(closes)
        labels_arr = np.full(n, np.nan)
        stop_loss = stop_loss_pct if stop_loss_pct is not None else up_threshold

        for t in range(n - 1):
            entry = closes[t]
            if entry <= 0:
                labels_arr[t] = 0
                continue
            upper = entry * (1.0 + up_threshold)
            lower = entry * (1.0 - stop_loss)
            end = min(t + 1 + horizon, n)
            window = closes[t + 1 : end]
            if len(window) == 0:
                labels_arr[t] = 0
                continue
            upper_hit = window >= upper
            lower_hit = window <= lower
            if upper_hit.any():
                first_upper = int(np.argmax(upper_hit))
                if lower_hit.any() and int(np.argmax(lower_hit)) < first_upper:
                    labels_arr[t] = -1  # lower hit first
                else:
                    labels_arr[t] = 1   # upper hit first
            elif lower_hit.any():
                labels_arr[t] = -1
            else:
                labels_arr[t] = 0  # time barrier (no barrier hit)

        # Map {-1, 0, 1} -> {0, 1} for binary classifiers: -1 -> 0, 1 -> 1
        labels_series = pd.Series(labels_arr, index=df.index)
        labels_series = labels_series.replace(-1, 0)
        return labels_series

    def _derive_regime_labels(
        self, features_df: pd.DataFrame, vol_threshold: float | None = None
    ) -> pd.Series:
        threshold = (
            float(vol_threshold)
            if vol_threshold is not None
            else float(features_df["volatility_30"].quantile(0.75))
        )
        labels: List[str] = []
        for _, row in features_df.iterrows():
            trend = float(row.get("trend_strength", 0.0))
            vol = float(row.get("volatility_30", 0.0))
            if vol >= threshold:
                labels.append("high_vol")
            elif trend >= 0.015:
                labels.append("bull")
            elif trend <= -0.015:
                labels.append("bear")
            else:
                labels.append("range")
        return pd.Series(labels, index=features_df.index)

    def _latest_regime(self, latest_row: pd.Series, vol_threshold: float) -> str:
        trend = float(latest_row.get("trend_strength", 0.0))
        vol = float(latest_row.get("volatility_30", 0.0))
        if vol >= vol_threshold:
            return "high_vol"
        if trend >= 0.015:
            return "bull"
        if trend <= -0.015:
            return "bear"
        return "range"

    @staticmethod
    def walk_forward_folds(
        total_n: int, n_folds: int, test_size_per_fold: float, horizon: int
    ):
        """Yield purged expanding-window folds.

        Each item is (train_start, train_end, test_start, test_end). Shared by
        backtest_multi_fold and scripts/ablation_edge.py so every variant is
        compared on exactly the same out-of-sample windows. An embargo of
        horizon rows between train and test prevents label leakage across the
        boundary.
        """
        fold_size = int(total_n * test_size_per_fold)
        embargo = int(horizon)
        for fold in range(int(n_folds)):
            test_end = total_n - (int(n_folds) - 1 - fold) * fold_size
            test_start = test_end - fold_size
            train_end = max(0, test_start - embargo)
            if test_start <= 0 or test_end <= test_start:
                continue
            yield 0, train_end, test_start, test_end

    def _eval_metrics(self, y_true, y_pred) -> Dict[str, float]:
        """Accuracy plus the metrics that are actually informative here.

        The fixed-horizon label (1 = "5-day return above +2%") is heavily
        imbalanced, so a model that always predicts 0 can score 70-90% accuracy.
        Every report therefore carries the majority-class baseline and
        EDGE = accuracy - baseline, alongside balanced accuracy and MCC.
        """
        y_true_arr = np.asarray(y_true)
        y_pred_arr = np.asarray(y_pred)
        accuracy = float(accuracy_score(y_true_arr, y_pred_arr))
        positives = float(np.mean(y_true_arr == 1)) if len(y_true_arr) else 0.0
        baseline = max(positives, 1.0 - positives)
        return {
            "accuracy": accuracy,
            "baseline_accuracy": float(baseline),
            "edge": float(accuracy - baseline),
            "n_eval": int(len(y_true_arr)),
            "balanced_accuracy": float(balanced_accuracy_score(y_true_arr, y_pred_arr)),
            "mcc": float(matthews_corrcoef(y_true_arr, y_pred_arr)),
            "precision": float(
                precision_score(y_true, y_pred, pos_label=1, zero_division=0)
            ),
            "recall": float(recall_score(y_true, y_pred, pos_label=1, zero_division=0)),
            "f1": float(f1_score(y_true, y_pred, pos_label=1, zero_division=0)),
        }

    def _iter_all_models(self) -> List[Tuple[str, str, object]]:
        out = []
        for layer_name, models in self.layer_models.items():
            for model_name, model in models.items():
                out.append((layer_name, model_name, model))
        return out

    def _tune_decision_threshold(self, y_true: pd.Series, ensemble_probs: np.ndarray) -> float:
        if len(y_true) == 0 or len(ensemble_probs) == 0:
            return 0.5
        y_arr = y_true.to_numpy()
        best_t = 0.5
        best_acc = -1.0
        for threshold in np.linspace(0.30, 0.65, 36):
            preds = (ensemble_probs > threshold).astype(int)
            acc = float(accuracy_score(y_arr, preds))
            if acc > best_acc:
                best_acc = acc
                best_t = float(threshold)
        return best_t

    def _fit_ensemble_bundle(
        self, X: pd.DataFrame, y: pd.Series, features_df: pd.DataFrame
    ) -> Dict[str, Any]:
        train_vol_threshold = float(features_df["volatility_30"].quantile(0.75))
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        trained_models: Dict[str, object] = {}
        for layer_name, model_name, model in self._iter_all_models():
            model_inst = clone(model)
            if y.nunique() < 2:
                from sklearn.dummy import DummyClassifier
                model_inst = DummyClassifier(strategy="most_frequent")
            model_inst.fit(X_scaled, y)
            trained_models[f"{layer_name}:{model_name}"] = model_inst

        global_regime_fallback = LogisticRegression(max_iter=2000, random_state=42)
        global_regime_fallback.fit(X_scaled, y)

        regime_train_labels = self._derive_regime_labels(
            features_df, vol_threshold=train_vol_threshold
        )
        regime_models: Dict[str, object] = {}
        for regime in ["bull", "bear", "range", "high_vol"]:
            idx = regime_train_labels[regime_train_labels == regime].index
            if len(idx) < 60:
                continue
            X_reg = X.loc[idx]
            y_reg = y.loc[idx]
            if y_reg.nunique() < 2:
                continue
            model = clone(self.regime_models[regime])
            model.fit(scaler.transform(X_reg), y_reg)
            regime_models[regime] = model

        return {
            "scaler": scaler,
            "trained_models": trained_models,
            "regime_models": regime_models,
            "global_regime_fallback": global_regime_fallback,
            "train_vol_threshold": train_vol_threshold,
        }

    def _predict_ensemble_up(
        self, bundle: Dict[str, Any], X: pd.DataFrame, features_df: pd.DataFrame
    ) -> np.ndarray:
        n_rows = len(X)
        if n_rows == 0:
            return np.array([])

        scaler = bundle["scaler"]
        trained_models: Dict[str, object] = bundle["trained_models"]
        regime_models: Dict[str, object] = bundle["regime_models"]
        global_regime_fallback = bundle["global_regime_fallback"]
        train_vol_threshold = float(bundle["train_vol_threshold"])

        X_scaled = scaler.transform(X)
        baseline_probs: List[np.ndarray] = []
        enhanced_probs: List[np.ndarray] = []
        baseline_weights: List[float] = []
        enhanced_weights: List[float] = []

        for model_id, model in trained_models.items():
            if self.active_model_ids and model_id not in self.active_model_ids:
                continue  # skip weak models
            layer = model_id.split(":", 1)[0]
            prob_up = model.predict_proba(X_scaled)[:, 1]
            cv_w = max(0.0, self.model_scores.get(model_id, {}).get("cv_mean", 0.5) - 0.45)
            weighted_prob = prob_up * cv_w
            if layer == "baseline":
                baseline_probs.append(weighted_prob)
                baseline_weights.append(cv_w)
            else:
                enhanced_probs.append(weighted_prob)
                enhanced_weights.append(cv_w)

        baseline_up = (
            np.average(np.array(baseline_probs), axis=0, weights=baseline_weights)
            if baseline_probs and sum(baseline_weights) > 0
            else np.full(n_rows, 0.5)
        )
        enhanced_up = (
            np.average(np.array(enhanced_probs), axis=0, weights=enhanced_weights)
            if enhanced_probs and sum(enhanced_weights) > 0
            else np.full(n_rows, 0.5)
        )

        regime_labels = self._derive_regime_labels(
            features_df, vol_threshold=train_vol_threshold
        )
        regime_up = np.full(n_rows, 0.5)
        for i in range(n_rows):
            regime = regime_labels.iloc[i]
            model = regime_models.get(regime, global_regime_fallback)
            row_scaled = X_scaled[i : i + 1]
            regime_up[i] = float(model.predict_proba(row_scaled)[0, 1])

        ensemble_up = (
            self.layer_weights["baseline"] * baseline_up
            + self.layer_weights["enhanced"] * enhanced_up
            + self.layer_weights["regime"] * regime_up
        )
        return np.clip(ensemble_up, 0.0, 1.0)

    def _fit_platt_calibrator(
        self, probs: np.ndarray, y: pd.Series
    ) -> LogisticRegression | None:
        if len(probs) < 20 or y.nunique() < 2:
            return None
        calibrator = LogisticRegression(max_iter=1000)
        calibrator.fit(np.asarray(probs, dtype=float).reshape(-1, 1), y.astype(int))
        return calibrator

    def _calibrate_probs(self, calibrator: LogisticRegression | None, probs: np.ndarray) -> np.ndarray:
        if calibrator is None:
            return np.asarray(probs, dtype=float)
        return calibrator.predict_proba(np.asarray(probs, dtype=float).reshape(-1, 1))[:, 1]

    def _fit_validation_artifacts(
        self, X: pd.DataFrame, y: pd.Series, features_df: pd.DataFrame
    ) -> Tuple[float, LogisticRegression | None, Dict[str, float | bool]]:
        if y.nunique() < 2:
            return 0.5, None, {"enabled": False, "reason": "single_class"}
        val_n = max(20, min(80, int(len(X) * 0.15)))
        inner_end = len(X) - val_n
        if inner_end < 80:
            return 0.5, None, {"enabled": False}
        inner_bundle = self._fit_ensemble_bundle(
            X.iloc[:inner_end], y.iloc[:inner_end], features_df.iloc[:inner_end]
        )
        val_probs_raw = self._predict_ensemble_up(
            inner_bundle, X.iloc[inner_end:], features_df.iloc[inner_end:]
        )
        y_val = y.iloc[inner_end:]
        calibrator = self._fit_platt_calibrator(val_probs_raw, y_val)
        val_probs = self._calibrate_probs(calibrator, val_probs_raw)
        threshold = self._tune_decision_threshold(y_val, val_probs)
        brier_raw = float(brier_score_loss(y_val.astype(int), val_probs_raw))
        brier_cal = float(brier_score_loss(y_val.astype(int), val_probs))
        return threshold, calibrator, {
            "enabled": calibrator is not None,
            "brier_raw": brier_raw,
            "brier_calibrated": brier_cal,
            "brier_improvement": float(brier_raw - brier_cal),
        }

    def _resolve_decision_threshold(
        self, X: pd.DataFrame, y: pd.Series, features_df: pd.DataFrame
    ) -> float:
        threshold, _, _ = self._fit_validation_artifacts(X, y, features_df)
        return threshold

    def _max_drawdown(self, equity_curve: np.ndarray) -> float:
        if len(equity_curve) == 0:
            return 0.0
        peaks = np.maximum.accumulate(equity_curve)
        drawdowns = (equity_curve - peaks) / np.maximum(peaks, 1e-9)
        return float(np.min(drawdowns))

    def _simulate_pnl_backtest(
        self,
        features_test: pd.DataFrame,
        signals: List[int],
        horizon: int,
        transaction_cost: float = 0.001,
        ensemble_probs: np.ndarray | None = None,
        decision_threshold: float = 0.5,
        min_confidence: float = 0.0,
        constraints: "TradingConstraints | None" = None,
    ) -> Dict[str, Any]:
        closes = features_test["close_price"].astype(float).values
        if "price_change" in features_test.columns:
            price_change = features_test["price_change"].astype(float).fillna(0.0).values
        else:
            price_change = np.diff(closes, prepend=closes[0]) / np.maximum(closes, 1e-9)

        n = len(signals)
        prob_gate_floor = max(0.25, float(min_confidence))

        # Per-side cost fractions: commission + transfer fee + (stamp tax on sell) + slippage.
        # `transaction_cost` is reused as the per-side slippage fraction.
        slippage = float(transaction_cost)
        if constraints is not None and TradingConstraints is not None:
            buy_cost = constraints.cost_rate("buy") + slippage
            sell_cost = constraints.cost_rate("sell") + slippage
        else:
            buy_cost = sell_cost = slippage

        # Simple on-the-fly regime detection from price data for adaptive entry gates
        def _detect_regime(idx: int) -> str:
            if idx < 20:
                return "range"
            lookback = closes[max(0, idx - 20):idx + 1]
            ret_20d = lookback[-1] / lookback[0] - 1.0
            vol_20d = float(np.std(np.diff(np.log(np.maximum(lookback, 1e-9)))))
            if vol_20d > 0.03:
                return "high_vol"
            if ret_20d > 0.015:
                return "bull"
            if ret_20d < -0.015:
                return "bear"
            return "range"

        # --- Constrained path (T+1, limit-up/down, slippage, stop-loss, confidence sizing) ---
        if constraints is not None and TradingConstraints is not None:
            prev_closes = np.concatenate([[closes[0]], closes[:-1]])
            position = np.zeros(n, dtype=float)
            hold_remaining = 0
            trade_signals = 0
            bought_today: set[int] = set()

            for i, sig in enumerate(signals):
                prob_up = (
                    float(ensemble_probs[i])
                    if ensemble_probs is not None and i < len(ensemble_probs)
                    else (1.0 if int(sig) == 1 else 0.0)
                )
                regime = _detect_regime(i)
                regime_gate = self.regime_entry_gates.get(regime, prob_gate_floor)
                go_long = prob_up >= max(prob_gate_floor, regime_gate)
                in_position = hold_remaining > 0
                t_plus_one_blocks = bool(constraints.enable_t_plus_one and i in bought_today)

                if in_position and t_plus_one_blocks:
                    position[i] = 1.0
                    hold_remaining = max(hold_remaining, 1)
                elif in_position and hold_remaining == 1:
                    prev_c = float(prev_closes[i])
                    blocked = False
                    if constraints.enable_limit_up_down and prev_c > 0 and closes[i] > 0:
                        change = abs(closes[i] / prev_c - 1.0)
                        if change >= constraints.limit_pct:
                            blocked = True
                    if blocked:
                        position[i] = 1.0
                        hold_remaining = 1
                    else:
                        position[i] = 0.0
                        hold_remaining = 0
                elif in_position:
                    position[i] = 1.0
                    hold_remaining -= 1
                elif go_long:
                    prev_c = float(prev_closes[i])
                    blocked = False
                    if constraints.enable_limit_up_down and prev_c > 0 and closes[i] > 0:
                        change = abs(closes[i] / prev_c - 1.0)
                        if change >= constraints.limit_pct:
                            blocked = True
                    if not blocked:
                        position[i] = 1.0
                        min_hold = 1 if constraints.enable_t_plus_one else 0
                        hold_remaining = max(min_hold, int(horizon) - 1)
                        trade_signals += 1
                        bought_today.add(i)

            entries = np.diff(position, prepend=0.0) > 0
            exits = np.diff(position, prepend=0.0) < 0
            daily_strategy = position * price_change - entries.astype(float) * buy_cost - exits.astype(float) * sell_cost
            equity = np.cumprod(1.0 + daily_strategy)
            buy_hold_equity = np.cumprod(1.0 + price_change)
            note = "T+1+limit+full-cost"
        # --- Simplified path (horizon hold, no extra exits) ---
        else:
            position = np.zeros(n, dtype=float)
            hold_remaining = 0
            trade_signals = 0
            for i, sig in enumerate(signals):
                prob_up = (
                    float(ensemble_probs[i])
                    if ensemble_probs is not None and i < len(ensemble_probs)
                    else (1.0 if int(sig) == 1 else 0.0)
                )
                regime = _detect_regime(i)
                regime_gate = self.regime_entry_gates.get(regime, prob_gate_floor)
                go_long = prob_up >= max(prob_gate_floor, regime_gate)
                if hold_remaining > 0:
                    position[i] = 1.0
                    hold_remaining -= 1
                elif go_long:
                    position[i] = 1.0
                    hold_remaining = max(0, int(horizon) - 1)
                    trade_signals += 1

            entries = np.diff(position, prepend=0.0) > 0
            exits = np.diff(position, prepend=0.0) < 0
            daily_strategy = position * price_change - entries.astype(float) * buy_cost - exits.astype(float) * sell_cost
            equity = np.cumprod(1.0 + daily_strategy)
            buy_hold_equity = np.cumprod(1.0 + price_change)
            note = "Simplified horizon hold + full-cost"

        active_mask = position > 0
        active_returns = daily_strategy[active_mask]
        win_rate = float(np.mean(active_returns > 0)) if len(active_returns) else 0.0
        vol = float(np.std(daily_strategy))
        sharpe = float(np.mean(daily_strategy) / (vol + 1e-9) * np.sqrt(252))

        return {
            "total_return": float(equity[-1] - 1.0) if len(equity) else 0.0,
            "buy_hold_return": float(buy_hold_equity[-1] - 1.0) if len(buy_hold_equity) else 0.0,
            "excess_return": float(equity[-1] - buy_hold_equity[-1]) if len(equity) else 0.0,
            "max_drawdown": self._max_drawdown(equity),
            "buy_hold_max_drawdown": self._max_drawdown(buy_hold_equity),
            "sharpe_ratio": sharpe,
            "win_rate": win_rate,
            "active_days": int(active_mask.sum()),
            "trade_signals": int(trade_signals),
            "min_confidence": float(min_confidence),
            "prob_gate": float(prob_gate_floor),
            "transaction_cost": float(transaction_cost),
            "equity_curve": [float(x) for x in equity.tolist()],
            "buy_hold_curve": [float(x) for x in buy_hold_equity.tolist()],
            "note": note,
        }

    def train(
        self,
        df: pd.DataFrame,
        horizon: int = 5,
        up_threshold: float = 0.02,
        *,
        fast: bool = False,
        label_method: str = "fixed_horizon",
        stop_loss_pct: float | None = None,
        progress_callback: object = None,
    ):
        cb = progress_callback  # local alias

        def _cb(event: dict) -> None:
            if cb is not None and callable(cb):
                try:
                    cb(event)
                except Exception:
                    pass

        self.label_method = label_method
        self.stop_loss_pct = stop_loss_pct

        _cb({"event": "phase", "phase": "prepare_features"})
        features_df = self.prepare_features(df)
        self.adopt_prepared_features()
        labels = self.prepare_labels(
            features_df, horizon=horizon, up_threshold=up_threshold,
            stop_loss_pct=stop_loss_pct, label_method=label_method,
        )
        features_df, labels = align_features_and_labels(features_df, labels)

        X = features_df[self.feature_columns]
        y = labels
        
        # Split data for weight learning
        if self.learn_weights:
            val_split = 0.2
            split_idx = int(len(X) * (1 - val_split))
            X_train = X.iloc[:split_idx]
            y_train = y.iloc[:split_idx]
            X_val = X.iloc[split_idx:]
            y_val = y.iloc[split_idx:]
            features_train = features_df.iloc[:split_idx]
            features_val = features_df.iloc[split_idx:]
        else:
            X_train = X
            y_train = y
            X_val = None
            y_val = None
            features_train = features_df
            features_val = None
        
        # Optional feature pruning. It must happen BEFORE anything is fitted,
        # otherwise the scaler and every model disagree with the inference matrix.
        if self.feature_selection and X_val is not None and y_val is not None and len(X_val) >= 50:
            self._select_features(X_val, y_val, min_features=20)
            selected = [c for c in self.active_feature_columns if c in features_df.columns]
            if selected and set(selected) != set(self.feature_columns):
                self.feature_columns = selected
                X = features_df[self.feature_columns]
                X_train = X.iloc[:split_idx]
                X_val = X.iloc[split_idx:]

        # The hold-out tail feeds several tuning decisions. Split it in two so
        # ensemble weights and regime thresholds/pruning are not all fitted on the
        # same rows. Below 100 rows we keep one block rather than starve both.
        if self.learn_weights and X_val is not None and len(X_val) >= 100:
            val_mid = split_idx + len(X_val) // 2
            X_val_w, y_val_w = X.iloc[split_idx:val_mid], y.iloc[split_idx:val_mid]
            features_val_w = features_df.iloc[split_idx:val_mid]
            X_val, y_val = X.iloc[val_mid:], y.iloc[val_mid:]
            features_val = features_df.iloc[val_mid:]
        else:
            X_val_w, y_val_w, features_val_w = X_val, y_val, features_val

        self.decision_threshold, self.probability_calibrator, _ = self._fit_validation_artifacts(
            X_train, y_train, features_train
        )
        self._train_vol_threshold = float(features_train["volatility_30"].quantile(0.75))
        X_scaled = self.scaler.fit_transform(X_train)

        self.model_scores = {}
        self.trained_models = {}
        time_cv = TimeSeriesSplit(n_splits=5)

        # Time-decay sample weights: recent data weighted more heavily (half-life ~252 days)
        n_train = len(X_scaled)
        decay_rate = np.log(2) / 252.0
        time_weights = np.exp(-decay_rate * np.arange(n_train - 1, -1, -1))
        time_weights = time_weights / time_weights.mean()  # normalize to mean=1

        for layer_name, model_name, model in self._iter_all_models():
            model_id = f"{layer_name}:{model_name}"
            _cb({"event": "model_training", "model_id": model_id, "layer": layer_name})
            cv_scores = cross_val_score(
                clone(model), X_scaled, y_train, cv=time_cv, scoring="accuracy",
            )
            model_instance = clone(model)
            model_instance.fit(X_scaled, y_train, sample_weight=time_weights)
            cv_mean = float(cv_scores.mean())
            cv_std = (
                float(np.std(cv_scores, ddof=1))
                if len(cv_scores) > 1
                else 0.0
            )
            self.trained_models[model_id] = model_instance
            self.model_scores[model_id] = {
                "layer": layer_name,
                "cv_mean": cv_mean,
                "cv_std": cv_std,
            }
            _cb({"event": "model_done", "model_id": model_id, "cv_mean": cv_mean, "cv_std": cv_std})

        self.global_regime_fallback = LogisticRegression(max_iter=2000, random_state=42)
        self.global_regime_fallback.fit(X_scaled, y_train, sample_weight=time_weights)

        regime_labels = self._derive_regime_labels(
            features_train, vol_threshold=self._train_vol_threshold
        )
        self.trained_regime_models = {}
        _cb({"event": "regime_start"})
        for regime in ["bull", "bear", "range", "high_vol"]:
            idx = regime_labels[regime_labels == regime].index
            if len(idx) < 80:
                _cb({"event": "regime_progress", "regime": regime, "status": "skipped"})
                continue
            X_regime = X_train.loc[idx]
            y_regime = y_train.loc[idx]
            idx_in_train = [list(X_train.index).index(i) for i in idx if i in X_train.index]
            regime_weights = time_weights[idx_in_train] if idx_in_train else None
            if y_regime.nunique() < 2:
                _cb({"event": "regime_progress", "regime": regime, "status": "skipped"})
                continue
            model = clone(self.regime_models[regime])
            model.fit(self.scaler.transform(X_regime), y_regime,
                      sample_weight=regime_weights)
            self.trained_regime_models[regime] = model
            _cb({"event": "regime_progress", "regime": regime, "status": "done"})
        _cb({"event": "regime_done"})

        # Filter weak models: exclude any model with CV accuracy < 50%
        # This prevents bad models from diluting ensemble predictions
        self.active_model_ids = set()
        for model_id, score in self.model_scores.items():
            if score["cv_mean"] >= 0.50:
                self.active_model_ids.add(model_id)
        # Always keep at least the best model
        if not self.active_model_ids and self.model_scores:
            best_id = max(self.model_scores, key=lambda k: self.model_scores[k]["cv_mean"])
            self.active_model_ids.add(best_id)

        # Train LSTM if enabled
        if self.lstm_enabled and self.lstm_model is not None:
            _cb({"event": "lstm_start"})
            try:
                X_train_scaled = self.scaler.transform(X_train)
                lstm_split = int(len(X_train_scaled) * 0.8)
                X_train_lstm = X_train_scaled[:lstm_split]
                y_train_lstm = y_train.iloc[:lstm_split].values
                X_val_lstm = X_train_scaled[lstm_split:]
                y_val_lstm = y_train.iloc[lstm_split:].values
                self.lstm_model.fit(X_train_lstm, y_train_lstm, X_val_lstm, y_val_lstm)
                _cb({"event": "lstm_done"})
            except Exception as exc:
                _cb({"event": "lstm_error", "error": str(exc)})
        else:
            _cb({"event": "lstm_skipped", "reason": "TensorFlow not available or LSTM disabled"})

        # Learn optimal weights if enabled
        if self.learn_weights and X_val_w is not None and self.weight_optimizer_available:
            _cb({"event": "weights_start"})
            self._learn_optimal_weights(X_val_w, y_val_w, features_val_w)
            _cb({"event": "weights_done"})
        else:
            _cb({"event": "weights_skipped"})

        # Compute feature importance from tree models
        self._compute_feature_importance()

        # Freeze the inference contract. prepare_features() rewrites
        # self.feature_columns on every call, so predict() must read this snapshot
        # instead -- previously the pruning above was silently undone before use.
        self.inference_columns = list(self.feature_columns)

        # Tune per-regime decision thresholds
        if X_val is not None and y_val is not None:
            self._tune_regime_thresholds(X_val, y_val, features_val)

        self.up_threshold = up_threshold
        self.is_trained = True
        _cb({"event": "training_complete"})

    def _compute_feature_importance(self) -> None:
        """Average feature importance from all tree-based trained models."""
        scores: Dict[str, List[float]] = {}
        for model_id, model in self.trained_models.items():
            if hasattr(model, 'feature_importances_'):
                for col, imp in zip(self.feature_columns, model.feature_importances_):
                    scores.setdefault(col, []).append(float(imp))
        self.feature_importance_scores = {
            col: float(np.mean(vals)) for col, vals in scores.items() if vals
        }
        self.active_feature_columns = list(self.feature_columns)

    def _select_features(self, X_val: pd.DataFrame, y_val: pd.Series, min_features: int = 20) -> None:
        """Drop features with negative or near-zero importance on validation data."""
        if len(X_val) < 50 or y_val.nunique() < 2:
            return
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import accuracy_score

        rf = RandomForestClassifier(n_estimators=80, max_depth=8, random_state=42, n_jobs=-1)
        rf.fit(X_val, y_val)
        baseline_acc = accuracy_score(y_val, rf.predict(X_val))

        importances: Dict[str, float] = {}
        for col in self.feature_columns:
            if col not in X_val.columns:
                continue
            X_perm = X_val.copy()
            X_perm[col] = np.random.permutation(X_perm[col].values)
            perm_acc = accuracy_score(y_val, rf.predict(X_perm))
            importances[col] = float(baseline_acc - perm_acc)

        # Keep features with positive importance
        kept = [col for col, imp in importances.items() if imp > 0.0]
        if len(kept) < min_features:
            # Fall back to top-N by importance
            kept = sorted(importances, key=lambda c: importances[c], reverse=True)[:min_features]

        self.active_feature_columns = kept

    def _tune_regime_thresholds(
        self, X_val: pd.DataFrame, y_val: pd.Series, features_val: pd.DataFrame
    ) -> None:
        """Tune per-regime decision thresholds to improve precision per market state."""
        if y_val.nunique() < 2 or len(X_val) < 40:
            self.regime_decision_thresholds = {}
            return
        from sklearn.metrics import f1_score
        X_val_scaled = self.scaler.transform(X_val)
        regime_labels = self._derive_regime_labels(features_val, vol_threshold=self._train_vol_threshold)

        for regime in ['bull', 'bear', 'range', 'high_vol']:
            idx = regime_labels[regime_labels == regime].index
            if len(idx) < 20:
                continue
            model = self.trained_regime_models.get(regime)
            if model is None:
                continue
            X_r = X_val.loc[idx]
            y_r = y_val.loc[idx]
            if y_r.nunique() < 2:
                continue
            probs = model.predict_proba(self.scaler.transform(X_r))[:, 1]
            best_t = 0.5
            best_f1 = -1.0
            for t in np.linspace(0.3, 0.7, 21):
                preds = (probs > t).astype(int)
                f1 = float(f1_score(y_r, preds, pos_label=1, zero_division=0))
                if f1 > best_f1:
                    best_f1 = f1
                    best_t = float(t)
            self.regime_decision_thresholds[regime] = best_t

    def _learn_optimal_weights(self, X_val: pd.DataFrame, y_val: pd.Series, features_val: pd.DataFrame):
        """
        Learn optimal ensemble weights from validation data using hierarchical optimization
        
        This addresses the criticism: "Hard-coded weights - where do these percentages come from?"
        Now weights are LEARNED from data, not hard-coded.
        """
        # Get predictions from all models on validation data
        X_val_scaled = self.scaler.transform(X_val)
        
        layer_predictions = {}
        
        # Collect baseline layer predictions
        layer_predictions['baseline'] = {}
        for model_id, model in self.trained_models.items():
            if model_id.startswith('baseline:'):
                model_name = model_id.split(':')[1]
                proba = model.predict_proba(X_val_scaled)[:, 1]
                layer_predictions['baseline'][model_name] = proba
        
        # Collect enhanced layer predictions
        layer_predictions['enhanced'] = {}
        for model_id, model in self.trained_models.items():
            if model_id.startswith('enhanced:'):
                model_name = model_id.split(':')[1]
                proba = model.predict_proba(X_val_scaled)[:, 1]
                layer_predictions['enhanced'][model_name] = proba
        
        # Collect regime layer predictions
        regime_labels_val = self._derive_regime_labels(features_val, vol_threshold=self._train_vol_threshold)
        regime_probs = []
        for i in range(len(X_val)):
            regime = regime_labels_val.iloc[i]
            model = self.trained_regime_models.get(regime, self.global_regime_fallback)
            prob = model.predict_proba(X_val_scaled[i:i+1])[0, 1]
            regime_probs.append(prob)
        layer_predictions['regime'] = {'regime': np.array(regime_probs)}
        
        # Add LSTM predictions if available
        if self.lstm_enabled and self.lstm_model is not None:
            lstm_proba = self.lstm_model.predict_proba(X_val_scaled)
            seq_len = self.lstm_model.sequence_length
            
            # Align all predictions to LSTM length
            aligned_layer_predictions = {}
            for layer_name, models in layer_predictions.items():
                aligned_layer_predictions[layer_name] = {
                    model_name: preds[seq_len:] 
                    for model_name, preds in models.items()
                }
            
            aligned_layer_predictions['lstm'] = {'lstm': lstm_proba}
            layer_predictions = aligned_layer_predictions
            y_val_aligned = y_val.iloc[seq_len:].values
        else:
            y_val_aligned = y_val.values
        
        # Hierarchical weight optimization (F1-based)
        result = self._hierarchical_weight_optimization(
            layer_predictions,
            y_val_aligned,
            method='stacking',
            verbose=False
        )

        self.within_layer_weights = result['within_layer_weights']
        self.learned_layer_weights = result['layer_weights']

        # Secondary Sharpe-based fine-tuning on layer weights
        if hasattr(features_val, 'columns') and 'price_change' in features_val.columns:
            try:
                layer_predictions_sharpe = {}
                for layer_name in ['baseline', 'enhanced', 'regime']:
                    if layer_name in layer_predictions and layer_name in self.within_layer_weights:
                        within_w = self.within_layer_weights[layer_name]
                        layer_pred = sum(
                            within_w[name] * preds
                            for name, preds in layer_predictions[layer_name].items()
                        )
                        layer_predictions_sharpe[layer_name] = layer_pred

                if layer_predictions_sharpe:
                    from .weight_optimizer import EnsembleWeightOptimizer
                    sharpe_opt = EnsembleWeightOptimizer(method='stacking')
                    sharpe_result = sharpe_opt.fit_sharpe(
                        layer_predictions_sharpe,
                        y_val_aligned,
                        features_val['price_change'].iloc[:len(y_val_aligned)].fillna(0).values,
                        horizon=self.horizon if hasattr(self, 'horizon') else 5,
                        verbose=False,
                    )
                    # Blend: 60% F1-based, 40% Sharpe-based layer weights
                    for layer in self.learned_layer_weights:
                        if layer in sharpe_result:
                            self.learned_layer_weights[layer] = (
                                0.6 * self.learned_layer_weights[layer] + 0.4 * sharpe_result[layer]
                            )
            except Exception:
                pass  # Sharpe fine-tuning is optional; F1 weights are already good

        # Update layer_weights for compatibility
        self.layer_weights = self.learned_layer_weights

    def _predict_layer_probs(self, latest_scaled: np.ndarray) -> Dict[str, float]:
        probs = {"baseline": [], "enhanced": []}
        weights = {"baseline": [], "enhanced": []}
        model_probs = {}

        for model_id, model in self.trained_models.items():
            if self.active_model_ids and model_id not in self.active_model_ids:
                continue  # skip weak models (CV < 50%)
            layer = model_id.split(":", 1)[0]
            prob = model.predict_proba(latest_scaled)[0]
            up_prob = float(prob[1])
            # Weight by CV score so good models dominate the ensemble
            cv_w = max(0.0, self.model_scores.get(model_id, {}).get("cv_mean", 0.5) - 0.45)
            probs[layer].append(up_prob * cv_w)
            weights[layer].append(cv_w)
            model_probs[model_id] = {"down": float(prob[0]), "up": up_prob}

        layer_up = {}
        for layer in ["baseline", "enhanced"]:
            if weights[layer] and sum(weights[layer]) > 0:
                layer_up[layer] = float(sum(probs[layer]) / sum(weights[layer]))
            else:
                layer_up[layer] = 0.5
        return {"layer_up": layer_up, "model_probs": model_probs}

    def predict(self, df: pd.DataFrame, horizon: int = 5) -> Dict:
        if not self.is_trained:
            raise ValueError("Model is not trained")

        features_df = self.prepare_features(df)
        columns = list(self.inference_columns or self.feature_columns)
        latest_features = features_df[columns].iloc[-1:]
        latest_scaled = self.scaler.transform(latest_features.values)

        layer_outputs = self._predict_layer_probs(latest_scaled)
        layer_up = layer_outputs["layer_up"]
        probabilities = layer_outputs["model_probs"]
        individual_predictions = {
            model_id: int(prob["up"] > 0.5) for model_id, prob in probabilities.items()
        }

        vol_threshold = float(self._train_vol_threshold or features_df["volatility_30"].quantile(0.75))
        regime = self._latest_regime(features_df.iloc[-1], vol_threshold)
        regime_model = self.trained_regime_models.get(regime, self.global_regime_fallback)
        regime_prob = regime_model.predict_proba(latest_scaled)[0]
        regime_up = float(regime_prob[1])
        probabilities[f"regime:{regime}"] = {"down": float(regime_prob[0]), "up": regime_up}
        individual_predictions[f"regime:{regime}"] = int(regime_up > 0.5)

        # Add LSTM prediction if available
        lstm_up = None
        if self.lstm_enabled and self.lstm_model is not None:
            # Get more features for sequence
            sequence_features = features_df[columns].iloc[-self.lstm_model.sequence_length:]
            if len(sequence_features) >= self.lstm_model.sequence_length:
                sequence_scaled = self.scaler.transform(sequence_features.values)
                lstm_proba = self.lstm_model.predict_proba(sequence_scaled)
                lstm_up = float(lstm_proba[-1])  # Last prediction
                probabilities["lstm:lstm"] = {"down": 1.0 - lstm_up, "up": lstm_up}
                individual_predictions["lstm:lstm"] = int(lstm_up > 0.5)

        # Calculate ensemble prediction using learned weights if available
        if self.learned_layer_weights:
            # Use learned weights
            weights = self.learned_layer_weights
            ensemble_up_raw = (
                weights.get("baseline", 0.35) * layer_up["baseline"] +
                weights.get("enhanced", 0.40) * layer_up["enhanced"] +
                weights.get("regime", 0.25) * regime_up
            )
            if lstm_up is not None and "lstm" in weights:
                # Adjust weights if LSTM is included — normalize to prevent unbounded ensemble
                total_trad = weights.get("baseline", 0) + weights.get("enhanced", 0) + weights.get("regime", 0)
                lstm_weight = weights.get("lstm", 0)
                total_weight = total_trad + lstm_weight
                if total_weight > 0:
                    ensemble_up_raw = (
                        weights.get("baseline", 0) * layer_up["baseline"] +
                        weights.get("enhanced", 0) * layer_up["enhanced"] +
                        weights.get("regime", 0) * regime_up +
                        lstm_weight * lstm_up
                    ) / total_weight
        else:
            # Use fixed weights
            ensemble_up_raw = _clip01(
                self.layer_weights["baseline"] * layer_up["baseline"]
                + self.layer_weights["enhanced"] * layer_up["enhanced"]
                + self.layer_weights["regime"] * regime_up
            )
            if lstm_up is not None:
                # Include LSTM with fixed weight (25%)
                ensemble_up_raw = 0.25 * layer_up["baseline"] + 0.30 * layer_up["enhanced"] + 0.20 * regime_up + 0.25 * lstm_up
        
        ensemble_up_raw = _clip01(ensemble_up_raw)
        ensemble_up = float(
            self._calibrate_probs(
                self.probability_calibrator, np.array([ensemble_up_raw])
            )[0]
        )
        ensemble_up = _clip01(ensemble_up)
        # Use regime-specific threshold when available, fall back to global threshold
        if self.regime_decision_thresholds and regime in self.regime_decision_thresholds:
            decision_threshold = self.regime_decision_thresholds[regime]
        else:
            decision_threshold = float(getattr(self, "decision_threshold", 0.5) or 0.5)
        model_up_values = [x["up"] for x in probabilities.values()]
        agreement = _clip01(1 - (np.std(model_up_values) * 2))
        direction_strength = abs(ensemble_up - 0.5) * 2
        confidence = _clip01(0.6 * direction_strength + 0.4 * agreement)

        # Separate model direction from an executable research signal. The
        # previous threshold-only rule could call a 38% probability "up" even
        # when every constituent model was bearish. A signal is tradeable only
        # when probability, confidence and model agreement all clear floors.
        raw_direction = 1 if ensemble_up > decision_threshold else 0
        bullish_votes = sum(1 for value in model_up_values if value >= 0.5)
        vote_ratio = bullish_votes / max(len(model_up_values), 1)
        trade_reasons = []
        if ensemble_up < 0.60:
            trade_reasons.append("probability_below_60pct")
        if confidence < 0.60:
            trade_reasons.append("confidence_below_60pct")
        if raw_direction == 1 and vote_ratio < 0.50:
            trade_reasons.append("model_consensus_below_50pct")
        trade_allowed = not trade_reasons and raw_direction == 1
        ensemble_prediction = 1 if trade_allowed else 0

        return {
            "prediction": ensemble_prediction,
            "raw_prediction": raw_direction,
            "trade_allowed": trade_allowed,
            "trade_reasons": trade_reasons,
            "confidence": confidence,
            "individual_predictions": individual_predictions,
            "probabilities": probabilities,
            "horizon": horizon,
            "up_threshold": self.up_threshold,
            "decision_threshold": decision_threshold,
            "model_scores": self.model_scores,
            "layer_outputs": {
                "baseline_up": round(layer_up["baseline"], 4),
                "enhanced_up": round(layer_up["enhanced"], 4),
                "regime_up": round(regime_up, 4),
                "lstm_up": round(lstm_up, 4) if lstm_up is not None else None,
                "regime": regime,
                "ensemble_up": round(ensemble_up, 4),
                "ensemble_up_raw": round(float(ensemble_up_raw), 4),
                "bullish_vote_ratio": round(vote_ratio, 4),
                "trade_allowed": trade_allowed,
                "weights_learned": bool(self.learned_layer_weights),
                "lstm_enabled": self.lstm_enabled,
            },
            "calibration_applied": self.probability_calibrator is not None,
        }

    def _backtest_ml_core(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        features_df: pd.DataFrame,
        test_size: float = 0.2,
        horizon: int = 0,
        min_confidence: float = 0.0,
    ) -> Dict[str, Dict]:
        train_end, test_start = purged_train_test_split(len(X), test_size=test_size, horizon=horizon)
        if train_end < 80 or len(X) - test_start < 10:
            raise ValueError("Insufficient samples after purged split for backtest")

        train_start = 0  # use all available training data
        X_train = X.iloc[train_start:train_end]
        X_test = X.iloc[test_start:]
        y_train = y.iloc[train_start:train_end]
        y_test = y.iloc[test_start:]
        feature_train = features_df.iloc[train_start:train_end]
        feature_test = features_df.iloc[test_start:]
        train_vol_threshold = float(feature_train["volatility_30"].quantile(0.75))

        decision_threshold, calibrator, calibration_fit = self._fit_validation_artifacts(
            X_train, y_train, feature_train
        )
        bundle = self._fit_ensemble_bundle(X_train, y_train, feature_train)
        trained: Dict[str, object] = bundle["trained_models"]
        scaler = bundle["scaler"]
        X_test_scaled = scaler.transform(X_test)

        layer_predictions: Dict[str, List[int]] = {"baseline": [], "enhanced": []}
        layer_up_probs: Dict[str, List[float]] = {"baseline": [], "enhanced": []}
        results: Dict[str, Dict] = {}

        for model_id, model_inst in trained.items():
            layer_name = model_id.split(":", 1)[0]
            y_pred = model_inst.predict(X_test_scaled)
            y_prob = model_inst.predict_proba(X_test_scaled)
            layer_predictions[layer_name].append(y_pred.astype(int))
            layer_up_probs[layer_name].append(y_prob[:, 1])
            results[model_id] = {
                **self._eval_metrics(y_test, y_pred),
                "predictions": y_pred.tolist(),
                "probabilities": y_prob.tolist(),
            }

        baseline_vote = (
            np.mean(layer_predictions["baseline"], axis=0) if layer_predictions["baseline"] else 0.5
        )
        enhanced_vote = (
            np.mean(layer_predictions["enhanced"], axis=0) if layer_predictions["enhanced"] else 0.5
        )
        baseline_up = (
            np.mean(layer_up_probs["baseline"], axis=0)
            if layer_up_probs["baseline"]
            else np.full(len(y_test), 0.5)
        )
        enhanced_up = (
            np.mean(layer_up_probs["enhanced"], axis=0)
            if layer_up_probs["enhanced"]
            else np.full(len(y_test), 0.5)
        )

        regime_labels_test = self._derive_regime_labels(feature_test, vol_threshold=train_vol_threshold)
        regime_models = bundle["regime_models"]
        global_regime_fallback = bundle["global_regime_fallback"]
        regime_up_probs = []
        regime_preds = []
        for i in range(len(feature_test)):
            regime = regime_labels_test.iloc[i]
            model = regime_models.get(regime, global_regime_fallback)
            row_scaled = X_test_scaled[i : i + 1]
            p = float(model.predict_proba(row_scaled)[0, 1])
            regime_up_probs.append(p)
            regime_preds.append(int(p > decision_threshold))

        ensemble_up_raw = self._predict_ensemble_up(bundle, X_test, feature_test)
        ensemble_up = self._calibrate_probs(calibrator, ensemble_up_raw)
        ensemble_preds = (ensemble_up > decision_threshold).astype(int).tolist()
        pnl_backtest = self._simulate_pnl_backtest(
            feature_test,
            ensemble_preds,
            horizon,
            ensemble_probs=ensemble_up,
            decision_threshold=decision_threshold,
            min_confidence=float(min_confidence or 0.0),
            constraints=TradingConstraints() if TradingConstraints is not None else None,
        )
        calibration_test = {
            "enabled": calibrator is not None,
            "brier_raw": float(brier_score_loss(y_test.astype(int), ensemble_up_raw)),
            "brier_calibrated": float(brier_score_loss(y_test.astype(int), ensemble_up)),
            "brier_improvement": float(
                brier_score_loss(y_test.astype(int), ensemble_up_raw)
                - brier_score_loss(y_test.astype(int), ensemble_up)
            ),
            "fit": calibration_fit,
        }

        baseline_layer_preds = (baseline_vote > decision_threshold).astype(int).tolist()
        enhanced_layer_preds = (enhanced_vote > decision_threshold).astype(int).tolist()
        results["layer:baseline"] = {
            **self._eval_metrics(y_test, baseline_layer_preds),
            "predictions": baseline_layer_preds,
        }
        results["layer:enhanced"] = {
            **self._eval_metrics(y_test, enhanced_layer_preds),
            "predictions": enhanced_layer_preds,
        }
        results["layer:regime"] = {
            **self._eval_metrics(y_test, regime_preds),
            "predictions": regime_preds,
        }
        results["ensemble"] = {
            **self._eval_metrics(y_test, ensemble_preds),
            "predictions": ensemble_preds,
        }

        baseline_accuracy = float(max(y_test.mean(), 1 - y_test.mean()))
        results["walk_forward"] = self._walk_forward_eval(
            X, y, features_df, test_start, horizon=horizon
        )

        return {
            "results": results,
            "test_size": int(len(y_test)),
            "train_size": int(len(y_train)),
            "purged_embargo": int(horizon),
            "decision_threshold": float(decision_threshold),
            "baseline_accuracy": baseline_accuracy,
            "improvement": float(results["ensemble"]["accuracy"] - baseline_accuracy),
            "feature_importance": self._get_feature_importance(trained),
            "pnl_backtest": pnl_backtest,
            "calibration": calibration_test,
        }

    def _backtest_ml(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        features_df: pd.DataFrame,
        test_size: float = 0.2,
        horizon: int = 0,
        min_confidence: float = 0.0,
    ) -> Dict[str, Dict]:
        if len(X) > 700:
            X_eval = X.iloc[-700:]
            y_eval = y.iloc[-700:]
            features_eval = features_df.iloc[-700:]
        else:
            X_eval = X
            y_eval = y
            features_eval = features_df

        return self._backtest_ml_core(
            X_eval, y_eval, features_eval, test_size, horizon=horizon, min_confidence=min_confidence
        )

    def _walk_forward_eval(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        features_df: pd.DataFrame,
        test_start: int,
        horizon: int = 0,
    ) -> Dict[str, float]:
        if len(X) - test_start <= 0:
            return {"samples": 0, "accuracy": 0.0, "method": "ensemble_walk_forward"}

        eval_indices = list(range(test_start, len(X)))
        max_steps = 12
        if len(eval_indices) > max_steps:
            step = max(1, len(eval_indices) // max_steps)
            eval_indices = eval_indices[::step]

        preds = []
        truths = []
        for idx in eval_indices:
            train_end = idx - max(0, int(horizon))
            if train_end < 80:
                continue
            X_train = X.iloc[:train_end]
            y_train = y.iloc[:train_end]
            feature_train = features_df.iloc[:train_end]
            y_cur = int(y.iloc[idx])

            decision_threshold, calibrator, _ = self._fit_validation_artifacts(
                X_train, y_train, feature_train
            )
            bundle = self._fit_ensemble_bundle(X_train, y_train, feature_train)
            prob_raw = float(
                self._predict_ensemble_up(
                    bundle, X.iloc[idx : idx + 1], features_df.iloc[idx : idx + 1]
                )[0]
            )
            prob = float(self._calibrate_probs(calibrator, np.array([prob_raw]))[0])
            pred = int(prob > decision_threshold)
            preds.append(pred)
            truths.append(y_cur)

        if not truths:
            return {"samples": 0, "accuracy": 0.0, "method": "ensemble_walk_forward"}

        return {
            "samples": len(truths),
            "accuracy": float(accuracy_score(truths, preds)),
            "method": "ensemble_walk_forward",
        }

    def backtest_multi_fold(
        self,
        df: pd.DataFrame,
        horizon: int = 5,
        test_size_per_fold: float = 0.15,
        n_folds: int = 3,
        up_threshold: float = 0.02,
        label_method: str = "triple_barrier",
    ) -> Dict[str, Any]:
        """Purged expanding-window multi-fold backtest.

        Splits the test period into N contiguous windows. For each window,
        trains on all data before it and tests on the window. Reports mean
        and std of PnL metrics across folds for honest evaluation.
        """
        features_df = self.prepare_features(df)
        labels = self.prepare_labels(
            features_df, horizon=horizon, up_threshold=up_threshold,
            label_method=label_method,
        )
        features_df, labels = align_features_and_labels(features_df, labels)
        self.adopt_prepared_features()
        X = features_df[self.feature_columns]
        y = labels

        total_n = len(X)
        fold_size = int(total_n * test_size_per_fold)
        if total_n < 200 or fold_size < 50:
            raise ValueError(f"Data too small for multi-fold: {total_n} rows")

        fold_metrics = []
        for fold, (train_start, train_end, test_start, test_end) in enumerate(
            self.walk_forward_folds(total_n, n_folds, test_size_per_fold, horizon)
        ):
            if train_end < 80 or test_end - test_start < 30:
                continue

            X_train = X.iloc[train_start:train_end]
            y_train = y.iloc[train_start:train_end]
            feature_train = features_df.iloc[train_start:train_end]
            X_test = X.iloc[test_start:test_end]
            y_test = y.iloc[test_start:test_end]
            feature_test = features_df.iloc[test_start:test_end]

            if y_train.nunique() < 2 or y_test.nunique() < 2:
                continue

            bundle = self._fit_ensemble_bundle(X_train, y_train, feature_train)
            scaler = bundle["scaler"]
            X_test_scaled = scaler.transform(X_test)

            decision_threshold, calibrator, _ = self._fit_validation_artifacts(
                X_train, y_train, feature_train
            )

            ensemble_up_raw = self._predict_ensemble_up(bundle, X_test, feature_test)
            ensemble_up = self._calibrate_probs(calibrator, ensemble_up_raw)
            ensemble_preds = (ensemble_up > decision_threshold).astype(int).tolist()

            pnl = self._simulate_pnl_backtest(
                feature_test, ensemble_preds, horizon,
                ensemble_probs=ensemble_up,
                decision_threshold=decision_threshold,
                min_confidence=0.0,
                constraints=TradingConstraints() if TradingConstraints is not None else None,
            )

            fold_eval = self._eval_metrics(y_test, ensemble_preds)
            fold_metrics.append({
                "fold": fold,
                "test_days": test_end - test_start,
                "train_days": train_end - train_start,
                "accuracy": fold_eval["accuracy"],
                "baseline_accuracy": fold_eval["baseline_accuracy"],
                "edge": fold_eval["edge"],
                "balanced_accuracy": fold_eval["balanced_accuracy"],
                "mcc": fold_eval["mcc"],
                "sharpe": pnl["sharpe_ratio"],
                "total_return": pnl["total_return"],
                "excess_return": pnl["excess_return"],
                "buy_hold_return": pnl["buy_hold_return"],
                "max_drawdown": pnl["max_drawdown"],
                "win_rate": pnl["win_rate"],
                "trade_signals": pnl["trade_signals"],
            })

        if not fold_metrics:
            raise ValueError("No valid folds produced")

        # Aggregate
        sharpes = [m["sharpe"] for m in fold_metrics]
        returns = [m["total_return"] for m in fold_metrics]
        excesses = [m["excess_return"] for m in fold_metrics]
        maxdds = [m["max_drawdown"] for m in fold_metrics]
        wins = [m["win_rate"] for m in fold_metrics]
        sigs = [m["trade_signals"] for m in fold_metrics]
        accs = [m["accuracy"] for m in fold_metrics]
        edges = [m["edge"] for m in fold_metrics]
        baselines = [m["baseline_accuracy"] for m in fold_metrics]
        n_eval_total = int(sum(m["test_days"] for m in fold_metrics))
        pooled_edge = float(np.mean(accs) - np.mean(baselines))

        return {
            "n_folds": len(fold_metrics),
            "method": "purged_expanding_window",
            "label_method": label_method,
            "horizon": horizon,
            "accuracy_mean": float(np.mean(accs)),
            "accuracy_std": float(np.std(accs, ddof=1)) if len(accs) > 1 else 0.0,
            # Headline honesty metrics: raw accuracy is dominated by the class
            # imbalance, so always read it together with the baseline and edge.
            "baseline_accuracy_mean": float(np.mean(baselines)),
            "edge_mean": float(np.mean(edges)),
            "edge_pooled": pooled_edge,
            "edge_std": float(np.std(edges, ddof=1)) if len(edges) > 1 else 0.0,
            "n_out_of_sample": n_eval_total,
            "sharpe_mean": float(np.mean(sharpes)),
            "sharpe_std": float(np.std(sharpes, ddof=1)) if len(sharpes) > 1 else 0.0,
            "total_return_mean": float(np.mean(returns)),
            "total_return_std": float(np.std(returns, ddof=1)) if len(returns) > 1 else 0.0,
            "excess_return_mean": float(np.mean(excesses)),
            "max_drawdown_mean": float(np.mean(maxdds)),
            "max_drawdown_worst": float(np.min(maxdds)),
            "win_rate_mean": float(np.mean(wins)),
            "trade_signals_mean": float(np.mean(sigs)),
            "trade_signals_total": int(sum(sigs)),
            "folds": fold_metrics,
        }

    def _backtest_rule_ma_cross(
        self, features_df: pd.DataFrame, labels: pd.Series, test_size: float, horizon: int = 0
    ):
        _, test_start = purged_train_test_split(len(features_df), test_size=test_size, horizon=horizon)
        test_features = features_df.iloc[test_start:]
        y_test = labels.iloc[test_start:]

        y_pred = (test_features["ma5"] > test_features["ma20"]).astype(int).tolist()
        metrics = self._eval_metrics(y_test, y_pred)
        baseline_accuracy = float(max(y_test.mean(), 1 - y_test.mean()))

        return {
            "results": {"ma_cross": {**metrics, "predictions": y_pred}},
            "test_size": int(len(y_test)),
            "baseline_accuracy": baseline_accuracy,
            "improvement": float(metrics["accuracy"] - baseline_accuracy),
            "feature_importance": {},
        }

    def _backtest_rule_rsi_reversion(
        self, features_df: pd.DataFrame, labels: pd.Series, test_size: float, horizon: int = 0
    ):
        _, test_start = purged_train_test_split(len(features_df), test_size=test_size, horizon=horizon)
        test_features = features_df.iloc[test_start:]
        y_test = labels.iloc[test_start:]

        y_pred = []
        for _, row in test_features.iterrows():
            if row["rsi"] <= 30:
                y_pred.append(1)
            elif row["rsi"] >= 70:
                y_pred.append(0)
            else:
                y_pred.append(1 if row["close_price"] > row["ma20"] else 0)

        metrics = self._eval_metrics(y_test, y_pred)
        baseline_accuracy = float(max(y_test.mean(), 1 - y_test.mean()))

        return {
            "results": {"rsi_reversion": {**metrics, "predictions": y_pred}},
            "test_size": int(len(y_test)),
            "baseline_accuracy": baseline_accuracy,
            "improvement": float(metrics["accuracy"] - baseline_accuracy),
            "feature_importance": {},
        }

    def backtest(
        self,
        df: pd.DataFrame,
        horizon: int = 5,
        test_size: float = 0.2,
        strategy: str = "ensemble_ml",
        up_threshold: float = 0.02,
        min_confidence: float = 0.0,
        label_method: str = "fixed_horizon",
        stop_loss_pct: float | None = None,
    ) -> Dict:
        features_df = self.prepare_features(df)
        labels = self.prepare_labels(
            features_df, horizon=horizon, up_threshold=up_threshold,
            stop_loss_pct=stop_loss_pct, label_method=label_method,
        )
        features_df, labels = align_features_and_labels(features_df, labels)
        self.adopt_prepared_features()

        X = features_df[self.feature_columns]
        y = labels

        strategy = (strategy or "ensemble_ml").lower()
        if strategy in {"default", "ensemble", "ml"}:
            strategy = "ensemble_ml"

        if strategy == "ma_cross":
            result = self._backtest_rule_ma_cross(features_df, y, test_size, horizon=horizon)
        elif strategy == "rsi_reversion":
            result = self._backtest_rule_rsi_reversion(features_df, y, test_size, horizon=horizon)
        else:
            result = self._backtest_ml(
                X, y, features_df, test_size, horizon=horizon, min_confidence=min_confidence
            )

        result.update(
            {
                "horizon": horizon,
                "strategy": strategy,
                "up_threshold": up_threshold,
                "label_method": label_method,
                "stop_loss_pct": stop_loss_pct,
            }
        )
        return result

    def _get_feature_importance(self, trained_models: Dict[str, object]) -> Dict[str, Dict[str, float]]:
        importance = {}
        for name, model in trained_models.items():
            if hasattr(model, "feature_importances_"):
                importance[name] = dict(
                    zip(self.feature_columns, [float(x) for x in model.feature_importances_])
                )
        return importance

    def get_prediction_explanation(self, prediction_result: Dict) -> str:
        pred = prediction_result["prediction"]
        confidence = prediction_result["confidence"]
        horizon = prediction_result["horizon"]
        layer_outputs = prediction_result.get("layer_outputs", {})

        direction = "上涨" if pred == 1 else "下跌"
        confidence_level = "高" if confidence > 0.7 else "中" if confidence > 0.5 else "低"

        lines = [
            f"预测结果：未来 {horizon} 天更可能{direction}。",
            f"置信度：{confidence_level}（{confidence:.1%}）。",
            "三层模型输出：",
            f"- 基线层上涨概率: {layer_outputs.get('baseline_up', 0):.2f}",
            f"- 增强层上涨概率: {layer_outputs.get('enhanced_up', 0):.2f}",
            f"- 制度层({layer_outputs.get('regime', 'range')})上涨概率: {layer_outputs.get('regime_up', 0):.2f}",
            f"- 综合上涨概率: {layer_outputs.get('ensemble_up', 0):.2f}",
            f"- 决策阈值: {prediction_result.get('decision_threshold', 0.5):.2f}",
            "风险提示：结果基于历史统计特征，不构成投资建议，请结合基本面与风险承受能力综合判断。",
        ]
        return "\n".join(lines)
