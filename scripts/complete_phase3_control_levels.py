"""Fill control shortage/stockout level metrics without rerunning PA policies."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from phase2_policy_components import DEFAULT_MIN_PAIR_COUNT, DEFAULT_TOP_K, buffers_from_graphs, default_edges, rewired_edges, shuffled_basket_edges, stale_edges  # noqa: E402
from run_experiment import basket_map, network_scores, simulate_policy, weekly_matrix  # noqa: E402
from run_phase1_calibration import SEED, internal_calibration  # noqa: E402
from run_phase2_test import build_test_empirical_forecast  # noqa: E402
from run_phase2_validation import SAFETY_MULTIPLIER, lead_matrix  # noqa: E402

ROOT = SCRIPT_DIR.parent
ALPHA, TAU = 1.5, .5

def main():
    out = ROOT / "results"
    d = pd.read_csv(out / "phase3_test_results.csv")
    _weekly, weeks, demand, products, _train, _val, test_idx = weekly_matrix(ROOT, support_threshold=20)
    residual = internal_calibration(demand, _train)["scale"]
    forecast = build_test_empirical_forecast(demand, test_idx)
    test_demand, test_weeks = demand[:, test_idx], weeks[test_idx]
    network = network_scores(ROOT, products, min_pair_count=DEFAULT_MIN_PAIR_COUNT, top_k=DEFAULT_TOP_K)
    baskets = basket_map(ROOT, products, test_weeks)
    graphs = {"default": default_edges(ROOT, products), "stale": stale_edges(ROOT, products), "shuffled": shuffled_basket_edges(ROOT, products, seed=SEED), "rewired": rewired_edges(default_edges(ROOT, products), seed=SEED)}
    buffers, _ = buffers_from_graphs(ROOT, products, residual, SAFETY_MULTIPLIER, graphs["default"], graphs["stale"], graphs["shuffled"], graphs["rewired"], tau=TAU)
    scenarios = pd.read_csv(ROOT / "data" / "synthetic" / "inventory_scenarios.csv")
    scenario = scenarios.loc[scenarios["scenario_id"] == "S05"].iloc[0]
    updates = []
    for row in d.loc[d["variant"].isin(["PA1", "C4"])].itertuples(index=False):
        lead = lead_matrix(scenario, "P2_independent_stochastic", len(test_idx), len(products), int(row.replication))
        target = float(row.matched_service_target)
        result = simulate_policy(test_demand, test_weeks, forecast, residual * SAFETY_MULTIPLIER, network, baskets, scenario, "P2_independent_stochastic", 0.0, lead, service_target=target, basket_buffer=None)
        updates.append({"scenario_id": row.scenario_id, "replication": row.replication, "variant": row.variant, "control_unmet_units": float(result["unmet_units"]), "control_stockout_frequency": float(result["stockout_frequency"])})
    u = pd.DataFrame(updates)
    d = d.merge(u, on=["scenario_id", "replication", "variant"], how="left")
    d.to_csv(out / "phase3_test_results.csv", index=False)
    print("updated", len(u), "control level rows")

if __name__ == "__main__":
    main()
