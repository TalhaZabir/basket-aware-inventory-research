"""Rolling-origin robustness check for the UCI primary replay.

The first window is historical and exploratory; the frozen primary window is
W3. Each window re-selects the product universe, forecast, and basket graph
using data available before that window's test period.
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path
import sys

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from phase2_policy_components import _basket_edges, edge_buffer, scale_to_total  # noqa: E402
from run_experiment import build_forecasts, basket_map, simulate_policy  # noqa: E402
from run_phase2_validation import SAFETY_MULTIPLIER, lead_matrix  # noqa: E402

ROOT = SCRIPT_DIR.parent
SCENARIO_ID = "S05"
ALPHA = 1.5


def build_window(name, train_end, val_start, val_end, test_start, test_end):
    weekly = pd.read_csv(ROOT / "data" / "processed" / "uci_weekly_product_demand.csv", dtype={"stock_code": "string"})
    weekly["week_start"] = pd.to_datetime(weekly["week_start"])
    weeks = pd.Index(sorted(weekly["week_start"].unique()))
    support = weekly.loc[weekly["week_start"] <= pd.Timestamp(train_end)].groupby("stock_code")["units_sold"].apply(lambda x: int((x > 0).sum()))
    products = pd.Index(sorted(support.loc[support >= 20].index.astype(str)))
    matrix = weekly.pivot_table(index="stock_code", columns="week_start", values="units_sold", aggfunc="sum").reindex(index=products, columns=weeks).fillna(0.0).astype(float)
    train_idx = np.flatnonzero(weeks <= pd.Timestamp(train_end))
    val_idx = np.flatnonzero((weeks >= pd.Timestamp(val_start)) & (weeks <= pd.Timestamp(val_end)))
    test_idx = np.flatnonzero((weeks >= pd.Timestamp(test_start)) & (weeks <= pd.Timestamp(test_end)))
    forecast, residual, selected, forecast_metrics = build_forecasts(matrix.to_numpy(), train_idx, val_idx, test_idx)
    lines = pd.read_csv(ROOT / "data" / "processed" / "uci_transaction_lines_clean.csv", dtype={"invoice_id": "string", "stock_code": "string"})
    lines["invoice_date"] = pd.to_datetime(lines["invoice_date"])
    training_lines = lines.loc[lines["invoice_date"] <= pd.Timestamp(train_end)].copy()
    default = _basket_edges(training_lines, products.to_numpy(), min_pair_count=5)
    risk = 1.645 * np.maximum(residual, 0.25)
    graph = edge_buffer(default, len(products), risk, top_k=5)
    train_volume = training_lines.loc[training_lines["stock_code"].isin(set(products))].groupby("stock_code")["quantity"].sum().reindex(products, fill_value=0.0).to_numpy(float)
    popularity = scale_to_total(train_volume, float(graph.sum()))
    graph = scale_to_total(graph, float(graph.sum()))
    selected_weeks = weeks[test_idx]
    baskets = basket_map(ROOT, products.to_numpy(), selected_weeks)
    scenarios = pd.read_csv(ROOT / "data" / "synthetic" / "inventory_scenarios.csv")
    scenario = scenarios.loc[scenarios["scenario_id"] == SCENARIO_ID].iloc[0]
    test_demand, test_weeks = matrix.to_numpy()[:, test_idx], weeks[test_idx]
    lead = lead_matrix(scenario, "P1_independent_deterministic", len(test_idx), len(products), 0)
    rows = []
    for policy, buffer in [("PA1_deterministic", graph), ("C4_deterministic", popularity)]:
        result = simulate_policy(test_demand, test_weeks, forecast, residual * SAFETY_MULTIPLIER, np.zeros(len(products)), baskets, scenario, policy, ALPHA, lead, service_target=0.90, basket_buffer=buffer)
        rows.append({"window": name, "train_end": train_end, "test_start": test_start, "test_end": test_end, "products": len(products), "test_weeks": len(test_idx), "graph_edges": len(default), "policy": policy, **{k: float(result[k]) for k in ["total_cost", "average_inventory_units", "item_fill_rate", "complete_basket_fill_rate", "unmet_units", "stockout_frequency"]}, "validation_wape_selected": float(forecast_metrics.loc[forecast_metrics["model"] == "selected_per_product", "validation_wape"].iloc[0])})
    return rows


def main():
    windows = [
        ("W1", "2010-12-27", "2011-01-03", "2011-02-28", "2011-03-07", "2011-05-30"),
        ("W2", "2011-03-28", "2011-04-04", "2011-05-30", "2011-06-06", "2011-08-29"),
        ("W3_primary", "2011-06-27", "2011-07-04", "2011-08-29", "2011-09-05", "2011-12-05"),
    ]
    rows = []
    for window in windows:
        rows.extend(build_window(*window))
    result = pd.DataFrame(rows)
    result.to_csv(ROOT / "results" / "phase3_rolling_window_results.csv", index=False)
    (ROOT / "results" / "phase3_rolling_window_report.md").write_text("# Three rolling-origin windows\n\n" + result.to_string(index=False) + "\n\nW3 is the primary frozen window; W1 and W2 are robustness windows. All graph and popularity buffers are rebuilt from each window's training period.\n", encoding="utf-8")
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
