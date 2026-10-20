"""Validation-only evaluation for the edge-level Phase 2 policies and controls."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from run_experiment import basket_map, network_scores, sample_lead_weeks, simulate_policy, weekly_matrix  # noqa: E402
from run_phase1_calibration import SEED, build_validation_forecasts, internal_calibration  # noqa: E402
from phase2_policy_components import (  # noqa: E402
    DEFAULT_MIN_PAIR_COUNT,
    DEFAULT_TOP_K,
    basket_coverage_score,
    buffers_from_graphs,
    default_edges,
    rewired_edges,
    shuffled_basket_edges,
    stale_edges,
    training_volume,
)


ALPHA_GRID = [0.5, 1.0, 1.5, 2.0, 3.0]
TAU_GRID = [0.50, 0.75, 0.90]
SAFETY_MULTIPLIER = 6.0
TARGET_GRID = [0.80, 0.85, 0.90, 0.95, 0.975, 0.99, 0.995, 0.999, 0.9999, 0.99999, 0.999999, 0.9999999]
VARIANTS = ["PA1", "PA2", "PA3", "C2", "C3", "C4", "C5"]


def lead_matrix(scenario: pd.Series, policy: str, horizon: int, n_products: int, rep: int) -> np.ndarray:
    if policy.endswith("_deterministic"):
        return np.ones((horizon, n_products), dtype=int)
    rng = np.random.default_rng(SEED + int(str(scenario["scenario_id"])[1:]) * 10000 + rep)
    return np.vstack([sample_lead_weeks(scenario, rng, n_products) for _ in range(horizon)])


def independent_name(stochastic: bool) -> str:
    return "P2_independent_stochastic" if stochastic else "P1_independent_deterministic"


def pair_name(variant: str, stochastic: bool) -> str:
    return f"{variant}_{'stochastic' if stochastic else 'deterministic'}"


def run_variant(demand: np.ndarray, weeks: pd.Index, forecast: np.ndarray, residual_scale: np.ndarray, network: np.ndarray, baskets: dict, scenario: pd.Series, policy: str, alpha: float, lead: np.ndarray, buffer: np.ndarray | None, service_target: float) -> dict[str, object]:
    return simulate_policy(
        demand,
        weeks,
        forecast,
        residual_scale * SAFETY_MULTIPLIER,
        network,
        baskets,
        scenario,
        policy,
        alpha,
        lead,
        service_target=service_target,
        basket_buffer=buffer,
    )


def match_independent(demand: np.ndarray, weeks: pd.Index, forecast: np.ndarray, residual_scale: np.ndarray, network: np.ndarray, baskets: dict, scenario: pd.Series, independent: str, lead: np.ndarray, basket_result: dict[str, object]) -> dict[str, object]:
    candidates = [run_variant(demand, weeks, forecast, residual_scale, network, baskets, scenario, independent, 0.0, lead, None, target) for target in TARGET_GRID]
    candidates = sorted(candidates, key=lambda result: float(result["service_target"]))
    basket_inventory = float(basket_result["average_inventory_units"])
    interpolated = []
    for low, high in zip(candidates[:-1], candidates[1:]):
        low_inventory = float(low["average_inventory_units"])
        high_inventory = float(high["average_inventory_units"])
        if low_inventory <= basket_inventory <= high_inventory and high_inventory > low_inventory:
            weight = (basket_inventory - low_inventory) / (high_inventory - low_inventory)
            target = float(low["service_target"]) + weight * (float(high["service_target"]) - float(low["service_target"]))
            interpolated.append(run_variant(demand, weeks, forecast, residual_scale, network, baskets, scenario, independent, 0.0, lead, None, target))
            break
    candidates.extend(interpolated)
    return min(candidates, key=lambda result: (abs(float(result["average_inventory_units"]) - basket_inventory), float(result["service_target"])))


def evaluate_tuning(root: Path, demand: np.ndarray, weeks: pd.Index, products: np.ndarray, val_idx: np.ndarray, forecast: np.ndarray, residual_scale: np.ndarray, network: np.ndarray, baskets: dict, scenarios: pd.DataFrame, graphs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    val_demand = demand[:, val_idx]
    val_weeks = weeks[val_idx]
    # One common validation path per scenario is used for hyperparameter tuning;
    # all paths are used for the frozen validation comparison below.
    for tau in TAU_GRID:
        buffers, _ = buffers_from_graphs(root, products, residual_scale, SAFETY_MULTIPLIER, graphs["default"], graphs["stale"], graphs["shuffled"], graphs["rewired"], tau=tau)
        for alpha in ALPHA_GRID:
            for scenario_dict in scenarios.to_dict("records"):
                scenario = pd.Series(scenario_dict)
                nominal = float(scenario["shortage_penalty_per_unit"]) / (float(scenario["shortage_penalty_per_unit"]) + float(scenario["holding_cost_per_unit_week"]))
                stochastic = scenario["lead_time_distribution"] != "deterministic_7d"
                policy = pair_name("PA1", stochastic)
                lead = lead_matrix(scenario, policy, len(val_idx), len(products), rep=0)
                basket_result = run_variant(val_demand, val_weeks, forecast, residual_scale, network, baskets, scenario, policy, alpha, lead, buffers["PA1"], nominal)
                independent = independent_name(stochastic)
                control = match_independent(val_demand, val_weeks, forecast, residual_scale, network, baskets, scenario, independent, lead, basket_result)
                rows.append({"variant": "PA1", "alpha": alpha, "tau": tau, "scenario_id": scenario["scenario_id"], "item_fill_gain": float(basket_result["item_fill_rate"]) - float(control["item_fill_rate"]), "basket_fill_gain": float(basket_result["complete_basket_fill_rate"]) - float(control["complete_basket_fill_rate"]), "inventory_difference": float(basket_result["average_inventory_units"]) - float(control["average_inventory_units"]), "cost_difference": float(basket_result["total_cost"]) - float(control["total_cost"])})
                policy = pair_name("PA3", stochastic)
                basket_result = run_variant(val_demand, val_weeks, forecast, residual_scale, network, baskets, scenario, policy, alpha, lead, buffers["PA3"], nominal)
                control = match_independent(val_demand, val_weeks, forecast, residual_scale, network, baskets, scenario, independent, lead, basket_result)
                rows.append({"variant": "PA3", "alpha": alpha, "tau": tau, "scenario_id": scenario["scenario_id"], "item_fill_gain": float(basket_result["item_fill_rate"]) - float(control["item_fill_rate"]), "basket_fill_gain": float(basket_result["complete_basket_fill_rate"]) - float(control["complete_basket_fill_rate"]), "inventory_difference": float(basket_result["average_inventory_units"]) - float(control["average_inventory_units"]), "cost_difference": float(basket_result["total_cost"]) - float(control["total_cost"])})
    return pd.DataFrame(rows)


def main() -> None:
    parser = __import__("argparse").ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    out = root / "results"
    out.mkdir(parents=True, exist_ok=True)

    _weekly, weeks, demand, products, train_idx, val_idx, _test_idx = weekly_matrix(root, support_threshold=20)
    points, scales, _selected, _bias = build_validation_forecasts(demand, train_idx, val_idx)
    forecast = points["empirical_quantile"]
    residual_scale = scales["empirical_quantile"]
    network = network_scores(root, products, min_pair_count=DEFAULT_MIN_PAIR_COUNT, top_k=DEFAULT_TOP_K)
    val_weeks = weeks[val_idx]
    baskets = basket_map(root, products, val_weeks)
    scenarios = pd.read_csv(root / "data" / "synthetic" / "inventory_scenarios.csv")
    graphs = {
        "default": default_edges(root, products),
        "stale": stale_edges(root, products),
    }
    graphs["shuffled"] = shuffled_basket_edges(root, products, seed=SEED)
    graphs["rewired"] = rewired_edges(graphs["default"], seed=SEED)

    tuning = evaluate_tuning(root, demand, weeks, products, val_idx, forecast, residual_scale, network, baskets, scenarios, graphs)
    tuning_summary = tuning.groupby(["variant", "alpha", "tau"], as_index=False)[["item_fill_gain", "basket_fill_gain", "inventory_difference", "cost_difference"]].mean()
    tuning_summary.to_csv(out / "phase2_validation_tuning.csv", index=False)
    selected = tuning_summary.sort_values(["basket_fill_gain", "item_fill_gain", "alpha", "tau"], ascending=[False, False, True, True]).iloc[0]
    selected_alpha = float(selected["alpha"])
    selected_tau = float(selected["tau"])

    buffers, metadata = buffers_from_graphs(root, products, residual_scale, SAFETY_MULTIPLIER, graphs["default"], graphs["stale"], graphs["shuffled"], graphs["rewired"], tau=selected_tau)
    rows: list[dict[str, object]] = []
    matched_rows: list[dict[str, object]] = []
    for scenario_dict in scenarios.to_dict("records"):
        scenario = pd.Series(scenario_dict)
        nominal = float(scenario["shortage_penalty_per_unit"]) / (float(scenario["shortage_penalty_per_unit"]) + float(scenario["holding_cost_per_unit_week"]))
        rep_count = 1 if scenario["lead_time_distribution"] == "deterministic_7d" else 30
        for rep in range(rep_count):
            for stochastic in [False, True]:
                independent = independent_name(stochastic)
                lead = lead_matrix(scenario, independent, len(val_idx), len(products), rep)
                control_cache: dict[float, dict[str, object]] = {}
                for target in TARGET_GRID:
                    control_cache[target] = run_variant(demand[:, val_idx], val_weeks, forecast, residual_scale, network, baskets, scenario, independent, 0.0, lead, None, target)
                for variant in VARIANTS:
                    policy = pair_name(variant, stochastic)
                    result = run_variant(demand[:, val_idx], val_weeks, forecast, residual_scale, network, baskets, scenario, policy, selected_alpha, lead, buffers[variant], nominal)
                    rows.append({"scenario_id": scenario["scenario_id"], "replication": rep, "variant": variant, "policy": policy, "nominal_target": nominal, "alpha": selected_alpha, "tau": selected_tau, **result})
                    control = min(control_cache.values(), key=lambda candidate: (abs(float(candidate["average_inventory_units"]) - float(result["average_inventory_units"])), float(candidate["service_target"])))
                    matched_rows.append({"scenario_id": scenario["scenario_id"], "replication": rep, "variant": variant, "policy": policy, "independent_policy": independent, "matched_service_target": control["service_target"], "item_fill_gain": float(result["item_fill_rate"]) - float(control["item_fill_rate"]), "basket_fill_gain": float(result["complete_basket_fill_rate"]) - float(control["complete_basket_fill_rate"]), "cost_difference": float(result["total_cost"]) - float(control["total_cost"]), "inventory_difference": float(result["average_inventory_units"]) - float(control["average_inventory_units"])})

    frame = pd.DataFrame(rows)
    frame.to_csv(out / "phase2_validation_results.csv", index=False)
    matched = pd.DataFrame(matched_rows)
    matched.to_csv(out / "phase2_validation_matched.csv", index=False)
    matched_summary = matched.groupby("variant", as_index=False)[["item_fill_gain", "basket_fill_gain", "cost_difference", "inventory_difference"]].agg(["mean", lambda x: x.quantile(0.025), lambda x: x.quantile(0.975)])
    matched_summary.columns = ["_".join(str(v) for v in col if str(v) != "") for col in matched_summary.columns]
    matched_summary.reset_index().to_csv(out / "phase2_validation_matched_summary.csv", index=False)

    config = {
        "phase": 2,
        "window": "validation_only",
        "primary_estimand": "service_at_matched_inventory",
        "forecast": "empirical_quantile",
        "safety_multiplier": SAFETY_MULTIPLIER,
        "selected_alpha": selected_alpha,
        "selected_tau": selected_tau,
        "alpha_grid": ALPHA_GRID,
        "tau_grid": TAU_GRID,
        "matching_target_grid": TARGET_GRID,
        "matching_method": "grid_then_one_linear_interpolation_replay",
        "min_pair_count": DEFAULT_MIN_PAIR_COUNT,
        "top_k": DEFAULT_TOP_K,
        "seed": SEED,
        "test_window_used": False,
        "graph_metadata": metadata,
    }
    config["config_hash"] = hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    (out / "phase2_validation_config.json").write_text(json.dumps(config, indent=2, default=str), encoding="utf-8")
    log_row = pd.DataFrame([{
        "config_hash": config["config_hash"], "date": pd.Timestamp.now(tz="Asia/Dhaka").isoformat(), "seed": SEED,
        "phase": "phase2_validation_only", "split": "train_validation_only", "scenario": "all_scenarios",
        "policy": "PA1-PA3_and_C2-C5", "replication": "1 deterministic / 30 stochastic", "test_window_used": False,
        "status": "completed", "outputs": "phase2_validation_tuning.csv;phase2_validation_results.csv;phase2_validation_matched.csv;phase2_validation_matched_summary.csv",
    }])
    log_row.to_csv(out / "run_log.csv", mode="a", header=False, index=False)

    p1 = matched.loc[matched["variant"] == "PA1"]
    controls = matched.groupby("variant")["item_fill_gain"].mean().to_dict()
    report = "\n".join([
        "# Phase 2 validation report",
        "",
        "Phase 2 was validation-only; no held-out test result was read or used for tuning.",
        "",
        f"The selected validation setting was alpha = {selected_alpha:g} and PA3 threshold quantile = {selected_tau:g}, chosen by scenario-averaged complete-basket-fill gain at matched inventory. The edge construction retained {metadata['default_edges']:,} default edges; rewired, shuffled-basket, and stale graphs retained {metadata['rewired_edges']:,}, {metadata['shuffled_edges']:,}, and {metadata['stale_edges']:,} records. All buffers were scaled to total mass {metadata['pa1_buffer_total']:.2f} units.",
        "",
        f"PA1 matched item-fill gain averaged {p1['item_fill_gain'].mean():.6f}; the matched complete-basket gain averaged {p1['basket_fill_gain'].mean():.6f}. Mean matched item-fill gains by variant were: " + ", ".join(f"{key}={value:.6f}" for key, value in sorted(controls.items())) + ".",
        "",
        "These validation results establish the frozen Phase 2 configuration but do not establish a test-window effect. The next step is a single guarded test replay under the recorded Phase 2 hash.",
        "",
        "Files: `phase2_preregistration_addendum.md`, `phase2_validation_config.json`, `phase2_validation_tuning.csv`, `phase2_validation_results.csv`, `phase2_validation_matched.csv`, `phase2_validation_matched_summary.csv`, and `run_log.csv`.",
    ])
    (out / "phase_2_report.md").write_text(report + "\n", encoding="utf-8")
    print(json.dumps({"config_hash": config["config_hash"], "selected_alpha": selected_alpha, "selected_tau": selected_tau, "rows": len(frame), "matched_rows": len(matched)}, indent=2))


if __name__ == "__main__":
    main()
