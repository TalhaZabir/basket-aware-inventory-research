"""Test whether PA1 helps in low-popularity, high-lift pair regimes."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from phase2_policy_components import DEFAULT_MIN_PAIR_COUNT, DEFAULT_TOP_K, buffers_from_graphs, default_edges, rewired_edges, shuffled_basket_edges, stale_edges
from run_experiment import basket_map, network_scores, simulate_policy, weekly_matrix
from run_phase1_calibration import internal_calibration, SEED
from run_phase2_test import build_test_empirical_forecast
from run_phase2_validation import SAFETY_MULTIPLIER, lead_matrix

ROOT = HERE.parent
REPS = 120
SCENARIO_ID = "S05"
ALPHA = 1.5

def ci(values):
    x = np.asarray(values, float); m = float(x.mean()); se = float(x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else 0.0
    return m, m - 1.96 * se, m + 1.96 * se

def main():
    _, weeks, demand, products, train_idx, _, test_idx = weekly_matrix(ROOT, support_threshold=20)
    forecast = build_test_empirical_forecast(demand, test_idx)
    residual = internal_calibration(demand, train_idx)["scale"]
    test_demand, test_weeks = demand[:, test_idx], weeks[test_idx]
    baskets = basket_map(ROOT, products, test_weeks)
    network = network_scores(ROOT, products, min_pair_count=DEFAULT_MIN_PAIR_COUNT, top_k=DEFAULT_TOP_K)
    graphs = {"default": default_edges(ROOT, products), "stale": stale_edges(ROOT, products), "shuffled": shuffled_basket_edges(ROOT, products, seed=SEED), "rewired": rewired_edges(default_edges(ROOT, products), seed=SEED)}
    buffers, _ = buffers_from_graphs(ROOT, products, residual, SAFETY_MULTIPLIER, graphs["default"], graphs["stale"], graphs["shuffled"], graphs["rewired"], tau=0.50)
    edge = pd.read_csv(ROOT / "data" / "processed" / "uci_copurchase_edges_train_only.csv")
    volume = demand[:, train_idx].sum(axis=1); rank = pd.Series(volume, index=products.astype(str))
    q25, q75 = rank.quantile(.25), rank.quantile(.75)
    lift_cut = edge["lift"].quantile(.90)
    support_cut = edge["co_purchase_count"].quantile(.75)
    idx = {str(p): i for i, p in enumerate(products)}
    low_set, high_set = set(), set()
    for row in edge.loc[(edge.lift >= lift_cut) & (edge.co_purchase_count >= support_cut)].itertuples():
        a, b = str(row.stock_code_a), str(row.stock_code_b)
        if a in rank.index and b in rank.index and rank[a] <= q25 and rank[b] <= q25: low_set.update([a,b])
        if a in rank.index and b in rank.index and rank[a] >= q75 and rank[b] >= q75: high_set.update([a,b])
    masks = {"low_pop_high_lift": np.array([str(p) in low_set for p in products]), "high_pop_high_lift": np.array([str(p) in high_set for p in products])}
    scenario = pd.read_csv(ROOT / "data" / "synthetic" / "inventory_scenarios.csv").loc[lambda x: x.scenario_id == SCENARIO_ID].iloc[0]
    rows = []
    for rep in range(REPS):
        lead = lead_matrix(scenario, "P2_independent_stochastic", len(test_idx), len(products), rep)
        for regime, mask in masks.items():
            if mask.sum() == 0: continue
            out = {}
            for policy, buffer in [("PA1_stochastic", buffers["PA1"]), ("C4_stochastic", buffers["C4"])]:
                out[policy] = simulate_policy(test_demand, test_weeks, forecast, residual * SAFETY_MULTIPLIER, network, baskets, scenario, policy, ALPHA, lead, service_target=float(scenario.shortage_penalty_per_unit)/(float(scenario.shortage_penalty_per_unit)+float(scenario.holding_cost_per_unit_week)), basket_buffer=buffer, metric_product_mask=mask)
            metric_pairs = [("total_cost", "total_cost"), ("average_inventory_units", "average_inventory_units"), ("item_fill_rate", "metric_item_fill_rate"), ("unmet_units", "metric_unmet_units")]
            for label, key in metric_pairs:
                rows.append({"regime": regime, "replication": rep, "products_in_regime": int(mask.sum()), "metric": label, "difference_PA1_minus_C4": float(out["PA1_stochastic"][key]) - float(out["C4_stochastic"][key]), "pa1": float(out["PA1_stochastic"][key]), "c4": float(out["C4_stochastic"][key])})
    frame = pd.DataFrame(rows); frame.to_csv(ROOT / "results" / "gate2_pair_regime_replications.csv", index=False)
    summary=[]
    for (regime, metric), g in frame.groupby(["regime","metric"]):
        m, lo, hi = ci(g.difference_PA1_minus_C4); summary.append({"regime":regime,"metric":metric,"products_in_regime":int(g.products_in_regime.iloc[0]),"replications":len(g),"mean_difference":m,"ci95_low":lo,"ci95_high":hi,"lift_threshold":float(lift_cut),"pair_count_threshold":float(support_cut),"popularity_q25":float(q25),"popularity_q75":float(q75)})
    pd.DataFrame(summary).to_csv(ROOT / "results" / "gate2_pair_regime_summary.csv", index=False)
    pd.DataFrame([{"edge_count":len(edge),"lift_cut_p90":lift_cut,"pair_count_cut_p75":support_cut,"low_pop_products":len(low_set),"high_pop_products":len(high_set),"note":"All thresholds and masks use training-period edge and volume features only."}]).to_csv(ROOT / "results" / "gate2_pair_regime_definition.csv", index=False)
    print(pd.DataFrame(summary).to_string(index=False))

if __name__ == "__main__": main()
