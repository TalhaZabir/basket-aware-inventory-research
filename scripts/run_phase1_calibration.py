"""Phase 1 validation-only forecast ladder and service calibration.

This script deliberately stops at the validation window. It does not read or
score the held-out test demand and therefore cannot change test-window results.
All inventory outcomes produced here are simulated under the package's frozen
assumptions.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from run_experiment import (  # noqa: E402
    POLICIES,
    basket_map,
    network_scores,
    sample_lead_weeks,
    simulate_policy,
    weekly_matrix,
)


SEED = 20261020
SMOOTHING = 0.1
METHODS = [
    "recent4",
    "recent8",
    "seasonal52",
    "croston",
    "sba",
    "tsb",
    "seasonal_ratio",
    "empirical_quantile",
]
PREDICTIVE_QUANTILES = [0.05, 0.50, 0.90, 0.95, 0.975]
PINBALL_QUANTILES = [0.50, 0.90, 0.95, 0.975]
SAFETY_MULTIPLIERS = [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]


def croston_one(x: np.ndarray, variant: str) -> float:
    positive = np.flatnonzero(x > 0)
    if len(positive) == 0:
        return 0.0
    z = float(x[positive[0]])
    interval = float(max(1, positive[0] + 1))
    last = int(positive[0])
    probability = 1.0
    for t in range(positive[0] + 1, len(x)):
        occurrence = float(x[t] > 0)
        if occurrence:
            gap = float(t - last)
            z += SMOOTHING * (float(x[t]) - z)
            interval += SMOOTHING * (gap - interval)
            last = t
        if variant == "tsb":
            probability += SMOOTHING * (occurrence - probability)
    if variant == "tsb":
        return max(0.0, z * probability)
    estimate = z / max(interval, 1e-9)
    if variant == "sba":
        estimate *= 1.0 - SMOOTHING / 2.0
    return max(0.0, estimate)


def point_forecast(history: np.ndarray, method: str) -> np.ndarray:
    if history.shape[1] == 0:
        return np.zeros(history.shape[0], dtype=float)
    if method == "recent4":
        return history[:, -min(4, history.shape[1]):].mean(axis=1)
    if method == "recent8":
        return history[:, -min(8, history.shape[1]):].mean(axis=1)
    if method == "seasonal52" and history.shape[1] >= 52:
        return history[:, -52]
    if method == "seasonal_ratio":
        base = history[:, -min(4, history.shape[1]):].mean(axis=1)
        if history.shape[1] < 56:
            return base
        same = history[:, -52]
        prior_four = history[:, -56:-52].mean(axis=1)
        ratio = np.divide(same, prior_four, out=np.ones_like(same), where=prior_four > 0)
        return base * np.clip(ratio, 0.25, 4.0)
    if method == "empirical_quantile":
        return np.quantile(history[:, -min(26, history.shape[1]):], 0.50, axis=1)
    if method in {"croston", "sba", "tsb"}:
        return np.array([croston_one(row, method) for row in history], dtype=float)
    raise ValueError(f"Unknown forecast method: {method}")


def predictive_quantiles(history: np.ndarray, point: np.ndarray, method: str, residual_scale: np.ndarray) -> np.ndarray:
    if method == "empirical_quantile":
        sample = history[:, -min(26, history.shape[1]):]
        return np.stack([np.quantile(sample, q, axis=1) for q in PREDICTIVE_QUANTILES], axis=1)
    # The other candidates use a normal residual approximation with dispersion
    # learned only from the internal training pseudo-validation period.
    from statistics import NormalDist
    return np.stack([
        np.maximum(0.0, point + NormalDist().inv_cdf(q) * residual_scale)
        for q in PREDICTIVE_QUANTILES
    ], axis=1)


def internal_calibration(demand: np.ndarray, train_idx: np.ndarray) -> dict[str, object]:
    internal_idx = train_idx[-8:]
    predictions = {method: np.zeros((demand.shape[0], len(internal_idx))) for method in METHODS}
    for j, idx in enumerate(internal_idx):
        history = demand[:, :idx]
        for method in METHODS:
            predictions[method][:, j] = point_forecast(history, method)
    actual = demand[:, internal_idx]
    mae = np.stack([np.abs(predictions[method] - actual).mean(axis=1) for method in METHODS], axis=1)
    selected_idx = np.argmin(mae, axis=1)
    selected_methods = np.array(METHODS, dtype=object)[selected_idx]
    selected = np.zeros_like(actual)
    for j in range(len(internal_idx)):
        selected[:, j] = np.array([predictions[METHODS[k]][i, j] for i, k in enumerate(selected_idx)])
    selected_error = selected - actual
    bias = selected_error.mean(axis=1)
    scale = np.maximum(selected_error.std(axis=1, ddof=1), 0.25)
    return {"indices": internal_idx, "predictions": predictions, "selected_methods": selected_methods, "bias": bias, "scale": scale}


def build_validation_forecasts(demand: np.ndarray, train_idx: np.ndarray, val_idx: np.ndarray) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], np.ndarray, np.ndarray]:
    internal = internal_calibration(demand, train_idx)
    points = {method: np.zeros((demand.shape[0], len(val_idx))) for method in METHODS}
    scales = {method: np.zeros(demand.shape[0], dtype=float) for method in METHODS}
    for method in METHODS:
        errors = internal["predictions"][method] - demand[:, internal["indices"]]
        scales[method] = np.maximum(errors.std(axis=1, ddof=1), 0.25)
    for j, idx in enumerate(val_idx):
        history = demand[:, :idx]
        for method in METHODS:
            points[method][:, j] = point_forecast(history, method)
    selected = np.zeros_like(points["recent4"])
    for j in range(len(val_idx)):
        selected[:, j] = np.array([points[str(internal["selected_methods"][i])][i, j] for i in range(demand.shape[0])])
    points["bias_corrected_selected"] = np.maximum(0.0, selected - internal["bias"][:, None])
    scales["bias_corrected_selected"] = internal["scale"]
    return points, scales, internal["selected_methods"], internal["bias"]


def pinball(actual: np.ndarray, prediction: np.ndarray, q: float) -> float:
    error = actual - prediction
    return float(np.where(error >= 0, q * error, (q - 1.0) * error).mean())


def forecast_metrics(demand: np.ndarray, val_idx: np.ndarray, points: dict[str, np.ndarray], scales: dict[str, np.ndarray]) -> pd.DataFrame:
    actual = demand[:, val_idx]
    rows: list[dict[str, object]] = []
    for method, point in points.items():
        history_for_first = demand[:, :val_idx[0]]
        if method == "empirical_quantile":
            qpred = np.stack([
                np.stack([np.quantile(demand[:, :idx][:, -min(26, idx):], q, axis=1) for q in PREDICTIVE_QUANTILES], axis=-1)
                for idx in val_idx
            ], axis=1)
        else:
            qpred = np.stack([
                np.maximum(0.0, point + __import__("statistics").NormalDist().inv_cdf(q) * scales[method][:, None])
                for q in PREDICTIVE_QUANTILES
            ], axis=-1)
        lower = qpred[:, :, 0]
        upper = qpred[:, :, 3]
        row: dict[str, object] = {
            "method": method,
            "validation_mae": float(np.abs(point - actual).mean()),
            "validation_wape": float(np.abs(point - actual).sum() / max(np.abs(actual).sum(), 1.0)),
            "validation_bias": float((point - actual).mean()),
            "validation_90pct_coverage": float(((actual >= lower) & (actual <= upper)).mean()),
            "validation_90pct_width": float((upper - lower).mean()),
            "internal_scale_mean": float(scales[method].mean()),
        }
        for q in PINBALL_QUANTILES:
            q_idx = PREDICTIVE_QUANTILES.index(q)
            row[f"pinball_{q:g}"] = pinball(actual, qpred[:, :, q_idx], q)
        grid = np.arange(0.05, 1.0, 0.05)
        losses = []
        for q in grid:
            if method == "empirical_quantile":
                qp = np.stack([np.quantile(demand[:, :idx][:, -min(26, idx):], q, axis=1) for idx in val_idx], axis=1)
            else:
                qp = np.maximum(0.0, point + __import__("statistics").NormalDist().inv_cdf(float(q)) * scales[method][:, None])
            losses.append(pinball(actual, qp, float(q)))
        row["crps_style"] = float(2.0 * np.mean(losses))
        rows.append(row)
    return pd.DataFrame(rows).sort_values("validation_wape")


def validation_leads(scenario: pd.Series, horizon: int, products: int, rng: np.random.Generator, stochastic: bool) -> np.ndarray:
    if not stochastic:
        return np.ones((horizon, products), dtype=int)
    return np.vstack([sample_lead_weeks(scenario, rng, products) for _ in range(horizon)])


def policy_validation(root: Path, demand: np.ndarray, weeks: pd.Index, products: np.ndarray, val_idx: np.ndarray, forecast: np.ndarray, residual_scale: np.ndarray, network: np.ndarray, scenarios: pd.DataFrame, baskets: dict[str, list[list[tuple[int, float]]]]) -> pd.DataFrame:
    val_demand = demand[:, val_idx]
    val_weeks = weeks[val_idx]
    rows: list[dict[str, object]] = []
    for scenario in scenarios.to_dict("records"):
        scenario_series = pd.Series(scenario)
        target_nominal = float(scenario_series["shortage_penalty_per_unit"]) / (float(scenario_series["shortage_penalty_per_unit"]) + float(scenario_series["holding_cost_per_unit_week"]))
        for policy in ["P1_independent_deterministic", "P2_independent_stochastic"]:
            stochastic = policy.startswith("P2")
            for multiplier in SAFETY_MULTIPLIERS:
                rng = np.random.default_rng(SEED + int(str(scenario_series["scenario_id"])[1:]) * 100 + int(multiplier * 1000))
                leads = validation_leads(scenario_series, len(val_idx), len(products), rng, stochastic)
                result = simulate_policy(val_demand, val_weeks, forecast, residual_scale * multiplier, network, baskets, scenario_series, policy, 0.0, leads, service_target=target_nominal)
                rows.append({"scenario_id": scenario_series["scenario_id"], "policy": policy, "nominal_target": target_nominal, "safety_multiplier": multiplier, **result})
    frame = pd.DataFrame(rows)
    chosen = frame.assign(distance=(frame["item_fill_rate"] - frame["nominal_target"]).abs()).sort_values(["scenario_id", "policy", "distance", "safety_multiplier"]).groupby(["scenario_id", "policy"], as_index=False).head(1).copy()
    chosen["acceptance_within_3_points"] = (chosen["item_fill_rate"] - chosen["nominal_target"]).abs() <= 0.03
    return chosen.sort_values(["scenario_id", "policy"])


def main() -> None:
    parser = __import__("argparse").ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    out = root / "results"
    out.mkdir(parents=True, exist_ok=True)

    weekly, weeks, demand, products, train_idx, val_idx, _test_idx = weekly_matrix(root, support_threshold=20)
    points, scales, selected_methods, bias = build_validation_forecasts(demand, train_idx, val_idx)
    metrics = forecast_metrics(demand, val_idx, points, scales)
    metrics.to_csv(out / "phase1_forecast_validation.csv", index=False)
    winner = str(metrics.iloc[0]["method"])
    network = network_scores(root, products, min_pair_count=5, top_k=5)
    scenarios = pd.read_csv(root / "data" / "synthetic" / "inventory_scenarios.csv")
    baskets = basket_map(root, products, weeks[val_idx])
    calibration = policy_validation(root, demand, weeks, products, val_idx, points[winner], scales[winner], network, scenarios, baskets)
    calibration.to_csv(out / "phase1_policy_validation_calibration.csv", index=False)

    config = {
        "phase": 1,
        "seed": SEED,
        "window": "validation_only",
        "train_end": str(weeks[train_idx[-1]].date()),
        "validation_start": str(weeks[val_idx[0]].date()),
        "validation_end": str(weeks[val_idx[-1]].date()),
        "methods": METHODS,
        "smoothing": SMOOTHING,
        "seasonal_ratio_clip": [0.25, 4.0],
        "empirical_history_weeks": 26,
        "safety_multiplier_candidates": SAFETY_MULTIPLIERS,
        "forecast_winner_by_validation_wape": winner,
        "primary_estimand": "service_at_matched_inventory",
        "test_window_used": False,
    }
    encoded = json.dumps(config, sort_keys=True).encode("utf-8")
    config["config_hash"] = hashlib.sha256(encoded).hexdigest()
    (out / "phase1_validation_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    log_path = out / "run_log.csv"
    log_row = {
        "config_hash": config["config_hash"],
        "date": pd.Timestamp.now(tz="Asia/Dhaka").isoformat(),
        "seed": SEED,
        "phase": "phase1_validation_only",
        "split": "train_validation_only",
        "scenario": "all_validation_scenarios",
        "policy": "P1/P2_validation_calibration",
        "replication": "not_applicable",
        "test_window_used": False,
        "outputs": "phase1_forecast_validation.csv;phase1_policy_validation_calibration.csv",
    }
    pd.DataFrame([log_row]).to_csv(log_path, mode="a", header=not log_path.exists(), index=False)

    accepted = bool(calibration["acceptance_within_3_points"].all())
    report = "\n".join([
        "# Phase 1 validation calibration report",
        "",
        "The phase was validation-only; the held-out test window was not read for scoring or tuning.",
        "",
        f"The validation winner by aggregate WAPE was `{winner}`. Forecast metrics are in `phase1_forecast_validation.csv`; the ladder includes moving averages, seasonal-naive, Croston, SBA, TSB, a prior-year seasonal-ratio forecast, and an empirical-quantile point forecast.",
        "",
        f"Independent service calibration selected the closest realised item-fill target per scenario and policy by multiplying the internal residual scale by one of {SAFETY_MULTIPLIERS}. The within-three-percentage-point acceptance result was `{accepted}` across {len(calibration)} scenario-policy rows.",
        "",
        "The calibration is not a test result. If the acceptance test fails, the failure and its magnitude must be reported and the forecast/policy must not be declared operationally calibrated.",
        "",
        "Files: `phase1_forecast_validation.csv`, `phase1_policy_validation_calibration.csv`, `phase1_validation_config.json`, and `run_log.csv`.",
    ])
    (out / "phase_1_report.md").write_text(report + "\n", encoding="utf-8")
    print(json.dumps({"winner": winner, "acceptance_within_3_points": accepted, "calibration_rows": len(calibration), "config_hash": config["config_hash"]}, indent=2))


if __name__ == "__main__":
    main()
