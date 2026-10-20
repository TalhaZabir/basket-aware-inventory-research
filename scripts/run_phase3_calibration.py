"""Validation-only alpha calibration for the Phase 3 frozen replay."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from run_phase1_calibration import build_validation_forecasts, internal_calibration  # noqa: E402
from run_experiment import basket_map, network_scores, weekly_matrix  # noqa: E402
from phase2_policy_components import DEFAULT_MIN_PAIR_COUNT, DEFAULT_TOP_K, buffers_from_graphs, default_edges, rewired_edges, shuffled_basket_edges, stale_edges  # noqa: E402
from run_phase2_validation import SAFETY_MULTIPLIER, lead_matrix, run_variant, TARGET_GRID  # noqa: E402

ALPHA_GRID = [0.10, 0.25, 0.50, 0.75, 1.00, 1.50, 2.00, 3.00, 4.00, 5.00]
MATCH_TOLERANCE = 0.01
SERVICE_GAIN_THRESHOLD = 0.05
SEED = 20261020


def match(candidates: list[dict[str, object]], basket_result: dict[str, object], run_interp) -> dict[str, object]:
    target_inventory = float(basket_result["average_inventory_units"])
    for candidate in candidates:
        relative_gap = abs(float(candidate["average_inventory_units"]) - target_inventory) / max(target_inventory, 1.0)
        if relative_gap <= MATCH_TOLERANCE:
            candidate = dict(candidate)
            candidate["relative_inventory_gap"] = relative_gap
            return candidate
    ordered = sorted(candidates, key=lambda x: float(x["service_target"]))
    for low, high in zip(ordered[:-1], ordered[1:]):
        li = float(low["average_inventory_units"])
        hi = float(high["average_inventory_units"])
        if li <= target_inventory <= hi and hi > li:
            w = (target_inventory - li) / (hi - li)
            target = float(low["service_target"]) + w * (float(high["service_target"]) - float(low["service_target"]))
            interpolated = run_interp(target)
            gap = abs(float(interpolated["average_inventory_units"]) - target_inventory) / max(target_inventory, 1.0)
            if gap <= MATCH_TOLERANCE:
                interpolated = dict(interpolated)
                interpolated["relative_inventory_gap"] = gap
                return interpolated
    best = min(candidates, key=lambda x: abs(float(x["average_inventory_units"]) - target_inventory))
    best = dict(best)
    best["relative_inventory_gap"] = abs(float(best["average_inventory_units"]) - target_inventory) / max(target_inventory, 1.0)
    return best


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out = root / "results"
    _weekly, weeks, demand, products, train_idx, val_idx, _test_idx = weekly_matrix(root, support_threshold=20)
    points, scales, _selected, _bias = build_validation_forecasts(demand, train_idx, val_idx)
    forecast = points["empirical_quantile"]
    residual_scale = scales["empirical_quantile"]
    baskets = basket_map(root, products, weeks[val_idx])
    network = network_scores(root, products, min_pair_count=DEFAULT_MIN_PAIR_COUNT, top_k=DEFAULT_TOP_K)
    graphs = {"default": default_edges(root, products), "stale": stale_edges(root, products)}
    graphs["shuffled"] = shuffled_basket_edges(root, products, seed=SEED)
    graphs["rewired"] = rewired_edges(graphs["default"], seed=SEED)
    buffers, metadata = buffers_from_graphs(root, products, residual_scale, SAFETY_MULTIPLIER, graphs["default"], graphs["stale"], graphs["shuffled"], graphs["rewired"], tau=0.50)
    scenarios = pd.read_csv(root / "data" / "synthetic" / "inventory_scenarios.csv")
    val_demand, val_weeks = demand[:, val_idx], weeks[val_idx]
    rows = []
    for scenario_dict in scenarios.to_dict("records"):
        scenario = pd.Series(scenario_dict)
        stochastic = scenario["lead_time_distribution"] != "deterministic_7d"
        independent = "P2_independent_stochastic" if stochastic else "P1_independent_deterministic"
        lead = lead_matrix(scenario, independent, len(val_idx), len(products), 0)
        nominal = float(scenario["shortage_penalty_per_unit"]) / (float(scenario["shortage_penalty_per_unit"]) + float(scenario["holding_cost_per_unit_week"]))
        controls = [run_variant(val_demand, val_weeks, forecast, residual_scale, network, baskets, scenario, independent, 0.0, lead, None, target) for target in TARGET_GRID]
        for alpha in ALPHA_GRID:
            pa = run_variant(val_demand, val_weeks, forecast, residual_scale, network, baskets, scenario, "PA1_stochastic" if stochastic else "PA1_deterministic", alpha, lead, buffers["PA1"], nominal)
            ctrl = match(controls, pa, lambda target: run_variant(val_demand, val_weeks, forecast, residual_scale, network, baskets, scenario, independent, 0.0, lead, None, target))
            rows.append({"scenario_id": scenario["scenario_id"], "alpha": alpha, "nominal_target": nominal, "item_fill_gain": float(pa["item_fill_rate"])-float(ctrl["item_fill_rate"]), "basket_fill_gain": float(pa["complete_basket_fill_rate"])-float(ctrl["complete_basket_fill_rate"]), "cost_difference": float(pa["total_cost"])-float(ctrl["total_cost"]), "relative_inventory_gap": float(ctrl["relative_inventory_gap"]), "pa_inventory": float(pa["average_inventory_units"]), "control_inventory": float(ctrl["average_inventory_units"])})
    frame = pd.DataFrame(rows)
    frame.to_csv(out / "phase3_alpha_validation.csv", index=False)
    grouped = frame.groupby("alpha", as_index=False)[["item_fill_gain", "basket_fill_gain", "cost_difference", "relative_inventory_gap"]].mean()
    baseline_basket = float(grouped.loc[grouped["alpha"] == 0.10, "basket_fill_gain"].iloc[0])
    eligible = grouped.loc[(grouped["basket_fill_gain"] >= baseline_basket + SERVICE_GAIN_THRESHOLD) & (grouped["relative_inventory_gap"] <= MATCH_TOLERANCE)]
    if eligible.empty:
        raise SystemExit("No alpha met the pre-registered validation service and matching rules.")
    chosen = float(eligible.sort_values(["cost_difference", "alpha"]).iloc[0]["alpha"])
    if chosen in {min(ALPHA_GRID), max(ALPHA_GRID)}:
        raise SystemExit(f"Selected alpha {chosen} is still a grid boundary; extend the grid before test replay.")
    config = {"phase": 3, "alpha_grid": ALPHA_GRID, "selected_alpha": chosen, "match_tolerance": MATCH_TOLERANCE, "service_gain_threshold": SERVICE_GAIN_THRESHOLD, "parent": "phase2_test_config.json", "graph_metadata": metadata}
    config["config_hash"] = hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode()).hexdigest()
    (out / "phase3_alpha_validation_config.json").write_text(json.dumps(config, indent=2, default=str), encoding="utf-8")
    grouped.to_csv(out / "phase3_alpha_validation_summary.csv", index=False)
    print(json.dumps({"selected_alpha": chosen, "config_hash": config["config_hash"], "summary": grouped.to_dict("records")}, indent=2, default=str))


if __name__ == "__main__":
    main()
