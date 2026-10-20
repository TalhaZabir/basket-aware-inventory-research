"""Run the requested P0 robustness, frontier, placebo, and stratification analyses."""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_experiment import (  # noqa: E402
    POLICIES,
    basket_map,
    build_forecasts,
    network_scores,
    sample_lead_weeks,
    simulate_policy,
    weekly_matrix,
)


def cost_target(scenario: pd.Series) -> float:
    p = float(scenario["shortage_penalty_per_unit"])
    h = float(scenario["holding_cost_per_unit_week"])
    return p / (p + h)


def load_base(root: Path, support_threshold: int = 20, min_pair_count: int = 5, top_k: int = 5):
    _, weeks, demand_all, products, train_idx, val_idx, test_idx = weekly_matrix(root, support_threshold=support_threshold)
    test_weeks = weeks[test_idx]
    test_demand = demand_all[:, test_idx]
    test_forecast, residual_std, selected_names, _ = build_forecasts(demand_all, train_idx, val_idx, test_idx)
    network = network_scores(root, products, min_pair_count=min_pair_count, top_k=top_k)
    baskets = basket_map(root, products, test_weeks)
    return weeks, demand_all, products, test_weeks, test_demand, test_forecast, residual_std, network, baskets


def lead_draws_for(scenario: pd.Series, n_products: int, horizon: int, rep: int) -> np.ndarray:
    rng = np.random.default_rng(int(scenario["random_seed"]) + int(rep))
    return np.vstack([sample_lead_weeks(scenario, rng, n_products) for _ in range(horizon)])


def run_one(base, scenario: pd.Series, policy: str, alpha: float, rep: int, service: float | None = None, network=None, backorder_mode: str = "lost_sales", basket_definition: str = "all_units", metric_mask=None):
    weeks, _, products, test_weeks, test_demand, test_forecast, residual_std, base_network, baskets = base
    leads = lead_draws_for(scenario, len(products), len(test_weeks), rep)
    return simulate_policy(
        test_demand,
        test_weeks,
        test_forecast,
        residual_std,
        base_network if network is None else network,
        baskets,
        scenario,
        policy,
        alpha,
        leads,
        service_target=cost_target(scenario) if service is None else service,
        backorder_mode=backorder_mode,
        basket_definition=basket_definition,
        metric_product_mask=metric_mask,
    )


def scenario_frame(root: Path) -> pd.DataFrame:
    return pd.read_csv(root / "data" / "synthetic" / "inventory_scenarios.csv")


def run_frontier(root: Path, out: Path, base, scenarios: pd.DataFrame, selected_alpha: float) -> pd.DataFrame:
    targets = [0.80, 0.85, 0.90, 0.95, 0.975, 0.99]
    alphas = [0.0, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0]
    chosen = scenarios.loc[scenarios["scenario_id"].isin(["S02", "S05", "S08", "S11"])]
    rows = []
    for _, scenario in chosen.iterrows():
        reps = 1 if scenario["lead_time_distribution"] == "deterministic_7d" else 3
        for rep in range(reps):
            for target in targets:
                for policy in ["P1_independent_deterministic", "P2_independent_stochastic", "P3_basket_deterministic", "P4_basket_stochastic"]:
                    if policy in {"P1_independent_deterministic", "P2_independent_stochastic"}:
                        policy_alphas = [0.0]
                    else:
                        policy_alphas = alphas
                    for alpha in policy_alphas:
                        result = run_one(base, scenario, policy, alpha, rep, service=target)
                        rows.append({"analysis": "service_inventory_frontier", "scenario_id": scenario["scenario_id"], "replication": rep, "service_target": target, "alpha": alpha, **result})
    frame = pd.DataFrame(rows)
    frame.to_csv(out / "frontier_results.csv", index=False)
    write_frontier_svg(frame, out / "frontier_plot.svg")
    try:
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(2, 2, figsize=(12, 9), sharex=False, sharey=True)
        for ax, scenario_id in zip(axes.flat, ["S02", "S05", "S08", "S11"]):
            subset = frame.loc[frame["scenario_id"] == scenario_id]
            for policy, marker in [("P1_independent_deterministic", "o"), ("P2_independent_stochastic", "s"), ("P3_basket_deterministic", "^"), ("P4_basket_stochastic", "D")]:
                for alpha in sorted(subset.loc[subset["policy"] == policy, "alpha"].unique()):
                    data = subset.loc[(subset["policy"] == policy) & (subset["alpha"] == alpha)].groupby("service_target", as_index=False)[["average_inventory_units", "complete_basket_fill_rate"]].mean().sort_values("service_target")
                    label = f"{policy[:2]}, a={alpha:g}" if policy.startswith("P3") or policy.startswith("P4") else policy[:2]
                    ax.plot(data["average_inventory_units"], data["complete_basket_fill_rate"], marker=marker, linewidth=1, markersize=4, label=label)
            ax.set_title(f"{scenario_id} frontier")
            ax.set_xlabel("Average inventory units")
            ax.set_ylabel("Complete-basket fill rate")
            ax.grid(alpha=0.25)
        handles, labels = axes.flat[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8)
        fig.tight_layout(rect=(0, 0.08, 1, 1))
        fig.savefig(out / "frontier_plot.png", dpi=180)
        plt.close(fig)
    except Exception as exc:
        (out / "frontier_plot_unavailable.txt").write_text(f"Plot generation unavailable: {exc}\n", encoding="utf-8")
    return frame


