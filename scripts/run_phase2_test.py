"""Guarded single test replay for the frozen Phase 2 policy comparison."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from run_experiment import basket_map, network_scores, weekly_matrix  # noqa: E402
from run_phase1_calibration import SEED, build_validation_forecasts, internal_calibration  # noqa: E402
from phase2_policy_components import DEFAULT_MIN_PAIR_COUNT, DEFAULT_TOP_K, buffers_from_graphs, default_edges, rewired_edges, shuffled_basket_edges, stale_edges  # noqa: E402
from run_phase2_validation import (  # noqa: E402
    ALPHA_GRID,
    SAFETY_MULTIPLIER,
    TARGET_GRID,
    VARIANTS,
    lead_matrix,
    match_independent,
    pair_name,
    run_variant,
)


FROZEN_ALPHA = 3.0
FROZEN_TAU = 0.50
PARENT_VALIDATION_HASH = "677bfb9345b95983bf1fb63fee0e4dd8da3ac63b372530d6c76587aaf5482e44"
REPLICATIONS = 30


def build_test_empirical_forecast(demand: np.ndarray, test_idx: np.ndarray) -> np.ndarray:
    forecast = np.zeros((demand.shape[0], len(test_idx)), dtype=float)
    for j, idx in enumerate(test_idx):
        history = demand[:, :idx]
        forecast[:, j] = np.quantile(history[:, -min(26, history.shape[1]):], 0.50, axis=1)
    return forecast


def main() -> None:
    parser = __import__("argparse").ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    out = root / "results"
    log_path = out / "run_log.csv"
    if log_path.exists():
        log = pd.read_csv(log_path, dtype="string")
        prior = log.loc[(log["phase"] == "phase2_test_frozen") & (log["status"].isin(["primary_replay", "duplicate_invocation_ignored"]))]
        if len(prior):
            raise SystemExit("Refusing to rerun the Phase 2 test window: a frozen primary replay is already logged.")

    _weekly, weeks, demand, products, train_idx, val_idx, test_idx = weekly_matrix(root, support_threshold=20)
    test_weeks = weeks[test_idx]
    internal = internal_calibration(demand, train_idx)
    residual_scale = internal["scale"]
    forecast = build_test_empirical_forecast(demand, test_idx)
    test_demand = demand[:, test_idx]
    network = network_scores(root, products, min_pair_count=DEFAULT_MIN_PAIR_COUNT, top_k=DEFAULT_TOP_K)
    baskets = basket_map(root, products, test_weeks)
    scenarios = pd.read_csv(root / "data" / "synthetic" / "inventory_scenarios.csv")
    graphs = {"default": default_edges(root, products), "stale": stale_edges(root, products)}
    graphs["shuffled"] = shuffled_basket_edges(root, products, seed=SEED)
    graphs["rewired"] = rewired_edges(graphs["default"], seed=SEED)
    buffers, metadata = buffers_from_graphs(root, products, residual_scale, SAFETY_MULTIPLIER, graphs["default"], graphs["stale"], graphs["shuffled"], graphs["rewired"], tau=FROZEN_TAU)

    rows: list[dict[str, object]] = []
    matched_rows: list[dict[str, object]] = []
    for scenario_dict in scenarios.to_dict("records"):
        scenario = pd.Series(scenario_dict)
        nominal = float(scenario["shortage_penalty_per_unit"]) / (float(scenario["shortage_penalty_per_unit"]) + float(scenario["holding_cost_per_unit_week"]))
        rep_count = 1 if scenario["lead_time_distribution"] == "deterministic_7d" else REPLICATIONS
        for rep in range(rep_count):
            for stochastic in [False, True]:
                independent = "P2_independent_stochastic" if stochastic else "P1_independent_deterministic"
                lead = lead_matrix(scenario, independent, len(test_idx), len(products), rep)
                # The independent control grid is identical for every basket-aware
                # variant within this scenario/replication.  Cache it once rather
                # than replaying the same 12 targets seven times per row.
                control_candidates = [
                    run_variant(test_demand, test_weeks, forecast, residual_scale, network, baskets, scenario, independent, 0.0, lead, None, target)
                    for target in TARGET_GRID
                ]

                def cached_match(basket_result: dict[str, object]) -> dict[str, object]:
                    basket_inventory = float(basket_result["average_inventory_units"])
                    candidates = sorted(control_candidates, key=lambda result: float(result["service_target"]))
                    interpolated = []
                    for low, high in zip(candidates[:-1], candidates[1:]):
                        low_inventory = float(low["average_inventory_units"])
                        high_inventory = float(high["average_inventory_units"])
                        if low_inventory <= basket_inventory <= high_inventory and high_inventory > low_inventory:
                            weight = (basket_inventory - low_inventory) / (high_inventory - low_inventory)
                            target = float(low["service_target"]) + weight * (float(high["service_target"]) - float(low["service_target"]))
                            interpolated.append(run_variant(test_demand, test_weeks, forecast, residual_scale, network, baskets, scenario, independent, 0.0, lead, None, target))
                            break
                    return min(candidates + interpolated, key=lambda result: (abs(float(result["average_inventory_units"]) - basket_inventory), float(result["service_target"])))

                for variant in VARIANTS:
                    policy = pair_name(variant, stochastic)
                    result = run_variant(test_demand, test_weeks, forecast, residual_scale, network, baskets, scenario, policy, FROZEN_ALPHA, lead, buffers[variant], nominal)
                    rows.append({"scenario_id": scenario["scenario_id"], "replication": rep, "variant": variant, "policy": policy, "nominal_target": nominal, "alpha": FROZEN_ALPHA, "tau": FROZEN_TAU, **result})
                    control = cached_match(result)
                    matched_rows.append({"scenario_id": scenario["scenario_id"], "replication": rep, "variant": variant, "policy": policy, "independent_policy": independent, "matched_service_target": control["service_target"], "basket_average_inventory_units": result["average_inventory_units"], "independent_average_inventory_units": control["average_inventory_units"], "item_fill_gain": float(result["item_fill_rate"]) - float(control["item_fill_rate"]), "basket_fill_gain": float(result["complete_basket_fill_rate"]) - float(control["complete_basket_fill_rate"]), "cost_difference": float(result["total_cost"]) - float(control["total_cost"]), "inventory_difference": float(result["average_inventory_units"]) - float(control["average_inventory_units"])})

    frame = pd.DataFrame(rows)
    matched = pd.DataFrame(matched_rows)
    frame.to_csv(out / "phase2_test_results.csv", index=False)
    matched.to_csv(out / "phase2_test_matched.csv", index=False)
    summary = frame.groupby(["scenario_id", "variant", "policy"], as_index=False)[["total_cost", "average_inventory_units", "item_fill_rate", "complete_basket_fill_rate", "unmet_units", "stockout_frequency"]].mean()
    summary.to_csv(out / "phase2_test_summary.csv", index=False)
    matched_summary = matched.groupby("variant", as_index=False)[["item_fill_gain", "basket_fill_gain", "cost_difference", "inventory_difference"]].agg(["mean", lambda x: x.quantile(0.025), lambda x: x.quantile(0.975)])
    matched_summary.columns = ["_".join(str(v) for v in col if str(v) != "") for col in matched_summary.columns]
    matched_summary.reset_index().to_csv(out / "phase2_test_matched_summary.csv", index=False)

    config = {
        "phase": 2,
        "parent_validation_hash": PARENT_VALIDATION_HASH,
        "primary_estimand": "service_at_matched_inventory",
        "forecast": "empirical_quantile",
        "safety_multiplier": SAFETY_MULTIPLIER,
        "alpha": FROZEN_ALPHA,
        "tau": FROZEN_TAU,
        "alpha_grid_frozen_before_test": ALPHA_GRID,
        "matching_target_grid": TARGET_GRID,
        "min_pair_count": DEFAULT_MIN_PAIR_COUNT,
        "top_k": DEFAULT_TOP_K,
        "seed": SEED,
        "stochastic_replications": REPLICATIONS,
        "deterministic_replications": 1,
        "test_window_used": True,
        "outputs": ["phase2_test_results.csv", "phase2_test_summary.csv", "phase2_test_matched.csv", "phase2_test_matched_summary.csv"],
        "graph_metadata": metadata,
    }
    config["config_hash"] = hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    (out / "phase2_test_config.json").write_text(json.dumps(config, indent=2, default=str), encoding="utf-8")
    pd.DataFrame([{
        "config_hash": config["config_hash"], "date": pd.Timestamp.now(tz="Asia/Dhaka").isoformat(), "seed": SEED,
        "phase": "phase2_test_frozen", "split": "train_validation_test", "scenario": "all_scenarios",
        "policy": "PA1-PA3_and_C2-C5", "replication": "1 deterministic / 30 stochastic", "test_window_used": True,
        "status": "primary_replay", "outputs": ";".join(config["outputs"]),
    }]).to_csv(log_path, mode="a", header=False, index=False)

    report_rows = []
    for variant, group in matched.groupby("variant"):
        report_rows.append(f"{variant}: item-fill gain {group['item_fill_gain'].mean():.6f} [{group['item_fill_gain'].quantile(.025):.6f}, {group['item_fill_gain'].quantile(.975):.6f}], basket-fill gain {group['basket_fill_gain'].mean():.6f} [{group['basket_fill_gain'].quantile(.025):.6f}, {group['basket_fill_gain'].quantile(.975):.6f}], cost difference {group['cost_difference'].mean():.2f}")
    report = "\n".join([
        "# Phase 2 frozen test report",
        "",
        f"This is the single guarded Phase 2 replay under parent validation hash `{PARENT_VALIDATION_HASH}`. No test result was used to tune alpha, tau, graph construction, or matching.",
        "",
        *report_rows,
        "",
        "The matched rows use the preregistered target grid plus one interpolation replay when needed. Results are based on 30 stochastic replications and one deterministic path per deterministic scenario; they are not the Phase 3 100-replication or bootstrap analysis.",
        "",
        "Files: `phase2_test_config.json`, `phase2_test_results.csv`, `phase2_test_summary.csv`, `phase2_test_matched.csv`, `phase2_test_matched_summary.csv`, and `run_log.csv`.",
    ])
    (out / "phase_2_test_report.md").write_text(report + "\n", encoding="utf-8")
    print(json.dumps({"config_hash": config["config_hash"], "rows": len(frame), "matched_rows": len(matched)}, indent=2))


if __name__ == "__main__":
    main()
