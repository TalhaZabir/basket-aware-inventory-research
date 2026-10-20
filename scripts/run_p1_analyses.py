"""Run P1 reporting and robustness analyses.

This script adds test-week bootstrap intervals, an earlier rolling-origin replay,
and a machine-readable report for the expanded alpha grid and missing contrasts.
"""

from __future__ import annotations

import itertools
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_experiment import (  # noqa: E402
    ALPHA_CANDIDATES,
    POLICIES,
    basket_map,
    build_forecasts,
    sample_lead_weeks,
    simulate_policy,
    weekly_matrix,
)


def scenario_target(scenario: pd.Series) -> float:
    p = float(scenario["shortage_penalty_per_unit"])
    h = float(scenario["holding_cost_per_unit_week"])
    return p / (p + h)


def load_base(root: Path):
    _, weeks, demand_all, products, train_idx, val_idx, test_idx = weekly_matrix(root, support_threshold=20)
    test_weeks = weeks[test_idx]
    test_demand = demand_all[:, test_idx]
    test_forecast, residual_std, selected_names, _ = build_forecasts(demand_all, train_idx, val_idx, test_idx)
    from run_experiment import network_scores
    network = network_scores(root, products, min_pair_count=5, top_k=5)
    baskets = basket_map(root, products, test_weeks)
    return weeks, demand_all, products, test_weeks, test_demand, test_forecast, residual_std, network, baskets


def lead_draws(scenario: pd.Series, rng: np.random.Generator, horizon: int, n_products: int) -> np.ndarray:
    return np.vstack([sample_lead_weeks(scenario, rng, n_products) for _ in range(horizon)])


def bootstrap_test_weeks(root: Path, out: Path, base, scenarios: pd.DataFrame, selected_alpha: float, bootstrap_reps: int = 100) -> pd.DataFrame:
    _, _, products, test_weeks, test_demand, test_forecast, residual_std, network, baskets = base
    rows = []
    contrasts = [
        ("P2_independent_stochastic", "P1_independent_deterministic", "P2_minus_P1"),
        ("P3_basket_deterministic", "P1_independent_deterministic", "P3_minus_P1"),
        ("P4_basket_stochastic", "P2_independent_stochastic", "P4_minus_P2"),
        ("P4_basket_stochastic", "P3_basket_deterministic", "P4_minus_P3"),
    ]
    horizon = len(test_weeks)
    for _, scenario in scenarios.iterrows():
        for b in range(bootstrap_reps):
            rng = np.random.default_rng(int(scenario["random_seed"]) + 500000 + b)
            sample_idx = rng.integers(0, horizon, size=horizon)
            sampled_weeks = pd.Index([test_weeks[i] for i in sample_idx])
            sampled_demand = test_demand[:, sample_idx]
            sampled_forecast = test_forecast[:, sample_idx]
            sampled_baskets = {pd.Timestamp(week).strftime("%Y-%m-%d"): baskets.get(pd.Timestamp(week).strftime("%Y-%m-%d"), []) for week in sampled_weeks}
            sampled_leads = lead_draws(scenario, rng, horizon, len(products))
            results = {}
            target = scenario_target(scenario)
            for policy in POLICIES:
                results[policy] = simulate_policy(sampled_demand, sampled_weeks, sampled_forecast, residual_std, network, sampled_baskets, scenario, policy, selected_alpha, sampled_leads, service_target=target)
            for basket_policy, base_policy, label in contrasts:
                b_result = results[basket_policy]
                i_result = results[base_policy]
                row = {"analysis": "test_week_bootstrap", "scenario_id": scenario["scenario_id"], "bootstrap_replication": b, "contrast": label, "sampled_test_weeks": "|".join(pd.Timestamp(x).strftime("%Y-%m-%d") for x in sampled_weeks)}
                for metric in ["total_cost", "average_inventory_units", "item_fill_rate", "complete_basket_fill_rate", "unmet_units", "stockout_frequency"]:
                    row[f"{metric}_difference"] = float(b_result[metric] - i_result[metric])
                rows.append(row)
    frame = pd.DataFrame(rows)
    frame.to_csv(out / "bootstrap_test_week_results.csv", index=False)
    summary_rows = []
    for keys, group in frame.groupby(["scenario_id", "contrast"], sort=False):
        scenario_id, contrast = keys
        row = {"scenario_id": scenario_id, "contrast": contrast, "bootstrap_replications": len(group)}
        for column in [c for c in frame.columns if c.endswith("_difference")]:
            values = group[column].to_numpy(float)
            row[f"{column}_mean"] = float(values.mean())
            row[f"{column}_p025"] = float(np.quantile(values, 0.025))
            row[f"{column}_p975"] = float(np.quantile(values, 0.975))
        summary_rows.append(row)
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(out / "bootstrap_test_week_summary.csv", index=False)
    pooled_rows = []
    for contrast, group in frame.groupby("contrast", sort=False):
        row = {"contrast": contrast, "bootstrap_draws": int(len(group)), "scenarios": int(group["scenario_id"].nunique()), "bootstrap_replications_per_scenario": int(bootstrap_reps)}
        for column in [c for c in frame.columns if c.endswith("_difference")]:
            values = group[column].to_numpy(float)
            row[f"{column}_mean"] = float(values.mean())
            row[f"{column}_p025"] = float(np.quantile(values, 0.025))
            row[f"{column}_p975"] = float(np.quantile(values, 0.975))
        pooled_rows.append(row)
    pd.DataFrame(pooled_rows).to_csv(out / "bootstrap_test_week_pooled_summary.csv", index=False)
    return summary