def write_frontier_svg(frame: pd.DataFrame, path: Path) -> None:
    """Write a dependency-free two-by-two frontier plot as SVG."""
    width, height = 1200, 900
    margin_x, margin_y = 70, 60
    panel_w, panel_h = 500, 330
    x_min = float(frame["average_inventory_units"].min())
    x_max = float(frame["average_inventory_units"].max())
    y_min = float(frame["complete_basket_fill_rate"].min())
    y_max = float(frame["complete_basket_fill_rate"].max())
    x_pad = max((x_max - x_min) * 0.05, 1.0)
    y_pad = max((y_max - y_min) * 0.05, 0.01)
    x_min, x_max = x_min - x_pad, x_max + x_pad
    y_min, y_max = max(0.0, y_min - y_pad), min(1.0, y_max + y_pad)
    colors = {"P1_independent_deterministic": "#4C78A8", "P2_independent_stochastic": "#72B7B2", "P3_basket_deterministic": "#F58518", "P4_basket_stochastic": "#E45756"}
    labels = {"P1_independent_deterministic": "P1 independent deterministic", "P2_independent_stochastic": "P2 independent stochastic", "P3_basket_deterministic": "P3 basket deterministic", "P4_basket_stochastic": "P4 basket stochastic"}
    def sx(value, left):
        return left + (float(value) - x_min) / (x_max - x_min) * panel_w
    def sy(value, top):
        return top + panel_h - (float(value) - y_min) / (y_max - y_min) * panel_h
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>', '<style>text{font-family:Arial,sans-serif;fill:#222} .axis{stroke:#555;stroke-width:1} .grid{stroke:#ddd;stroke-width:1}</style>', '<text x="600" y="28" text-anchor="middle" font-size="20" font-weight="bold">Service versus average inventory frontier</text>']
    scenarios = ["S02", "S05", "S08", "S11"]
    for panel, scenario_id in enumerate(scenarios):
        left = margin_x + (panel % 2) * 560
        top = margin_y + (panel // 2) * 390
        parts.append(f'<text x="{left + panel_w / 2:.1f}" y="{top - 16}" text-anchor="middle" font-size="16" font-weight="bold">{scenario_id}</text>')
        parts.append(f'<line class="axis" x1="{left}" y1="{top + panel_h}" x2="{left + panel_w}" y2="{top + panel_h}"/><line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{top + panel_h}"/>')
        for tick in np.linspace(0, 1, 5):
            y = sy(y_min + tick * (y_max - y_min), top)
            parts.append(f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{left + panel_w}" y2="{y:.1f}"/>')
        subset = frame.loc[frame["scenario_id"] == scenario_id]
        for (policy, alpha), data in subset.groupby(["policy", "alpha"], sort=False):
            data = data.groupby("service_target", as_index=False)[["average_inventory_units", "complete_basket_fill_rate"]].mean().sort_values("service_target")
            points = " ".join(f"{sx(row.average_inventory_units, left):.1f},{sy(row.complete_basket_fill_rate, top):.1f}" for row in data.itertuples(index=False))
            opacity = "0.9" if policy.startswith("P3") or policy.startswith("P4") else "0.65"
            parts.append(f'<polyline points="{points}" fill="none" stroke="{colors[policy]}" stroke-width="2" opacity="{opacity}"/>')
            for row in data.itertuples(index=False):
                parts.append(f'<circle cx="{sx(row.average_inventory_units, left):.1f}" cy="{sy(row.complete_basket_fill_rate, top):.1f}" r="3" fill="{colors[policy]}"/>')
        parts.append(f'<text x="{left + panel_w / 2:.1f}" y="{top + panel_h + 35}" text-anchor="middle" font-size="11">Average inventory units</text>')
        parts.append(f'<text x="{left - 42}" y="{top + panel_h / 2:.1f}" text-anchor="middle" font-size="11" transform="rotate(-90 {left - 42} {top + panel_h / 2:.1f})">Complete-basket fill</text>')
    legend_x, legend_y = 70, 875
    for i, policy in enumerate(colors):
        x = legend_x + i * 270
        parts.append(f'<line x1="{x}" y1="{legend_y - 4}" x2="{x + 22}" y2="{legend_y - 4}" stroke="{colors[policy]}" stroke-width="3"/><text x="{x + 28}" y="{legend_y}" font-size="11">{labels[policy]}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def run_placebo(root: Path, out: Path, base, scenarios: pd.DataFrame, selected_alpha: float) -> pd.DataFrame:
    _, _, products, _, _, _, _, network, _ = base
    placebo_network = network[np.random.default_rng(20261020).permutation(len(network))]
    rows = []
    for _, scenario in scenarios.iterrows():
        reps = 1 if scenario["lead_time_distribution"] == "deterministic_7d" else 10
        for rep in range(reps):
            for label, graph in [("real_graph_score_vector", network), ("random_shuffled_product_score", placebo_network)]:
                for policy in ["P3_basket_deterministic", "P4_basket_stochastic"]:
                    result = run_one(base, scenario, policy, selected_alpha, rep, network=graph)
                    rows.append({"analysis": "graph_placebo", "graph_type": label, "scenario_id": scenario["scenario_id"], "replication": rep, **result})
    frame = pd.DataFrame(rows)
    frame.to_csv(out / "placebo_results.csv", index=False)
    summary = frame.groupby(["scenario_id", "policy", "graph_type"], as_index=False)[["total_cost", "average_inventory_units", "item_fill_rate", "complete_basket_fill_rate", "unmet_units"]].mean()
    summary.to_csv(out / "placebo_summary.csv", index=False)
    paired_rows = []
    for keys, group in frame.groupby(["scenario_id", "replication", "policy"], sort=False):
        values = group.set_index("graph_type")
        if not {"real_graph_score_vector", "random_shuffled_product_score"}.issubset(values.index):
            continue
        row = {"scenario_id": keys[0], "replication": keys[1], "policy": keys[2]}
        for metric in ["total_cost", "average_inventory_units", "item_fill_rate", "complete_basket_fill_rate", "unmet_units"]:
            row[f"{metric}_difference_real_minus_placebo"] = float(values.loc["real_graph_score_vector", metric] - values.loc["random_shuffled_product_score", metric])
        paired_rows.append(row)
    paired = pd.DataFrame(paired_rows)
    interval_rows = []
    for policy, group in paired.groupby("policy", sort=False):
        row = {"policy": policy, "replication_paths": int(len(group)), "placebo_seed": 20261020}
        for column in [c for c in paired.columns if c.endswith("_real_minus_placebo")]:
            values = group[column].to_numpy(float)
            row[f"{column}_mean"] = float(values.mean())
            row[f"{column}_p025"] = float(np.quantile(values, 0.025))
            row[f"{column}_p975"] = float(np.quantile(values, 0.975))
        interval_rows.append(row)
    pd.DataFrame(interval_rows).to_csv(out / "placebo_comparison_summary.csv", index=False)
    return frame


def run_inventory_matched(root: Path, out: Path, base, scenarios: pd.DataFrame, selected_alpha: float) -> pd.DataFrame:
    targets = [0.80, 0.85, 0.90, 0.95, 0.975, 0.99, 0.995]
    rows = []
    for _, scenario in scenarios.iterrows():
        reps = 1 if scenario["lead_time_distribution"] == "deterministic_7d" else 10
        for rep in range(reps):
            for basket_policy, independent_policy in [("P3_basket_deterministic", "P1_independent_deterministic"), ("P4_basket_stochastic", "P2_independent_stochastic")]:
                basket = run_one(base, scenario, basket_policy, selected_alpha, rep)
                candidates = [run_one(base, scenario, independent_policy, 0.0, rep, service=target) for target in targets]
                matched = min(candidates, key=lambda result: abs(float(result["average_inventory_units"]) - float(basket["average_inventory_units"])))
                rows.append({
                    "analysis": "inventory_matched_independent_baseline",
                    "scenario_id": scenario["scenario_id"],
                    "replication": rep,
                    "basket_policy": basket_policy,
                    "matched_policy": independent_policy,
                    "basket_service_target": basket["service_target"],
                    "matched_service_target": matched["service_target"],
                    "basket_inventory": basket["average_inventory_units"],
                    "matched_inventory": matched["average_inventory_units"],
                    "basket_cost": basket["total_cost"],
                    "matched_cost": matched["total_cost"],
                    "basket_item_fill": basket["item_fill_rate"],
                    "matched_item_fill": matched["item_fill_rate"],
                    "basket_fill": basket["complete_basket_fill_rate"],
                    "matched_fill": matched["complete_basket_fill_rate"],
                    "cost_difference_basket_minus_matched": basket["total_cost"] - matched["total_cost"],
                    "item_fill_difference_basket_minus_matched": basket["item_fill_rate"] - matched["item_fill_rate"],
                    "basket_fill_difference_basket_minus_matched": basket["complete_basket_fill_rate"] - matched["complete_basket_fill_rate"],
                })
    frame = pd.DataFrame(rows)
    frame.to_csv(out / "inventory_matched_baseline.csv", index=False)
    return frame


def run_break_even(out: Path, raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (scenario_id, rep), frame in raw.groupby(["scenario_id", "replication"]):
        values = frame.set_index("policy")
        for basket_policy, base_policy, contrast in [("P3_basket_deterministic", "P1_independent_deterministic", "P3_minus_P1"), ("P4_basket_stochastic", "P2_independent_stochastic", "P4_minus_P2")]:
            if basket_policy not in values.index or base_policy not in values.index:
                continue
            b = values.loc[basket_policy]
            i = values.loc[base_policy]
            delta_nonshort = (float(b["total_cost"]) - float(b["shortage_cost"])) - (float(i["total_cost"]) - float(i["shortage_cost"]))
            delta_unmet = float(b["unmet_units"]) - float(i["unmet_units"])
            break_even_p = delta_nonshort / (-delta_unmet) if delta_unmet < 0 else np.nan
            h = float(b["holding_cost_per_unit_week"])
            rows.append({"scenario_id": scenario_id, "replication": rep, "contrast": contrast, "delta_nonshort_cost": delta_nonshort, "delta_unmet_units": delta_unmet, "break_even_shortage_penalty_p": break_even_p, "break_even_p_over_h": break_even_p / h if np.isfinite(break_even_p) else np.nan, "actual_p_over_h": float(b["shortage_penalty_per_unit"]) / h})
    frame = pd.DataFrame(rows)
    frame.to_csv(out / "break_even_analysis.csv", index=False)
    return frame


def edge_stability_scores(root: Path, products: np.ndarray) -> np.ndarray:
    lines = pd.read_csv(root / "data" / "processed" / "uci_transaction_lines_clean.csv", dtype={"invoice_id": "string", "stock_code": "string"}, usecols=["invoice_id", "invoice_date", "stock_code"])
    lines["invoice_date"] = pd.to_datetime(lines["invoice_date"])
    train = lines.loc[lines["invoice_date"] <= pd.Timestamp("2011-06-27")]
    midpoint = train["invoice_date"].min() + (train["invoice_date"].max() - train["invoice_date"].min()) / 2
    halves = [train.loc[train["invoice_date"] <= midpoint], train.loc[train["invoice_date"] > midpoint]]
    pair_counts = []
    for half in halves:
        counter = {}
        for _, group in half.groupby("invoice_id")["stock_code"]:
            vals = sorted(set(str(x) for x in group))
            for a, b in itertools.combinations(vals, 2):
                key = (a, b)
                counter[key] = counter.get(key, 0) + 1
        pair_counts.append(counter)
    neighbors = []
    for counter in pair_counts:
        mapping = {}
        for (a, b), count in counter.items():
            if count < 5:
                continue
            mapping.setdefault(a, set()).add(b)
            mapping.setdefault(b, set()).add(a)
        neighbors.append(mapping)
    scores = np.zeros(len(products), dtype=float)
    for i, product in enumerate(products):
        a = neighbors[0].get(str(product), set())
        b = neighbors[1].get(str(product), set())
        union = a | b
        scores[i] = len(a & b) / len(union) if union else 0.0
    return scores


def run_sensitivity(root: Path, out: Path, base, scenarios: pd.DataFrame, selected_alpha: float) -> pd.DataFrame:
    rows = []
    scenario = scenarios.loc[scenarios["scenario_id"] == "S05"].iloc[0]
    _, _, products, _, _, _, _, base_network, _ = base
    # Graph threshold and top-k robustness.
    for parameter, values in [("graph_min_pair_count", [5, 10, 20]), ("graph_top_k", [3, 5, 10])]:
        for value in values:
            min_pairs = int(value) if parameter == "graph_min_pair_count" else 5
            top_k = int(value) if parameter == "graph_top_k" else 5
            network = network_scores(root, products, min_pair_count=min_pairs, top_k=top_k)
            for rep in range(10):
                for policy in ["P1_independent_deterministic", "P3_basket_deterministic"]:
                    result = run_one(base, scenario, policy, selected_alpha, rep, network=network)
                    rows.append({"analysis": parameter, "setting": value, "replication": rep, "policy": policy, **result})
    # Backorder/lost-sales and basket definition.
    for mode in ["lost_sales", "backorder"]:
        for rep in range(10):
            for policy in ["P1_independent_deterministic", "P2_independent_stochastic", "P3_basket_deterministic", "P4_basket_stochastic"]:
                result = run_one(base, scenario, policy, selected_alpha, rep, backorder_mode=mode)
                rows.append({"analysis": "stockout_model", "setting": mode, "replication": rep, "policy": policy, **result})
    for definition in ["all_units", "all_items"]:
        for rep in range(10):
            for policy in ["P3_basket_deterministic", "P4_basket_stochastic"]:
                result = run_one(base, scenario, policy, selected_alpha, rep, basket_definition=definition)
                rows.append({"analysis": "basket_definition", "setting": definition, "replication": rep, "policy": policy, **result})
    # Universe support threshold robustness, recomputing the product universe and forecasts.
    for threshold in [10, 20, 50]:
        threshold_base = load_base(root, support_threshold=threshold, min_pair_count=5, top_k=5)
        for rep in range(10):
            for policy in ["P1_independent_deterministic", "P3_basket_deterministic"]:
                result = run_one(threshold_base, scenario, policy, selected_alpha, rep)
                rows.append({"analysis": "universe_support_threshold", "setting": threshold, "replication": rep, "policy": policy, **result})
    # RQ3: concentration and edge stability strata, using segment-level outcomes.
    concentration = base_network
    stability = edge_stability_scores(root, products)
    for label, score in [("basket_concentration", concentration), ("edge_stability", stability)]:
        low_cut, high_cut = np.quantile(score, [0.25, 0.75])
        for segment, mask in [("low", score <= low_cut), ("high", score >= high_cut)]:
            for rep in range(10):
                for policy in ["P1_independent_deterministic", "P3_basket_deterministic"]:
                    result = run_one(base, scenario, policy, selected_alpha, rep, metric_mask=mask)
                    rows.append({"analysis": label, "setting": segment, "replication": rep, "policy": policy, "segment_products": int(mask.sum()), **result})
    # Holding-cost variation is intentionally retained as its own analysis label.
    for scenario_id in ["S04", "S05", "S06"]:
        cost_scenario = scenarios.loc[scenarios["scenario_id"] == scenario_id].iloc[0]
        reps = 10
        for rep in range(reps):
            for policy in ["P1_independent_deterministic", "P3_basket_deterministic"]:
                result = run_one(base, cost_scenario, policy, selected_alpha, rep)
                rows.append({"analysis": "holding_cost_variation", "setting": scenario_id, "replication": rep, "policy": policy, **result})
    frame = pd.DataFrame(rows)
    frame.to_csv(out / "sensitivity_results.csv", index=False)
    return frame


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else SCRIPT_DIR.parent
    out = root / "results"
    out.mkdir(parents=True, exist_ok=True)
    scenarios = scenario_frame(root)
    base = load_base(root)
    calibration = pd.read_csv(out / "basket_alpha_validation_calibration.csv")
    selected_alpha = float(calibration.sort_values(["total_cost", "alpha"]).iloc[0]["alpha"])
    # Preserve the main experiment's selected alpha when its calibration table has no eligible target.
    if "selected_basket_alpha" in json.loads((out / "experiment_config.json").read_text(encoding="utf-8")):
        selected_alpha = float(json.loads((out / "experiment_config.json").read_text(encoding="utf-8"))["selected_basket_alpha"])
    raw = pd.read_csv(out / "inventory_results_by_replication.csv")
    frontier = run_frontier(root, out, base, scenarios, selected_alpha)
    placebo = run_placebo(root, out, base, scenarios, selected_alpha)
    matched = run_inventory_matched(root, out, base, scenarios, selected_alpha)
    break_even = run_break_even(out, raw)
    sensitivity = run_sensitivity(root, out, base, scenarios, selected_alpha)
    report = {
        "selected_alpha": selected_alpha,
        "frontier_rows": len(frontier),
        "placebo_rows": len(placebo),
        "inventory_matched_rows": len(matched),
        "break_even_rows": len(break_even),
        "sensitivity_rows": len(sensitivity),
        "notes": "Primary policies use cost-based critical fractile p/(p+h); all inventory, lead-time, cost, and stockout outcomes remain simulated.",
    }
    (out / "p0_analysis_config.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
