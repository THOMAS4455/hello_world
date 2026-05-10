#!/usr/bin/env python3
"""
Three-layer predictor used by the FastAPI prediction service.
Layer-1: baseline tree models
Layer-2: enhanced statistical/boosting models
Layer-3: regime-aware model routing
"""

from __future__ import annotations

import warnings
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

warnings.filterwarnings("ignore")


def _clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


SENTIMENT_COLUMNS = [
    "sentiment_score_lag1",
    "sentiment_confidence_lag1",
    "positive_ratio_lag1",
    "negative_ratio_lag1",
    "market_breadth_lag1",
    "target_match_count_lag1",
    "sentiment_decay_lag1",
    "sentiment_available",
]


class ImprovedPredictor:
    def __init__(self) -> None:
        self.layer_models = {
            "baseline": {
                "rf": RandomForestClassifier(n_estimators=160, random_state=42),
                "gb": GradientBoostingClassifier(n_estimators=160, random_state=42),
            },
            "enhanced": {
                "extra_trees": ExtraTreesClassifier(n_estimators=220, random_state=42),
                "log_reg": LogisticRegression(max_iter=2000, random_state=42),
                "svm": SVC(kernel="rbf", probability=True, random_state=42),
            },
        }
        self.regime_models = {
            "bull": LogisticRegression(max_iter=2000, random_state=42),
            "bear": LogisticRegression(max_iter=2000, random_state=42),
            "range": LogisticRegression(max_iter=2000, random_state=42),
            "high_vol": LogisticRegression(max_iter=2000, random_state=42),
        }
        self.scaler = StandardScaler()
        self.feature_columns: List[str] = []
        self.is_trained = False
        self.model_scores: Dict[str, Dict[str, float]] = {}
        self.layer_weights = {"baseline": 0.35, "enhanced": 0.4, "regime": 0.25}
        self.up_threshold = 0.02
        self.trained_models: Dict[str, object] = {}
        self.trained_regime_models: Dict[str, object] = {}
        self.global_regime_fallback = LogisticRegression(max_iter=2000, random_state=42)

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        features = df.copy()

        features["ma5"] = features["close_price"].rolling(window=5).mean()
        features["ma10"] = features["close_price"].rolling(window=10).mean()
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

        for col in SENTIMENT_COLUMNS:
            if col not in features.columns:
                features[col] = 0.0
        features[SENTIMENT_COLUMNS] = features[SENTIMENT_COLUMNS].fillna(0.0)

        features = features.replace([np.inf, -np.inf], np.nan).dropna()

        base_columns = [
            "ma5",
            "ma10",
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
        ]
        self.feature_columns = base_columns + SENTIMENT_COLUMNS
        return features

    def prepare_labels(
        self, df: pd.DataFrame, horizon: int = 5, up_threshold: float = 0.02
    ) -> pd.Series:
        future_return = df["close_price"].shift(-horizon) / df["close_price"] - 1
        return (future_return > up_threshold).astype(int)

    def _derive_regime_labels(self, features_df: pd.DataFrame) -> pd.Series:
        labels = []
        vol_threshold = features_df["volatility_30"].quantile(0.75)
        for _, row in features_df.iterrows():
            trend = float(row.get("trend_strength", 0.0))
            vol = float(row.get("volatility_30", 0.0))
            if vol >= vol_threshold:
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

    def _eval_metrics(self, y_true, y_pred) -> Dict[str, float]:
        return {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(
                precision_score(y_true, y_pred, average="weighted", zero_division=0)
            ),
            "recall": float(
                recall_score(y_true, y_pred, average="weighted", zero_division=0)
            ),
            "f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        }

    def _iter_all_models(self) -> List[Tuple[str, str, object]]:
        out = []
        for layer_name, models in self.layer_models.items():
            for model_name, model in models.items():
                out.append((layer_name, model_name, model))
        return out

    def train(self, df: pd.DataFrame, horizon: int = 5, up_threshold: float = 0.02):
        features_df = self.prepare_features(df)
        labels = self.prepare_labels(features_df, horizon=horizon, up_threshold=up_threshold)

        min_length = min(len(features_df), len(labels))
        features_df = features_df.iloc[:min_length]
        labels = labels.iloc[:min_length]

        X = features_df[self.feature_columns]
        y = labels
        X_scaled = self.scaler.fit_transform(X)

        self.model_scores = {}
        self.trained_models = {}
        time_cv = TimeSeriesSplit(n_splits=5)

        for layer_name, model_name, model in self._iter_all_models():
            model_instance = clone(model)
            cv_scores = cross_val_score(model_instance, X_scaled, y, cv=time_cv, scoring="accuracy")
            model_instance.fit(X_scaled, y)
            model_id = f"{layer_name}:{model_name}"
            self.trained_models[model_id] = model_instance
            self.model_scores[model_id] = {
                "layer": layer_name,
                "cv_mean": float(cv_scores.mean()),
                "cv_std": float(cv_scores.std()),
            }

        self.global_regime_fallback = LogisticRegression(max_iter=2000, random_state=42)
        self.global_regime_fallback.fit(X_scaled, y)

        regime_labels = self._derive_regime_labels(features_df)
        self.trained_regime_models = {}
        for regime in ["bull", "bear", "range", "high_vol"]:
            idx = regime_labels[regime_labels == regime].index
            if len(idx) < 80:
                continue
            X_regime = X.loc[idx]
            y_regime = y.loc[idx]
            if y_regime.nunique() < 2:
                continue
            model = clone(self.regime_models[regime])
            model.fit(self.scaler.transform(X_regime), y_regime)
            self.trained_regime_models[regime] = model

        self.up_threshold = up_threshold
        self.is_trained = True

    def _predict_layer_probs(self, latest_scaled: np.ndarray) -> Dict[str, float]:
        probs = {"baseline": [], "enhanced": []}
        model_probs = {}

        for model_id, model in self.trained_models.items():
            layer = model_id.split(":", 1)[0]
            prob = model.predict_proba(latest_scaled)[0]
            up_prob = float(prob[1])
            probs[layer].append(up_prob)
            model_probs[model_id] = {"down": float(prob[0]), "up": up_prob}

        layer_up = {
            "baseline": float(np.mean(probs["baseline"])) if probs["baseline"] else 0.5,
            "enhanced": float(np.mean(probs["enhanced"])) if probs["enhanced"] else 0.5,
        }
        return {"layer_up": layer_up, "model_probs": model_probs}

    def predict(self, df: pd.DataFrame, horizon: int = 5) -> Dict:
        if not self.is_trained:
            raise ValueError("Model is not trained")

        features_df = self.prepare_features(df)
        latest_features = features_df[self.feature_columns].iloc[-1:]
        latest_scaled = self.scaler.transform(latest_features.values)

        layer_outputs = self._predict_layer_probs(latest_scaled)
        layer_up = layer_outputs["layer_up"]
        probabilities = layer_outputs["model_probs"]
        individual_predictions = {
            model_id: int(prob["up"] > 0.5) for model_id, prob in probabilities.items()
        }

        vol_threshold = float(features_df["volatility_30"].quantile(0.75))
        regime = self._latest_regime(features_df.iloc[-1], vol_threshold)
        regime_model = self.trained_regime_models.get(regime, self.global_regime_fallback)
        regime_prob = regime_model.predict_proba(latest_scaled)[0]
        regime_up = float(regime_prob[1])
        probabilities[f"regime:{regime}"] = {"down": float(regime_prob[0]), "up": regime_up}
        individual_predictions[f"regime:{regime}"] = int(regime_up > 0.5)

        ensemble_up = (
            self.layer_weights["baseline"] * layer_up["baseline"]
            + self.layer_weights["enhanced"] * layer_up["enhanced"]
            + self.layer_weights["regime"] * regime_up
        )
        ensemble_up = _clip01(ensemble_up)
        ensemble_prediction = 1 if ensemble_up > 0.5 else 0

        model_up_values = [x["up"] for x in probabilities.values()]
        agreement = _clip01(1 - (np.std(model_up_values) * 2))
        direction_strength = abs(ensemble_up - 0.5) * 2
        confidence = _clip01(0.6 * direction_strength + 0.4 * agreement)

        return {
            "prediction": ensemble_prediction,
            "confidence": confidence,
            "individual_predictions": individual_predictions,
            "probabilities": probabilities,
            "horizon": horizon,
            "up_threshold": self.up_threshold,
            "model_scores": self.model_scores,
            "layer_outputs": {
                "baseline_up": round(layer_up["baseline"], 4),
                "enhanced_up": round(layer_up["enhanced"], 4),
                "regime_up": round(regime_up, 4),
                "regime": regime,
                "ensemble_up": round(ensemble_up, 4),
            },
        }

    def _backtest_ml_core(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        features_df: pd.DataFrame,
        test_size: float = 0.2,
    ) -> Dict[str, Dict]:
        split_idx = int(len(X) * (1 - test_size))
        X_train = X.iloc[:split_idx]
        X_test = X.iloc[split_idx:]
        y_train = y.iloc[:split_idx]
        y_test = y.iloc[split_idx:]
        feature_test = features_df.iloc[split_idx:]

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        layer_predictions: Dict[str, List[int]] = {"baseline": [], "enhanced": []}
        layer_up_probs: Dict[str, List[float]] = {"baseline": [], "enhanced": []}
        results: Dict[str, Dict] = {}

        trained: Dict[str, object] = {}
        for layer_name, model_name, model in self._iter_all_models():
            model_inst = clone(model)
            model_inst.fit(X_train_scaled, y_train)
            y_pred = model_inst.predict(X_test_scaled)
            y_prob = model_inst.predict_proba(X_test_scaled)
            model_id = f"{layer_name}:{model_name}"
            trained[model_id] = model_inst
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
            np.mean(layer_up_probs["baseline"], axis=0) if layer_up_probs["baseline"] else np.full(len(y_test), 0.5)
        )
        enhanced_up = (
            np.mean(layer_up_probs["enhanced"], axis=0) if layer_up_probs["enhanced"] else np.full(len(y_test), 0.5)
        )

        regime_labels_test = self._derive_regime_labels(feature_test)
        regime_train_labels = self._derive_regime_labels(features_df.iloc[:split_idx])
        regime_models = {}
        global_regime_fallback = LogisticRegression(max_iter=2000, random_state=42)
        global_regime_fallback.fit(X_train_scaled, y_train)
        for regime in ["bull", "bear", "range", "high_vol"]:
            idx = regime_train_labels[regime_train_labels == regime].index
            if len(idx) < 60:
                continue
            X_reg = X.loc[idx]
            y_reg = y.loc[idx]
            if y_reg.nunique() < 2:
                continue
            m = clone(self.regime_models[regime])
            m.fit(scaler.transform(X_reg), y_reg)
            regime_models[regime] = m

        regime_up_probs = []
        regime_preds = []
        for i, (_, row) in enumerate(feature_test.iterrows()):
            regime = regime_labels_test.iloc[i]
            model = regime_models.get(regime, global_regime_fallback)
            row_scaled = scaler.transform(X_test.iloc[i : i + 1])
            p = model.predict_proba(row_scaled)[0, 1]
            regime_up_probs.append(float(p))
            regime_preds.append(int(p > 0.5))

        ensemble_up = (
            self.layer_weights["baseline"] * baseline_up
            + self.layer_weights["enhanced"] * enhanced_up
            + self.layer_weights["regime"] * np.array(regime_up_probs)
        )
        ensemble_preds = (ensemble_up > 0.5).astype(int).tolist()

        baseline_layer_preds = (baseline_vote > 0.5).astype(int).tolist()
        enhanced_layer_preds = (enhanced_vote > 0.5).astype(int).tolist()
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
        results["walk_forward"] = self._walk_forward_eval(X, y, split_idx)

        return {
            "results": results,
            "test_size": int(len(y_test)),
            "baseline_accuracy": baseline_accuracy,
            "improvement": float(results["ensemble"]["accuracy"] - baseline_accuracy),
            "feature_importance": self._get_feature_importance(trained),
        }

    def _backtest_ml(
        self, X: pd.DataFrame, y: pd.Series, features_df: pd.DataFrame, test_size: float = 0.2
    ) -> Dict[str, Dict]:
        if len(X) > 700:
            X_eval = X.iloc[-700:]
            y_eval = y.iloc[-700:]
            features_eval = features_df.iloc[-700:]
        else:
            X_eval = X
            y_eval = y
            features_eval = features_df

        with_sent = self._backtest_ml_core(X_eval, y_eval, features_eval, test_size)

        no_sent_cols = [c for c in X_eval.columns if c not in SENTIMENT_COLUMNS]
        sentiment_cols = [c for c in X_eval.columns if c in SENTIMENT_COLUMNS]
        if len(no_sent_cols) == len(X_eval.columns) or len(sentiment_cols) == 0:
            with_sent["sentiment_comparison"] = {
                "enabled": False,
                "reason": "sentiment_features_not_available",
            }
            return with_sent

        without_sent = self._backtest_ml_core(
            X_eval[no_sent_cols], y_eval, features_eval, test_size
        )
        with_acc = float(with_sent["results"]["ensemble"]["accuracy"])
        with_f1 = float(with_sent["results"]["ensemble"]["f1"])
        no_acc = float(without_sent["results"]["ensemble"]["accuracy"])
        no_f1 = float(without_sent["results"]["ensemble"]["f1"])
        with_sent["sentiment_comparison"] = {
            "enabled": True,
            "with_sentiment": {
                "accuracy": with_acc,
                "f1": with_f1,
                "improvement": float(with_sent["improvement"]),
            },
            "without_sentiment": {
                "accuracy": no_acc,
                "f1": no_f1,
                "improvement": float(without_sent["improvement"]),
            },
            "delta": {
                "accuracy": float(with_acc - no_acc),
                "f1": float(with_f1 - no_f1),
                "improvement": float(with_sent["improvement"] - without_sent["improvement"]),
            },
            "feature_count": {
                "with_sentiment": int(len(X_eval.columns)),
                "without_sentiment": int(len(no_sent_cols)),
                "sentiment_only": int(len(sentiment_cols)),
            },
        }
        return with_sent

    def _walk_forward_eval(self, X: pd.DataFrame, y: pd.Series, split_idx: int) -> Dict[str, float]:
        if len(X) - split_idx <= 0:
            return {"samples": 0, "accuracy": 0.0}

        eval_indices = list(range(split_idx, len(X)))
        max_steps = 12
        if len(eval_indices) > max_steps:
            step = max(1, len(eval_indices) // max_steps)
            eval_indices = eval_indices[::step]

        preds = []
        truths = []
        for idx in eval_indices:
            if idx < 120:
                continue
            X_train = X.iloc[:idx]
            y_train = y.iloc[:idx]
            X_cur = X.iloc[idx : idx + 1]
            y_cur = int(y.iloc[idx])

            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_cur_scaled = scaler.transform(X_cur)

            model = LogisticRegression(max_iter=600, random_state=42)
            model.fit(X_train_scaled, y_train)
            pred = int(model.predict(X_cur_scaled)[0])
            preds.append(pred)
            truths.append(y_cur)

        if not truths:
            return {"samples": 0, "accuracy": 0.0}

        return {
            "samples": len(truths),
            "accuracy": float(accuracy_score(truths, preds)),
        }

    def _backtest_rule_ma_cross(self, features_df: pd.DataFrame, labels: pd.Series, test_size: float):
        split_idx = int(len(features_df) * (1 - test_size))
        test_features = features_df.iloc[split_idx:]
        y_test = labels.iloc[split_idx:]

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
        self, features_df: pd.DataFrame, labels: pd.Series, test_size: float
    ):
        split_idx = int(len(features_df) * (1 - test_size))
        test_features = features_df.iloc[split_idx:]
        y_test = labels.iloc[split_idx:]

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
    ) -> Dict:
        features_df = self.prepare_features(df)
        labels = self.prepare_labels(features_df, horizon=horizon, up_threshold=up_threshold)

        min_length = min(len(features_df), len(labels))
        features_df = features_df.iloc[:min_length]
        labels = labels.iloc[:min_length]

        X = features_df[self.feature_columns]
        y = labels

        strategy = (strategy or "ensemble_ml").lower()
        if strategy in {"default", "ensemble", "ml"}:
            strategy = "ensemble_ml"

        if strategy == "ma_cross":
            result = self._backtest_rule_ma_cross(features_df, y, test_size)
        elif strategy == "rsi_reversion":
            result = self._backtest_rule_rsi_reversion(features_df, y, test_size)
        else:
            result = self._backtest_ml(X, y, features_df, test_size)

        result.update(
            {
                "horizon": horizon,
                "strategy": strategy,
                "up_threshold": up_threshold,
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
            "风险提示：结果基于历史统计特征，不构成投资建议，请结合基本面与风险承受能力综合判断。",
        ]
        return "\n".join(lines)