def network_scores_from_lines(root: Path, products: np.ndarray, cutoff: pd.Timestamp, min_pair_count: int = 5, top_k: int = 5) -> np.ndarray:
    lines = pd.read_csv(root / "data" / "processed" / "uci_transaction_lines_clean.csv", dtype={"invoice_id": "string", "stock_code": "string"}, usecols=["invoice_id", "invoice_date", "stock_code"])
    lines["invoice_date"] = pd.to_datetime(lines["invoice_date"])
    lines = lines.loc[lines["invoice_date"] <= cutoff]
    product_index = {str(product): i for i, product in enumerate(products)}
    product_baskets = Counter()
    pair_counts = Counter()
    for _, group in lines.groupby("invoice_id")["stock_code"]:
        values = sorted(set(str(value) for value in group if str(value) in product_index))
        for value in values:
            product_baskets[value] += 1
        for a, b in itertools.combinations(values, 2):
            pair_counts[(a, b)] += 1
    directed = {}
    for (a, b), count in pair_counts.items():
        if count < min_pair_count:
            continue
        directed.setdefault(product_index[a], []).append(count / max(product_baskets[a], 1))
        directed.setdefault(product_index[b], []).append(count / max(product_baskets[b], 1))
    scores = np.zeros(len(products), dtype=float)
    for index, values in directed.items():
        scores[index] = min(float(np.mean(sorted(values, reverse=True)[:top_k])), 1.0)
    return scores


def load_rolling_origin_base(root: Path):
    weekly = pd.read_csv(root / "data" / "processed" / "uci_weekly_product_demand.csv", dtype={"stock_code": "string"})
    weekly["week_start"] = pd.to_datetime(weekly["week_start"])
    weeks = pd.Index(sorted(weekly["week_start"].unique()))
    train_end = pd.Timestamp("2010-12-27")
    val_start = pd.Timestamp("2011-01-03")
    val_end = pd.Timestamp("2011-02-28")
    test_start = pd.Timestamp("2011-03-07")
    test_end = pd.Timestamp("2011-06-06")
    support = weekly.loc[weekly["week_start"] <= train_end].groupby("stock_code")["units_sold"].apply(lambda x: int((x > 0).sum()))
    products = np.array(sorted(support.loc[support >= 20].index.astype(str)))
    matrix = weekly.pivot_table(index="stock_code", columns="week_start", values="units_sold", aggfunc="sum").reindex(index=products, columns=weeks).fillna(0.0).astype(float).to_numpy()
    train_idx = np.flatnonzero(weeks <= train_end)
    val_idx = np.flatnonzero((weeks >= val_start) & (weeks <= val_end))
    test_idx = np.flatnonzero((weeks >= test_start) & (weeks <= test_end))
    test_forecast, residual_std, selected_names, _ = build_forecasts(matrix, train_idx, val_idx, test_idx)
    test_weeks = weeks[test_idx]
    baskets = basket_map(root, products, test_weeks)
    network = network_scores_from_lines(root, products, train_end)
    return weeks, matrix, products, test_weeks, matrix[:, test_idx], test_forecast, residual_std, network, baskets


