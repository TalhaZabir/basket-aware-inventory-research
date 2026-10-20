"""Run the frozen Phase 1 forecast on the held-out test window.

This script is executed only after the validation configuration is frozen in
results/preregistration.md. It uses no test information for tuning.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from run_experiment import (  # noqa: E402
    basket_map,
    network_scores,
    sample_lead_weeks,
    simulate_policy,
    weekly_matrix,
)
from run_phase1_calibration import (  # noqa: E402
    SEED,
    internal_calibration,
    point_forecast,
)


ALPHA = 1.5
SAFETY_MULTIPLIER = 6.0
REPLICATIONS = 30
TARGET_GRID = [0.80, 0.85, 0.90, 0.95, 0.975, 0.99, 0.995]
POLICIES = [
    "P1_independent_deterministic",
    "P2_independent_stochastic",
    "P3_basket_deterministic",
    "P4_basket_stochastic",
]


def test_forecast(demand: np.ndarray, test_idx: np.ndarray, scale: np.ndarray) -> tuple[np.ndarray, pd.DataFrame]:
    point = np.zeros((demand.shape[0], len(test_idx)), dtype=float)
    lower = np.zeros_like(point)
    upper = np.zeros_like(point)
    for j, idx in enumerate(test_idx):
        history = demand[:, :idx]
        sample = history[:, -min(26, history.shape[1]):]
        point[:, j] = np.quantile(sample, 0.50, axis=1)
        lower[:, j] = np.quantile(sample, 0.05, axis=1)
        upper[:, j] = np.quantile(sample, 0.95, axis=1)
    actual = demand[:, test_idx]
    error = point - actual
    metrics = pd.DataFrame([{
        "model": "empirical_quantile_frozen",
        "test_mae": float(np.abs(error).mean()),
        "test_wape": float(np.abs(error).sum() / max(np.abs(actual).sum(), 1.0)),
        "test_bias": float(error.mean()),
        "test_90pct_coverage": float(((actual >= lower) & (actual <= upper)).mean()),
        "test_90pct_width": float((upper - lower).mean()),
        "products": int(demand.shape[0]),
    }])
    return point, metrics


def leads_for(scenario: pd.Series, policy: str, horizon: int, products: int, rep: int) -> np.ndarray:
    if policy in {"P1_independent_deterministic", "P3_basket_deterministic"}:
        return np.ones((horizon, products), dtype=int)
    scenario_number = int(str(scenario["scenario_id"])[1:])
    rng = np.random.default_rng(SEED + scenario_number * 10000 + rep)
    return np.vstack([sample_lead_weeks(scenario, rng, products) for _ in range(horizon)])


def main() -> None:
    parser = __import__("argparse").ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    out = root / "results"
    log_path = out / "run_log.csv"
    if log_path.exists():
        log = pd.read_csv(log_path, dtype="string")
        prior = log.loc[
            (log["phase"] == "phase1_test_frozen")
            & (log["status"].isin(["primary_replay", "duplicate_invocation_ignored"]))
        ]
        if len(prior):
            raise SystemExit(
                "Refusing to rerun the Phase 1 test window: a frozen primary replay "
                "is already logged. Use the existing primary outputs and record any "
                "new analysis under a new preregistered configuration."
            )

    _weekly, weeks, demand, products, train_idx, _val_idx, test_idx = weekly_matrix(root, support_threshold=20)
    test_weeks = weeks[test_idx]
    internal = internal_calibration(demand, train_idx)
    scale = internal["scale"]
    forecast, forecast_metrics = test_forecast(demand, test_idx, scale)
    forecast_metrics.to_csv(out / "phase1_forecast_test.csv", index=False)
    test_demand = demand[:, test_idx]
    network = network_scores(root, products, min_pair_count=5, top_k=5)
    baskets = basket_map(root, products, test_weeks)
    scenarios = pd.read_csv(root / "data" / "synthetic" / "inventory_scenarios.csv")

    rows: list[dict[str, object]] = []
    matched_rows: list[dict[str, object]] = []
    for scenario_dict in scenarios.to_dict("records"):
        scenario = pd.Series(scenario_dict)
        scenario_number = int(str(scenario["scenario_id"])[1:])
        rep_count = 1 if scenario["lead_time_distribution"] == "deterministic_7d" else REPLICATIONS
        nominal = float(scenario["shortage_penalty_per_unit"]) / (float(scenario["shortage_penalty_per_unit"]) + float(scenario["holding_cost_per_unit_week"]))
        for rep in range(rep_count):
            lead_cache = {
                policy: leads_for(scenario, policy, len(test_idx), len(products), rep)
                for policy in POLICIES
            }
            result_cache: dict[tuple[str, float], dict[str, object]] = {}
            for policy in POLICIES:
                result = simulate_policy(
                    test_demand,
                    test_weeks,
                    forecast,
                    scale * SAFETY_MULTIPLIER,
                    network,
                    baskets,
                    scenario,
                    policy,
                    ALPHA,
                    lead_cache[policy],
                    service_target=nominal,
                )
                result_cache[(policy, nominal)] = result
                rows.append({
                    "scenario_id": scenario["scenario_id"],
                    "replication": rep,
                    "lead_time_distribution": scenario["lead_time_distribution"],
                    "holding_cost_per_unit_week": scenario["holding_cost_per_unit_week"],
                    "shortage_penalty_per_unit": scenario["shortage_penalty_per_unit"],
                    "service_target": nominal,
                    "basket_alpha": ALPHA,
                    "safety_multiplier": SAFETY_MULTIPLIER,
                    **result,
                })

            for basket_policy, independent_policy in [
                ("P3_basket_deterministic", "P1_independent_deterministic"),
                ("P4_basket_stochastic", "P2_independent_stochastic"),
            ]:
                basket_result = result_cache[(basket_policy, nominal)]
                candidates = []
                for target in TARGET_GRID:
                    result = simulate_policy(
                        test_demand,
                        test_weeks,
                        forecast,
                        scale * SAFETY_MULTIPLIER,
                        network,
                        baskets,
                        scenario,
                        independent_policy,
                        0.0,
                        lead_cache[independent_policy],
                        service_target=target,
                    )
                    candidates.append(result)
                independent_result = min(candidates, key=lambda r: (abs(float(r["average_inventory_units"]) - float(basket_result["average_inventory_units"])), float(r["service_target"])))
                matched_rows.append({
                    "scenario_id": scenario["scenario_id"],
                    "replication": rep,
                    "basket_policy": basket_policy,
                    "independent_policy": independent_policy,
                    "matched_independent_service_target": independent_result["service_target"],
                    "basket_average_inventory_units": basket_result["average_inventory_units"],
                    "independent_average_inventory_units": independent_result["average_inventory_units"],
                    "basket_item_fill_rate": basket_result["item_fill_rate"],
                    "independent_item_fill_rate": independent_result["item_fill_rate"],
                    "basket_complete_basket_fill_rate": basket_result["complete_basket_fill_rate"],
                    "independent_complete_basket_fill_rate": independent_result["complete_basket_fill_rate"],
                    "basket_total_cost": basket_result["total_cost"],
                    "independent_total_cost": independent_result["total_cost"],
                    "item_fill_difference": float(basket_result["item_fill_rate"]) - float(independent_result["item_fill_rate"]),
                    "complete_basket_fill_difference": float(basket_result["complete_basket_fill_rate"]) - float(independent_result["complete_basket_fill_rate"]),
                    "cost_difference": float(basket_result["total_cost"]) - float(independent_result["total_cost"]),
                    "inventory_difference": float(basket_result["average_inventory_units"]) - float(independent_result["average_inventory_units"]),
                })

    frame = pd.DataFrame(rows)
    frame.to_csv(out / "phase1_inventory_results_by_replication.csv", index=False)
    summary_cols = [
        "total_cost", "average_inventory_units", "item_fill_rate", "complete_basket_fill_rate",
        "unmet_units", "stockout_frequency", "holding_cost", "shortage_cost", "ordering_cost", "purchase_cost",
    ]
    summary = frame.groupby(["scenario_id", "policy"], as_index=False)[summary_cols].agg(["mean", lambda x: x.quantile(0.025), lambda x: x.quantile(0.975)])
    summary.columns = ["_".join(str(v) for v in col if str(v) != "") for col in summary.columns]
    summary = summary.reset_index()
    summary.to_csv(out / "phase1_inventory_summary.csv", index=False)

    matched = pd.DataFrame(matched_rows)
    matched.to_csv(out / "phase1_inventory_matched.csv", index=False)
    matched_summary = matched.groupby(["basket_policy", "independent_policy"], as_index=False)[[
        "item_fill_difference", "complete_basket_fill_difference", "cost_difference", "inventory_difference",
    ]].agg(["mean", lambda x: x.quantile(0.025), lambda x: x.quantile(0.975)])
    matched_summary.columns = ["_".join(str(v) for v in col if str(v) != "") for col in matched_summary.columns]
    matched_summary.reset_index().to_csv(out / "phase1_inventory_matched_summary.csv", index=False)

    config = {
        "phase": 1,
        "primary_estimand": "service_at_matched_inventory",
        "forecast": "empirical_quantile",
        "alpha": ALPHA,
        "safety_multiplier": SAFETY_MULTIPLIER,
        "replications_stochastic": REPLICATIONS,
        "replications_deterministic": 1,
        "seed": SEED,
        "test_window_used": True,
        "train_end": str(weeks[train_idx[-1]].date()),
        "test_start": str(test_weeks[0].date()),
        "test_end": str(test_weeks[-1].date()),
        "outputs": [
            "phase1_forecast_test.csv", "phase1_inventory_results_by_replication.csv",
            "phase1_inventory_summary.csv", "phase1_inventory_matched.csv",
            "phase1_inventory_matched_summary.csv",
        ],
    }
    config["config_hash"] = hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()
    (out / "phase1_test_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    log = pd.DataFrame([{
        "config_hash": config["config_hash"],
        "date": pd.Timestamp.now(tz="Asia/Dhaka").isoformat(),
        "seed": SEED,
        "phase": "phase1_test_frozen",
        "split": "train_validation_test",
        "scenario": "all_scenarios",
        "policy": "P1-P4_and_matched_controls",
        "replication": f"1 deterministic / {REPLICATIONS} stochastic",
        "test_window_used": True,
        "status": "primary_replay",
        "outputs": ";".join(config["outputs"]),
    }])
    log.to_csv(out / "run_log.csv", mode="a", header=False, index=False)

    primary = matched.loc[matched["basket_policy"] == "P4_basket_stochastic"]
    report = "\n".join([
        "# Phase 1 frozen test report",
        "",
        "The validation-selected empirical-quantile forecast and safety multiplier 6.0 were frozen before this test-window replay. No test result was used to tune the configuration.",
        "",
        f"The test forecast row is in `phase1_forecast_test.csv`. The four-policy level results are in `phase1_inventory_summary.csv`; replication rows are in `phase1_inventory_results_by_replication.csv`.",
        "",
        f"For the primary P4-versus-P2 matched-inventory comparison, the mean item-fill difference was {primary['item_fill_difference'].mean():.6f} with a percentile interval [{primary['item_fill_difference'].quantile(0.025):.6f}, {primary['item_fill_difference'].quantile(0.975):.6f}], and the mean complete-basket-fill difference was {primary['complete_basket_fill_difference'].mean():.6f} with interval [{primary['complete_basket_fill_difference'].quantile(0.025):.6f}, {primary['complete_basket_fill_difference'].quantile(0.975):.6f}].",
        "",
        "These are Phase 1 results under 30 stochastic replications and one deterministic path per deterministic scenario. They are not the final uncertainty analysis specified for Phase 3.",
        "",
        "Files: `phase1_test_config.json`, `phase1_forecast_test.csv`, `phase1_inventory_summary.csv`, `phase1_inventory_results_by_replication.csv`, `phase1_inventory_matched.csv`, `phase1_inventory_matched_summary.csv`, and `run_log.csv`.",
    ])
    (out / "phase_1_test_report.md").write_text(report + "\n", encoding="utf-8")
    print(json.dumps({"config_hash": config["config_hash"], "rows": len(frame), "matched_rows": len(matched), "primary_item_fill_difference_mean": float(primary["item_fill_difference"].mean())}, indent=2))


if __name__ == "__main__":
    main()
