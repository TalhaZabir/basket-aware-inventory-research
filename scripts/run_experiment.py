"""Run the reproducible UCI forecast and inventory-policy experiment.

The experiment is intentionally conservative: UCI transaction data are used to
construct demand and observed-basket inputs, while inventory states, lead times,
costs, and service outcomes are simulated assumptions or simulation outputs.
"""

from __future__ import annotations

import argparse
import json
import math
from statistics import NormalDist
from pathlib import Path

import numpy as np
import pandas as pd


Z95 = 1.645
ALPHA_CANDIDATES = [0.0, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0]
POLICIES = ["P1_independent_deterministic", "P2_independent_stochastic", "P3_basket_deterministic", "P4_basket_stochastic"]


def weekly_matrix(root: Path, support_threshold: int = 20) -> tuple[pd.DataFrame, pd.Index, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    path = root / "data" / "processed" / "uci_weekly_product_demand.csv"
    weekly = pd.read_csv(path, dtype={"stock_code": "string"})
    weekly["week_start"] = pd.to_datetime(weekly["week_start"])
    all_weeks = pd.Index(sorted(weekly["week_start"].unique()))
    train_end = pd.Timestamp("2011-06-27")
    val_start = pd.Timestamp("2011-07-04")
    val_end = pd.Timestamp("2011-08-29")
    test_start = pd.Timestamp("2011-09-05")
    test_end = pd.Timestamp("2011-12-05")
    support = weekly.loc[weekly["week_start"] <= train_end].groupby("stock_code")["units_sold"].apply(lambda x: int((x > 0).sum()))
    products = pd.Index(sorted(support.loc[support >= support_threshold].index.astype(str)))
    matrix = (
        weekly.pivot_table(index="stock_code", columns="week_start", values="units_sold", aggfunc="sum")
        .reindex(index=products, columns=all_weeks)
        .fillna(0.0)
        .astype(float)
    )
    train_idx = np.flatnonzero(all_weeks <= train_end)
    val_idx = np.flatnonzero((all_weeks >= val_start) & (all_weeks <= val_end))
    test_idx = np.flatnonzero((all_weeks >= test_start) & (all_weeks <= test_end))
    return weekly, all_weeks, matrix.to_numpy(), products.to_numpy(), train_idx, val_idx, test_idx


def forecast_values(history: np.ndarray, method: str) -> np.ndarray:
    if method == "recent4":
        return history[:, -min(4, history.shape[1]):].mean(axis=1)
    if method == "recent8":
        return history[:, -min(8, history.shape[1]):].mean(axis=1)
    if method == "seasonal52" and history.shape[1] >= 52:
        return history[:, -52]
    return history[:, -min(8, history.shape[1]):].mean(axis=1)


def build_forecasts(demand: np.ndarray, train_idx: np.ndarray, val_idx: np.ndarray, test_idx: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, pd.DataFrame]:
    methods = ["recent4", "recent8", "seasonal52"]
    n = demand.shape[0]
    val_predictions = {method: np.zeros((n, len(val_idx))) for method in methods}
    for j, idx in enumerate(val_idx):
        history = demand[:, :idx]
        for method in methods:
            val_predictions[method][:, j] = forecast_values(history, method)
    actual_val = demand[:, val_idx]
    mae = np.vstack([np.abs(val_predictions[method] - actual_val).mean(axis=1) for method in methods]).T
    selected = np.argmin(mae, axis=1)
    selected_names = np.array(methods, dtype=object)[selected]
    selected_val = np.choose(selected[:, None], np.stack([val_predictions[method] for method in methods], axis=0))
    residuals = actual_val - selected_val
    residual_std = residuals.std(axis=1, ddof=1)
    fallback_std = demand[:, train_idx[-min(26, len(train_idx)):]].std(axis=1, ddof=1)
    residual_std = np.where(np.isfinite(residual_std), residual_std, fallback_std)
    residual_std = np.where(np.isfinite(residual_std), residual_std, 0.0)
    residual_std = np.maximum(residual_std, 0.25)

    test_predictions = np.zeros((n, len(test_idx)))
    for j, idx in enumerate(test_idx):
        history = demand[:, :idx]
        candidates = np.stack([forecast_values(history, method) for method in methods], axis=0)
        test_predictions[:, j] = candidates[selected, np.arange(n)]

    rows = []
    for method in methods:
        pred = val_predictions[method]
        err = pred - actual_val
        denom = np.abs(actual_val).sum(axis=1)
        rows.append({
            "model": method,
            "validation_mae": float(np.abs(err).mean()),
            "validation_wape": float(np.abs(err).sum() / max(np.abs(actual_val).sum(), 1.0)),
            "validation_bias": float(err.mean()),
            "validation_90pct_coverage": np.nan,
            "validation_90pct_width": np.nan,
            "products_selected": int((selected_names == method).sum()),
        })
    selected_err = selected_val - actual_val
    rows.append({
        "model": "selected_per_product",
        "validation_mae": float(np.abs(selected_err).mean()),
        "validation_wape": float(np.abs(selected_err).sum() / max(np.abs(actual_val).sum(), 1.0)),
        "validation_bias": float(selected_err.mean()),
        "validation_90pct_coverage": float(((actual_val >= (selected_val - Z95 * residual_std[:, None])) & (actual_val <= (selected_val + Z95 * residual_std[:, None]))).mean()),
        "validation_90pct_width": float((2 * Z95 * residual_std).mean()),
        "products_selected": int(n),
    })
    return test_predictions, residual_std, selected_names, pd.DataFrame(rows)


def evaluate_test_forecast(demand: np.ndarray, test_idx: np.ndarray, test_forecast: np.ndarray, selected_names: np.ndarray) -> pd.DataFrame:
    """Evaluate the frozen forecast on the held-out test window after replay.

    These metrics are descriptive and are never used to select the forecast or
    tune the inventory policy.  They document whether the test-period demand
    path was systematically under- or over-forecast.
    """
    actual = demand[:, test_idx]
    methods = ["recent4", "recent8", "seasonal52"]
    rows = []
    for method in methods:
        predictions = np.zeros_like(actual, dtype=float)
        for j, idx in enumerate(test_idx):
            candidates = np.stack([forecast_values(demand[:, :idx], name) for name in methods], axis=0)
            predictions[:, j] = candidates[methods.index(method)]
        error = predictions - actual
        rows.append({
            "model": method,
            "test_mae": float(np.abs(error).mean()),
            "test_wape": float(np.abs(error).sum() / max(np.abs(actual).sum(), 1.0)),
            "test_bias": float(error.mean()),
            "products_selected": int((selected_names == method).sum()),
        })
    error = test_forecast - actual
    rows.append({
        "model": "selected_per_product",
        "test_mae": float(np.abs(error).mean()),
        "test_wape": float(np.abs(error).sum() / max(np.abs(actual).sum(), 1.0)),
        "test_bias": float(error.mean()),
        "products_selected": int(len(selected_names)),
    })
    return pd.DataFrame(rows)


def network_scores(root: Path, products: np.ndarray, min_pair_count: int = 5, top_k: int = 5) -> np.ndarray:
    path = root / "data" / "processed" / "uci_copurchase_edges_train_only.csv"
    edges = pd.read_csv(path, dtype={"stock_code_a": "string", "stock_code_b": "string"})
    edges = edges.loc[edges["co_purchase_count"] >= min_pair_count]
    index = {str(product): i for i, product in enumerate(products)}
    directed: dict[int, list[float]] = {}
    for row in edges.itertuples(index=False):
        a = index.get(str(row.stock_code_a))
        b = index.get(str(row.stock_code_b))
        if a is None or b is None:
            continue
        directed.setdefault(a, []).append(float(row.p_b_given_a))
        directed.setdefault(b, []).append(float(row.p_a_given_b))
    score = np.zeros(len(products), dtype=float)
    for idx, values in directed.items():
        values = sorted(values, reverse=True)[:top_k]
        score[idx] = min(float(np.mean(values)), 1.0)
    return score


def m5_benchmark(root: Path, results_dir: Path) -> pd.DataFrame:
    path = root / "data" / "processed" / "m5_weekly_product_demand_sample.csv"
    frame = pd.read_csv(path, dtype={"id": "string"})
    frame["week_start"] = pd.to_datetime(frame["week_start"])
    weeks = pd.Index(sorted(frame["week_start"].unique()))
    holdout = 4
    matrix = frame.pivot_table(index="id", columns="week_start", values="units_sold", aggfunc="sum").reindex(columns=weeks).fillna(0.0)
    actual = matrix.to_numpy()[:, -holdout:]
    rows = []
    for method in ["recent4", "recent8", "seasonal52"]:
        predictions = []
        for j in range(holdout):
            history = matrix.to_numpy()[:, : -holdout + j]
            predictions.append(forecast_values(history, method))
        pred = np.stack(predictions, axis=1)
        err = pred - actual
        rows.append({
            "dataset": "M5 sample",
            "series": int(matrix.shape[0]),
            "holdout_weeks": holdout,
            "holdout_start": str(weeks[-holdout].date()),
            "holdout_end": str(weeks[-1].date()),
            "model": method,
            "mae": float(np.abs(err).mean()),
            "wape": float(np.abs(err).sum() / max(np.abs(actual).sum(), 1.0)),
            "bias": float(err.mean()),
        })
    result = pd.DataFrame(rows)
    result.to_csv(results_dir / "m5_sample_forecast_summary.csv", index=False)
    return result


def basket_map(root: Path, products: np.ndarray, selected_weeks: pd.Index) -> dict[str, list[list[tuple[int, float]]]]:
    lines = pd.read_csv(root / "data" / "processed" / "uci_transaction_lines_clean.csv", dtype={"invoice_id": "string", "stock_code": "string"})
    lines["invoice_date"] = pd.to_datetime(lines["invoice_date"])
    lines["week_start"] = lines["invoice_date"].dt.normalize() - pd.to_timedelta(lines["invoice_date"].dt.weekday, unit="D")
    lines = lines.loc[lines["week_start"].isin(selected_weeks)].copy()
    product_index = {str(product): i for i, product in enumerate(products)}
    lines["product_idx"] = lines["stock_code"].map(product_index)
    lines = lines.dropna(subset=["product_idx"])
    lines["product_idx"] = lines["product_idx"].astype(int)
    grouped = lines.groupby(["week_start", "invoice_id", "product_idx"], as_index=False)["quantity"].sum()
    result: dict[str, list[list[tuple[int, float]]]] = {}
    for (week, invoice), frame in grouped.groupby(["week_start", "invoice_id"]):
        basket = [(int(row.product_idx), float(row.quantity)) for row in frame.itertuples(index=False)]
        result.setdefault(pd.Timestamp(week).strftime("%Y-%m-%d"), []).append(basket)
    return result


def sample_lead_weeks(scenario: pd.Series, rng: np.random.Generator, count: int) -> np.ndarray:
    family = scenario["lead_time_distribution"]
    if family == "deterministic_7d":
        days = np.full(count, 7.0)
    elif family in {"low_variance_normal", "high_variance_normal"}:
        days = np.rint(rng.normal(float(scenario["lead_time_mean_days"]), float(scenario["lead_time_sd_days"]), size=count))
        days = np.clip(days, float(scenario["lead_time_min_days"]), float(scenario["lead_time_max_days"]))
    elif family == "right_skewed_discrete":
        values = np.arange(int(scenario["lead_time_min_days"]), int(scenario["lead_time_max_days"]) + 1)
        weights = np.exp(-(values - values.min()) / 5.0)
        weights = weights / weights.sum()
        days = rng.choice(values, size=count, p=weights)
    else:
        raise ValueError(f"Unknown lead-time family: {family}")
    return np.maximum(1, np.ceil(days / 7.0).astype(int))


def simulate_policy(
    demand: np.ndarray,
    weeks: pd.Index,
    forecast: np.ndarray,
    residual_std: np.ndarray,
    network: np.ndarray,
    basket_data: dict[str, list[list[tuple[int, float]]]],
    scenario: pd.Series,
    policy: str,
    alpha: float,
    lead_draws: np.ndarray,
    service_target: float | None = None,
    backorder_mode: str = "lost_sales",
    basket_definition: str = "all_units",
    metric_product_mask: np.ndarray | None = None,
    basket_buffer: np.ndarray | None = None,
    return_weekly: bool = False,
) -> dict[str, float | int | str]:
    n, horizon = demand.shape
    stochastic = policy.endswith("_stochastic") or policy in {"P2_independent_stochastic", "P4_basket_stochastic"}
    basket_aware = (
        policy in {"P3_basket_deterministic", "P4_basket_stochastic"}
        or policy.startswith(("PA1_", "PA2_", "PA3_", "C2_", "C3_", "C4_", "C5_"))
    )
    coverage = 2.0
    lead_sd_weeks = float(scenario["lead_time_sd_days"]) / 7.0
    if not 0.5 <= float(service_target if service_target is not None else 0.95) < 1.0:
        raise ValueError("service_target must be in [0.5, 1.0)")
    z = NormalDist().inv_cdf(float(service_target if service_target is not None else 0.95))
    initial_target = np.ceil(forecast[:, 0] * coverage + z * residual_std * math.sqrt(coverage)).astype(float)
    onhand = initial_target.copy()
    max_lead = int(max(1, math.ceil(float(scenario["lead_time_max_days"]) / 7.0)))
    arrivals = [np.zeros(n, dtype=float) for _ in range(horizon + max_lead + 3)]
    on_order = np.zeros(n, dtype=float)
    backorder = np.zeros(n, dtype=float)
    total_holding = 0.0
    total_shortage = 0.0
    total_ordering = 0.0
    total_purchase = 0.0
    total_unmet = 0.0
    total_fulfilled = 0.0
    total_demand = float(demand.sum())
    metric_mask = np.ones(n, dtype=bool) if metric_product_mask is None else np.asarray(metric_product_mask, dtype=bool)
    metric_demand = 0.0
    metric_fulfilled = 0.0
    metric_unmet = 0.0
    total_inventory = 0.0
    basket_total = 0
    basket_complete = 0
    stockout_events = 0
    demand_events = int((demand > 0).sum())
    order_events = 0
    order_units = 0.0
    weekly_cost = np.zeros(horizon, dtype=float)
    weekly_inventory = np.zeros(horizon, dtype=float)
    weekly_fulfilled = np.zeros(horizon, dtype=float)
    weekly_demand = np.zeros(horizon, dtype=float)
    weekly_unmet = np.zeros(horizon, dtype=float)
    weekly_stockout_events = np.zeros(horizon, dtype=float)
    weekly_baskets = np.zeros(horizon, dtype=float)
    weekly_complete_baskets = np.zeros(horizon, dtype=float)
    week_strings = [pd.Timestamp(week).strftime("%Y-%m-%d") for week in weeks]
    for t in range(horizon):
        week_ordering_cost = 0.0
        week_purchase_cost = 0.0
        onhand += arrivals[t]
        on_order -= arrivals[t]
        if backorder_mode == "backorder" and backorder.sum() > 0:
            recovered = np.minimum(onhand, backorder)
            onhand -= recovered
            backorder -= recovered
            total_fulfilled += float(recovered.sum())
        inv_position = onhand + on_order - (backorder if backorder_mode == "backorder" else 0.0)
        target = forecast[:, t] * coverage + z * residual_std * math.sqrt(coverage)
        if stochastic:
            target += z * forecast[:, t] * lead_sd_weeks
        if basket_aware:
            if basket_buffer is None:
                target += alpha * network * forecast[:, t]
            else:
                buffer_array = np.asarray(basket_buffer, dtype=float)
                if buffer_array.ndim == 1:
                    target += alpha * buffer_array
                elif buffer_array.shape == (n, horizon):
                    target += alpha * buffer_array[:, t]
                else:
                    raise ValueError("basket_buffer must have shape (n,) or (n, horizon)")
        quantity = np.maximum(0.0, np.ceil(target - inv_position))
        if quantity.sum() > 0:
            order_events += int((quantity > 0).sum())
            order_units += float(quantity.sum())
            week_ordering_cost = float(scenario["ordering_cost_per_order"])
            week_purchase_cost = float(scenario["unit_purchase_cost"]) * float(quantity.sum())
            total_ordering += week_ordering_cost
            total_purchase += week_purchase_cost
            lead = lead_draws[t]
            for product_idx in np.flatnonzero(quantity > 0):
                arrival = t + int(lead[product_idx])
                arrivals[arrival][product_idx] += quantity[product_idx]
            on_order += quantity

        baskets = basket_data.get(week_strings[t], [])
        week_basket_total = len(baskets)
        week_basket_complete = 0
        basket_total += len(baskets)
        for basket in baskets:
            if basket_definition == "all_items":
                required = [(product_idx, 1.0) for product_idx, _ in basket]
            else:
                required = basket
            if all(onhand[product_idx] >= required_quantity for product_idx, required_quantity in required):
                basket_complete += 1
                week_basket_complete += 1

        week_demand = demand[:, t]
        available_before_demand = onhand.copy()
        fulfilled = np.minimum(onhand, week_demand)
        unmet = np.maximum(0.0, week_demand - onhand)
        onhand = np.maximum(0.0, onhand - week_demand)
        if backorder_mode == "backorder":
            backorder += unmet
        elif backorder_mode != "lost_sales":
            raise ValueError("backorder_mode must be lost_sales or backorder")
        total_fulfilled += float(fulfilled.sum())
        total_unmet += float(unmet.sum())
        metric_demand += float(week_demand[metric_mask].sum())
        metric_fulfilled += float(fulfilled[metric_mask].sum())
        metric_unmet += float(unmet[metric_mask].sum())
        week_shortage_cost = float(scenario["shortage_penalty_per_unit"]) * float(unmet.sum())
        week_holding_cost = float(scenario["holding_cost_per_unit_week"]) * float(onhand.sum())
        total_shortage += week_shortage_cost
        total_holding += week_holding_cost
        week_inventory = float(onhand.sum())
        week_stockout_events = int(((week_demand > 0) & (available_before_demand < week_demand)).sum())
        total_inventory += week_inventory
        stockout_events += week_stockout_events
        weekly_cost[t] = week_holding_cost + week_shortage_cost + week_ordering_cost + week_purchase_cost
        weekly_inventory[t] = week_inventory
        weekly_fulfilled[t] = float(fulfilled.sum())
        weekly_demand[t] = float(week_demand.sum())
        weekly_unmet[t] = float(unmet.sum())
        weekly_stockout_events[t] = float(week_stockout_events)
        weekly_baskets[t] = float(week_basket_total)
        weekly_complete_baskets[t] = float(week_basket_complete)

    total_cost = total_holding + total_shortage + total_ordering + total_purchase
    result = {
        "policy": policy,
        "total_cost": total_cost,
        "holding_cost": total_holding,
        "shortage_cost": total_shortage,
        "ordering_cost": total_ordering,
        "purchase_cost": total_purchase,
        "average_inventory_units": total_inventory / max(horizon, 1),
        "item_fill_rate": total_fulfilled / max(total_demand, 1.0),
        "complete_basket_fill_rate": basket_complete / max(basket_total, 1),
        "unmet_units": total_unmet,
        "stockout_frequency": stockout_events / max(demand_events, 1),
        "order_events": order_events,
        "average_order_units": order_units / max(order_events, 1),
        "basket_count": basket_total,
        "demand_units": total_demand,
        "service_target": float(service_target if service_target is not None else 0.95),
        "backorder_mode": backorder_mode,
        "basket_definition": basket_definition,
        "metric_demand_units": metric_demand,
        "metric_item_fill_rate": metric_fulfilled / max(metric_demand, 1.0),
        "metric_unmet_units": metric_unmet,
    }
    if return_weekly:
        result["weekly_cost"] = weekly_cost
        result["weekly_inventory"] = weekly_inventory
        result["weekly_fulfilled"] = weekly_fulfilled
        result["weekly_demand"] = weekly_demand
        result["weekly_unmet"] = weekly_unmet
        result["weekly_stockout_events"] = weekly_stockout_events
        result["weekly_baskets"] = weekly_baskets
        result["weekly_complete_baskets"] = weekly_complete_baskets
    return result


def calibrate_alpha(demand: np.ndarray, weeks: pd.Index, forecast: np.ndarray, residual_std: np.ndarray, network: np.ndarray, basket_data: dict[str, list[list[tuple[int, float]]]], products: np.ndarray) -> tuple[float, pd.DataFrame]:
    scenario = pd.Series({
        "lead_time_distribution": "deterministic_7d",
        "lead_time_sd_days": 0.0,
        "lead_time_max_days": 7.0,
        "holding_cost_per_unit_week": 0.15,
        "shortage_penalty_per_unit": 5.0,
        "ordering_cost_per_order": 1.0,
        "unit_purchase_cost": 1.0,
    })
    lead = np.ones((demand.shape[1], len(products)), dtype=int)
    rows = []
    calibration_target = 5.0 / (5.0 + 0.15)
    for alpha in ALPHA_CANDIDATES:
        result = simulate_policy(demand, weeks, forecast, residual_std, network, basket_data, scenario, "P3_basket_deterministic", alpha, lead, service_target=calibration_target)
        rows.append({"alpha": alpha, **result})
    frame = pd.DataFrame(rows)
    independent_targets = [0.80, 0.85, 0.90, 0.95, 0.975, 0.99, 0.995]
    independent_rows = []
    for target in independent_targets:
        independent_rows.append(simulate_policy(demand, weeks, forecast, residual_std, network, basket_data, scenario, "P1_independent_deterministic", 0.0, lead, service_target=target))
    matched_costs = []
    for result in frame.to_dict("records"):
        matched = min(independent_rows, key=lambda candidate: abs(float(candidate["average_inventory_units"]) - float(result["average_inventory_units"])))
        result["matched_independent_cost"] = float(matched["total_cost"])
        result["matched_independent_service_target"] = float(matched["service_target"])
        result["matched_cost_difference"] = float(result["total_cost"] - matched["total_cost"])
        matched_costs.append(result)
    frame = pd.DataFrame(matched_costs)
    baseline_fill = float(frame.loc[frame["alpha"] == min(ALPHA_CANDIDATES), "complete_basket_fill_rate"].iloc[0])
    eligible = frame.loc[frame["complete_basket_fill_rate"] >= baseline_fill + 0.01]
    if len(eligible):
        selected = float(eligible.sort_values(["matched_cost_difference", "alpha"]).iloc[0]["alpha"])
    else:
        selected = float(frame.sort_values(["matched_cost_difference", "alpha"]).iloc[0]["alpha"])
    return selected, frame


def run(root: Path, replications: int) -> dict[str, object]:
    processed = root / "data" / "processed"
    results_dir = root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    support_threshold = 20
    weekly, all_weeks, demand_all, products, train_idx, val_idx, test_idx = weekly_matrix(root, support_threshold=support_threshold)
    test_weeks = all_weeks[test_idx]
    val_weeks = all_weeks[val_idx]
    test_demand = demand_all[:, test_idx]
    val_demand = demand_all[:, val_idx]
    test_forecast, residual_std, selected_names, forecast_summary = build_forecasts(demand_all, train_idx, val_idx, test_idx)
    forecast_summary.to_csv(results_dir / "forecast_validation_summary.csv", index=False)
    test_forecast_summary = evaluate_test_forecast(demand_all, test_idx, test_forecast, selected_names)
    test_forecast_summary.to_csv(results_dir / "forecast_test_summary.csv", index=False)
    m5_summary = m5_benchmark(root, results_dir)
    network = network_scores(root, products, min_pair_count=5, top_k=5)
    val_forecast = np.zeros_like(val_demand)
    methods = ["recent4", "recent8", "seasonal52"]
    for j, idx in enumerate(val_idx):
        history = demand_all[:, :idx]
        candidates = np.stack([forecast_values(history, method) for method in methods], axis=0)
        val_forecast[:, j] = candidates[np.argmin(np.abs(candidates - val_demand[:, j][None, :]), axis=0) if False else np.zeros(len(products), dtype=int), np.arange(len(products))]
    # Reconstruct selected validation forecasts consistently with build_forecasts.
    selected_idx = np.array([methods.index(name) for name in selected_names])
    for j, idx in enumerate(val_idx):
        candidates = np.stack([forecast_values(demand_all[:, :idx], method) for method in methods], axis=0)
        val_forecast[:, j] = candidates[selected_idx, np.arange(len(products))]
    selected_alpha, alpha_calibration = calibrate_alpha(val_demand, val_weeks, val_forecast, residual_std, network, basket_map(root, products, val_weeks), products)
    alpha_calibration.to_csv(results_dir / "basket_alpha_validation_calibration.csv", index=False)

    scenarios = pd.read_csv(root / "data" / "synthetic" / "inventory_scenarios.csv")
    basket_data = basket_map(root, products, test_weeks)
    all_rows: list[dict[str, object]] = []
    for scenario in scenarios.itertuples(index=False):
        scenario_series = pd.Series(scenario._asdict())
        family = scenario_series["lead_time_distribution"]
        n_reps = 1 if family == "deterministic_7d" else replications
        for rep in range(n_reps):
            rng = np.random.default_rng(int(scenario_series["random_seed"]) + rep)
            lead_draws = np.vstack([sample_lead_weeks(scenario_series, rng, len(products)) for _ in range(len(test_weeks))])
            for policy in POLICIES:
                critical_fractile = float(scenario_series["shortage_penalty_per_unit"]) / float(scenario_series["shortage_penalty_per_unit"] + scenario_series["holding_cost_per_unit_week"])
                result = simulate_policy(test_demand, test_weeks, test_forecast, residual_std, network, basket_data, scenario_series, policy, selected_alpha, lead_draws, service_target=critical_fractile)
                result.update({"scenario_id": scenario_series["scenario_id"], "scenario_status": scenario_series["scenario_status"], "lead_time_distribution": family, "holding_cost_per_unit_week": scenario_series["holding_cost_per_unit_week"], "shortage_penalty_per_unit": scenario_series["shortage_penalty_per_unit"], "critical_fractile": critical_fractile, "replication": rep, "basket_alpha": selected_alpha})
                all_rows.append(result)
    raw_results = pd.DataFrame(all_rows)
    raw_results.to_csv(results_dir / "inventory_results_by_replication.csv", index=False)

    metrics = ["total_cost", "holding_cost", "shortage_cost", "ordering_cost", "purchase_cost", "average_inventory_units", "item_fill_rate", "complete_basket_fill_rate", "unmet_units", "stockout_frequency", "order_events", "average_order_units"]
    summary_rows = []
    for keys, frame in raw_results.groupby(["scenario_id", "policy"], sort=False):
        scenario_id, policy = keys
        row = {"scenario_id": scenario_id, "policy": policy, "replications": len(frame), "lead_time_distribution": frame["lead_time_distribution"].iloc[0], "holding_cost_per_unit_week": frame["holding_cost_per_unit_week"].iloc[0], "shortage_penalty_per_unit": frame["shortage_penalty_per_unit"].iloc[0], "basket_alpha": selected_alpha}
        for metric in metrics:
            values = frame[metric].to_numpy(float)
            row[f"{metric}_mean"] = float(values.mean())
            row[f"{metric}_p025"] = float(np.quantile(values, 0.025))
            row[f"{metric}_p975"] = float(np.quantile(values, 0.975))
        summary_rows.append(row)
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(results_dir / "inventory_summary.csv", index=False)

    pivots = []
    for scenario_id, frame in raw_results.groupby("scenario_id", sort=False):
        for rep, rep_frame in frame.groupby("replication"):
            values = rep_frame.set_index("policy")
            for basket_policy, base_policy, label in [
                ("P2_independent_stochastic", "P1_independent_deterministic", "P2_minus_P1"),
                ("P3_basket_deterministic", "P1_independent_deterministic", "P3_minus_P1"),
                ("P4_basket_stochastic", "P2_independent_stochastic", "P4_minus_P2"),
                ("P4_basket_stochastic", "P3_basket_deterministic", "P4_minus_P3"),
            ]:
                if basket_policy not in values.index or base_policy not in values.index:
                    continue
                row = {"scenario_id": scenario_id, "replication": rep, "contrast": label}
                for metric in ["total_cost", "average_inventory_units", "item_fill_rate", "complete_basket_fill_rate", "unmet_units", "stockout_frequency"]:
                    row[f"{metric}_difference"] = float(values.loc[basket_policy, metric] - values.loc[base_policy, metric])
                pivots.append(row)
    contrasts = pd.DataFrame(pivots)
    contrast_summary_rows = []
    for keys, frame in contrasts.groupby(["scenario_id", "contrast"], sort=False):
        scenario_id, contrast = keys
        row = {"scenario_id": scenario_id, "contrast": contrast, "replications": len(frame)}
        for column in [c for c in contrasts.columns if c.endswith("_difference")]:
            values = frame[column].to_numpy(float)
            row[f"{column}_mean"] = float(values.mean())
            row[f"{column}_p025"] = float(np.quantile(values, 0.025))
            row[f"{column}_p975"] = float(np.quantile(values, 0.975))
            row[f"{column}_probability_better"] = float((values < 0).mean()) if "cost" in column or "unmet" in column or "stockout" in column else float((values > 0).mean())
        contrast_summary_rows.append(row)
    contrast_summary = pd.DataFrame(contrast_summary_rows)
    contrast_summary.to_csv(results_dir / "policy_contrasts_summary.csv", index=False)

    config = {
        "train_end_week": str(all_weeks[train_idx[-1]].date()),
        "validation_start_week": str(all_weeks[val_idx[0]].date()),
        "validation_end_week": str(all_weeks[val_idx[-1]].date()),
        "test_start_week": str(all_weeks[test_idx[0]].date()),
        "test_end_week": str(all_weeks[test_idx[-1]].date()),
        "product_support_threshold": support_threshold,
        "products_simulated": int(len(products)),
        "test_weeks": int(len(test_weeks)),
        "forecast_selection": "lowest product-level validation MAE among recent4, recent8, and seasonal52",
        "basket_alpha_candidates": ALPHA_CANDIDATES,
        "selected_basket_alpha": selected_alpha,
        "basket_alpha_selection_rule": "validation alpha minimizing matched-inventory cost difference versus an independent policy, subject to at least a 1 percentage-point complete-basket-fill improvement over alpha zero",
        "cost_target_rule": "critical fractile p/(p+h), with p=shortage penalty per unit and h=holding cost per unit-week",
        "critical_fractile_break_even_rule": "basket-aware is preferred when p/h exceeds the scenario-specific break-even ratio computed from paired non-shortage cost and unmet-unit differences",
        "basket_score": "mean of top five directed training-period conditional co-purchase probabilities, clipped to 1",
        "initial_inventory": "common independent deterministic target using first test forecast and two-week protection",
        "warm_up_weeks": 0,
        "replay_event_order": "post scheduled receipts, place weekly order, evaluate in-universe basket proxy, then consume aggregate weekly demand",
        "out_of_universe_baskets": "baskets with no in-universe products are omitted; mixed baskets are projected onto in-universe products",
        "review_interval_weeks": 1,
        "coverage_weeks": 2,
        "basket_fulfilment_proxy": "share of observed test-week baskets whose full quantities fit within simulated on-hand stock at weekly review",
        "stockout_model": "lost sales; unmet units are not backordered in the primary analysis; backorder is a sensitivity condition",
        "stochastic_replications": replications,
        "deterministic_replications": 1,
        "replication_reason": "30 paired stochastic paths per non-deterministic scenario were used as a computationally tractable frozen budget; deterministic scenarios require one path, and test-week bootstrap resampling supplies an additional window-sensitivity analysis",
        "primary_contrast": "P4_minus_P2",
        "secondary_contrast": "P3_minus_P1",
        "lead_time_sampling": "clipped rounded normal for low/high variance; truncated exponential discrete distribution on 2 to 21 days for right-skewed family",
        "primary_cost": "holding plus shortage plus ordering plus normalized purchase cost",
        "observed_data_boundary": "inventory, supplier, lead-time, stockout, lost-sales, and historical cost fields are unavailable and remain synthetic or simulated",
    }
    (results_dir / "experiment_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    report = build_report(config, forecast_summary, m5_summary, alpha_calibration, summary, contrast_summary)
    (results_dir / "experiment_report.md").write_text(report, encoding="utf-8")
    return {"config": config, "forecast_summary": forecast_summary, "summary": summary, "contrasts": contrast_summary}


def markdown_table(frame: pd.DataFrame) -> str:
    frame = frame.copy()
    columns = [str(column) for column in frame.columns]
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for values in frame.itertuples(index=False, name=None):
        rendered = []
        for value in values:
            if isinstance(value, (float, np.floating)):
                rendered.append(f"{float(value):.6g}")
            else:
                rendered.append(str(value))
        lines.append("| " + " | ".join(rendered) + " |")
    return "\n".join(lines)


def build_report(config: dict[str, object], forecast_summary: pd.DataFrame, m5_summary: pd.DataFrame, alpha_calibration: pd.DataFrame, summary: pd.DataFrame, contrasts: pd.DataFrame) -> str:
    lines = [
        "# Executed forecast and inventory simulation results",
        "",
        "## Evidence boundary",
        "",
        "The UCI transaction and basket tables are observed or directly derived. Inventory states, lead times, costs, stockouts, unmet units, and policy outcomes below are simulated under the frozen configuration. M5 remains a separate forecasting benchmark and is not merged with UCI.",
        "",
        "## Frozen configuration",
        "",
        f"- Product universe: {config['products_simulated']} products with at least 20 positive training weeks.",
        f"- Forecast split: training through {config['train_end_week']}; validation {config['validation_start_week']} to {config['validation_end_week']}; test {config['test_start_week']} to {config['test_end_week']}.",
        f"- Selected basket buffer alpha: {config['selected_basket_alpha']} from candidates {config['basket_alpha_candidates']}.",
        "- Active service target: critical fractile p/(p+h), with p equal to shortage penalty and h equal to holding cost.",
        f"- Stochastic replications: {config['stochastic_replications']}; deterministic scenarios: one deterministic run.",
        "",
        "## Forecast validation",
        "",
        markdown_table(forecast_summary),
        "",
        "## M5 benchmark sample",
        "",
        markdown_table(m5_summary),
        "",
        "## Basket-buffer calibration",
        "",
        markdown_table(alpha_calibration[["alpha", "total_cost", "item_fill_rate", "complete_basket_fill_rate", "unmet_units"]]),
        "",
        "## Inventory summary",
        "",
        markdown_table(summary[["scenario_id", "policy", "replications", "total_cost_mean", "average_inventory_units_mean", "item_fill_rate_mean", "complete_basket_fill_rate_mean", "unmet_units_mean"]]),
        "",
        "## Basket-aware policy contrasts",
        "",
        markdown_table(contrasts[["scenario_id", "contrast", "total_cost_difference_mean", "total_cost_difference_p025", "total_cost_difference_p975", "item_fill_rate_difference_mean", "complete_basket_fill_rate_difference_mean"]]),
        "",
        "## Interpretation",
        "",
        "The policy contrasts are paired differences within scenario and replication. Negative cost differences favor the basket-aware policy; positive fill-rate differences favor it. Deterministic scenarios have no stochastic interval because the demand path and lead time are fixed. These are comparative simulation findings, not observed retailer savings or historical stockout estimates.",
        "",
        "P0 robustness outputs are generated by `scripts/run_p0_analyses.py`: `frontier_results.csv`, `frontier_plot.png`, `placebo_results.csv`, `inventory_matched_baseline.csv`, `break_even_analysis.csv`, and `sensitivity_results.csv`.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None)
    parser.add_argument("--replications", type=int, default=30)
    args = parser.parse_args()
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    result = run(root, args.replications)
    print(json.dumps({"results_dir": str(root / 'results'), "products_simulated": result["config"]["products_simulated"], "selected_alpha": result["config"]["selected_basket_alpha"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