def rolling_origin(root: Path, out: Path, scenarios: pd.DataFrame, selected_alpha: float) -> pd.DataFrame:
    base = load_rolling_origin_base(root)
    _, _, products, test_weeks, test_demand, test_forecast, residual_std, network, baskets = base
    chosen = scenarios.loc[scenarios["scenario_id"].isin(["S02", "S05", "S08"])]
    rows = []
    for _, scenario in chosen.iterrows():
        reps = 1 if scenario["lead_time_distribution"] == "deterministic_7d" else 10
        for rep in range(reps):
            rng = np.random.default_rng(int(scenario["random_seed"]) + 800000 + rep)
            leads = lead_draws(scenario, rng, len(test_weeks), len(products))
            for policy in POLICIES:
                result = simulate_policy(test_demand, test_weeks, test_forecast, residual_std, network, baskets, scenario, policy, selected_alpha, leads, service_target=scenario_target(scenario))
                rows.append({"analysis": "rolling_origin", "window": "train_to_2010-12-27_test_2011-03-07_to_2011-06-06", "scenario_id": scenario["scenario_id"], "replication": rep, **result})
    frame = pd.DataFrame(rows)
    frame.to_csv(out / "rolling_origin_results.csv", index=False)
    frame.groupby(["window", "scenario_id", "policy"], as_index=False)[["total_cost", "average_inventory_units", "item_fill_rate", "complete_basket_fill_rate", "unmet_units"]].mean().to_csv(out / "rolling_origin_summary.csv", index=False)
    return frame


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else SCRIPT_DIR.parent
    out = root / "results"
    out.mkdir(parents=True, exist_ok=True)
    base = load_base(root)
    scenarios = pd.read_csv(root / "data" / "synthetic" / "inventory_scenarios.csv")
    config = json.loads((out / "experiment_config.json").read_text(encoding="utf-8"))
    selected_alpha = float(config["selected_basket_alpha"])
    bootstrap_summary = bootstrap_test_weeks(root, out, base, scenarios, selected_alpha, bootstrap_reps=100)
    rolling = rolling_origin(root, out, scenarios, selected_alpha)
    alpha = pd.read_csv(out / "basket_alpha_validation_calibration.csv")
    report = {
        "alpha_candidates": ALPHA_CANDIDATES,
        "selected_alpha": selected_alpha,
        "selected_alpha_is_grid_boundary": bool(selected_alpha == max(ALPHA_CANDIDATES)),
        "bootstrap_replications_per_scenario": 100,
        "bootstrap_summary_rows": len(bootstrap_summary),
        "rolling_origin_rows": len(rolling),
        "rolling_origin_window": "training through 2010-12-27, validation 2011-01-03 through 2011-02-28, test 2011-03-07 through 2011-06-06",
    }
    (out / "p1_analysis_config.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    alpha.to_csv(out / "alpha_extended_validation_calibration.csv", index=False)
    (out / "p1_analysis_report.md").write_text(
        "# P1 robustness analysis report\n\n"
        f"The alpha grid was extended to {ALPHA_CANDIDATES}; matched-inventory calibration selected alpha = {selected_alpha}, which is interior to the grid. The selection minimizes matched cost subject to at least a one-percentage-point complete-basket-fill improvement over alpha zero. The full calibration table is `alpha_extended_validation_calibration.csv`.\n\n"
        "Bootstrap intervals resample the 14 observed test weeks with replacement and rerun the paired policy comparison under common lead-time draws: 100 resamples per scenario and 1,200 pooled draws per contrast. The pooled file reports descriptive quantiles over all draws; it does not average scenario-level interval endpoints, and the pooled quantiles should not be interpreted as a formal confidence interval for a single overall mean because scenarios are clustered and have different cost scales. These intervals represent sampling uncertainty over the realized test-week composition; they do not turn synthetic inventory outcomes into observed inventory truth. Results are in `bootstrap_test_week_results.csv`, `bootstrap_test_week_summary.csv`, and `bootstrap_test_week_pooled_summary.csv`.\n\n"
        "The rolling-origin check re-estimates the product universe, forecasts, and co-purchase scores using data through 2010-12-27, validates through 2011-02-28, and evaluates an earlier 2011-03-07 to 2011-06-06 test window. Results are in `rolling_origin_results.csv` and `rolling_origin_summary.csv`.\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
