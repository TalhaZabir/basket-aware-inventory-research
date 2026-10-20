"""Full Phase 3 replay across all frozen scenarios with paired uncertainty."""

from __future__ import annotations

import hashlib
import json
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
from run_phase2_validation import SAFETY_MULTIPLIER, TARGET_GRID, lead_matrix  # noqa: E402

ALPHA = 1.5
TAU = 0.50
MATCH_TOLERANCE = 0.01
REPLICATIONS = 120
BOOTSTRAP_REPS = 1000
VARIANTS = ["PA1", "C4"]
CONTRASTS = ["PA1_minus_C1", "PA1_minus_C4"]
PARENT_CONFIG_HASH = "ac87a2e332c1c82cff38e93a053770ebe97b744c7af8931e9f3269582ef05866"


def run(demand, weeks, forecast, residual, network, baskets, scenario, policy, alpha, lead, buffer, target, weekly=False):
    return simulate_policy(demand, weeks, forecast, residual * SAFETY_MULTIPLIER, network, baskets, scenario, policy, alpha, lead, service_target=target, basket_buffer=buffer, return_weekly=weekly)


def control_match(demand, weeks, forecast, residual, network, baskets, scenario, independent, lead, target_inventory, candidates=None):
    if candidates is None:
        candidates = [run(demand, weeks, forecast, residual, network, baskets, scenario, independent, 0.0, lead, None, target, False) for target in TARGET_GRID]
    candidates = sorted(candidates, key=lambda x: float(x["service_target"]))
    for c in candidates:
        if abs(float(c["average_inventory_units"]) - target_inventory) / max(target_inventory, 1.0) <= MATCH_TOLERANCE:
            return c
    for low, high in zip(candidates[:-1], candidates[1:]):
        li, hi = float(low["average_inventory_units"]), float(high["average_inventory_units"])
        if li <= target_inventory <= hi and hi > li:
            w = (target_inventory - li) / (hi - li)
            target = float(low["service_target"]) + w * (float(high["service_target"]) - float(low["service_target"]))
            c = run(demand, weeks, forecast, residual, network, baskets, scenario, independent, 0.0, lead, None, target, False)
            if abs(float(c["average_inventory_units"]) - target_inventory) / max(target_inventory, 1.0) <= MATCH_TOLERANCE:
                return c
    return min(candidates, key=lambda x: abs(float(x["average_inventory_units"]) - target_inventory))


def diff_metric(a, b, metric):
    return float(a[metric]) - float(b[metric])


def mean_ci(values):
    values = np.asarray(values, dtype=float)
    mean = float(values.mean())
    se = float(values.std(ddof=1) / np.sqrt(len(values))) if len(values) > 1 else 0.0
    return mean, mean - 1.96 * se, mean + 1.96 * se


def bootstrap_summary(weekly_store: list[dict[str, object]], out: Path) -> None:
    rows = []
    for scenario_id in sorted({str(x["scenario_id"]) for x in weekly_store}):
        group = [x for x in weekly_store if str(x["scenario_id"]) == scenario_id]
        for contrast in CONTRASTS:
            if contrast == "PA1_minus_C1":
                left_key, right_key = "PA1", "C1_PA1"
            else:
                # Placebo contrasts are paired at the common frozen target;
                # only PA1 and the popularity control receive matched-
                # inventory independent controls.
                left_key, right_key = "PA1", contrast.split("_minus_")[1]
            left = [x for x in group if x["variant"] == left_key]
            right = [x for x in group if x["variant"] == right_key]
            if not left or not right:
                continue
            left = sorted(left, key=lambda x: int(x["replication"]))
            right = sorted(right, key=lambda x: int(x["replication"]))
            n = min(len(left), len(right))
            h = len(left[0]["weekly_cost"])
            rng = np.random.default_rng(SEED + 900000 + sum(ord(c) for c in scenario_id) + sum(ord(c) for c in contrast))
            for b in range(BOOTSTRAP_REPS):
                rep_idx = rng.integers(0, n, size=n)
                week_idx = rng.integers(0, h, size=h)
                def agg(key):
                    vals = [key[i]["weekly_cost"][week_idx].sum() for i in rep_idx]
                    inv = [key[i]["weekly_inventory"][week_idx].mean() for i in rep_idx]
                    fulfilled = sum(key[i]["weekly_fulfilled"][week_idx].sum() for i in rep_idx)
                    demand = sum(key[i]["weekly_demand"][week_idx].sum() for i in rep_idx)
                    unmet = sum(key[i]["weekly_unmet"][week_idx].sum() for i in rep_idx)
                    baskets = sum(key[i]["weekly_baskets"][week_idx].sum() for i in rep_idx)
                    complete = sum(key[i]["weekly_complete_baskets"][week_idx].sum() for i in rep_idx)
                    stockouts = sum(key[i]["weekly_stockout_events"][week_idx].sum() for i in rep_idx)
                    unmet_mean = float(np.mean([key[i]["weekly_unmet"][week_idx].sum() for i in rep_idx]))
                    stockout_mean = float(np.mean([key[i]["weekly_stockout_events"][week_idx].sum() for i in rep_idx]))
                    return np.mean(vals), np.mean(inv), fulfilled / max(demand, 1.0), complete / max(baskets, 1.0), unmet_mean, stockout_mean
                la = agg(left); rb = agg(right)
                rows.append({"scenario_id": scenario_id, "contrast": contrast, "bootstrap_replication": b, "total_cost_difference": la[0]-rb[0], "average_inventory_difference": la[1]-rb[1], "item_fill_difference": la[2]-rb[2], "basket_fill_difference": la[3]-rb[3], "unmet_units_difference": la[4]-rb[4], "stockout_difference": la[5]-rb[5]})
    frame = pd.DataFrame(rows)
    frame.to_csv(out / "phase3_bootstrap_week_results.csv", index=False)
    summary = frame.groupby(["scenario_id", "contrast"], as_index=False).agg({c: ["mean", lambda x: x.quantile(.025), lambda x: x.quantile(.975)] for c in frame.columns if c not in {"scenario_id", "contrast", "bootstrap_replication"}})
    summary.columns = ["_".join(str(v) for v in c if str(v) != "") if isinstance(c, tuple) else str(c) for c in summary.columns]
    summary.to_csv(out / "phase3_bootstrap_week_summary.csv", index=False)
    pooled = frame.groupby("contrast", as_index=False).agg({c: ["mean", lambda x: x.quantile(.025), lambda x: x.quantile(.975)] for c in frame.columns if c not in {"scenario_id", "contrast", "bootstrap_replication"}})
    pooled.columns = ["_".join(str(v) for v in c if str(v) != "") if isinstance(c, tuple) else str(c) for c in pooled.columns]
    pooled.to_csv(out / "phase3_bootstrap_pooled_summary.csv", index=False)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out = root / "results"
    _weekly, weeks, demand, products, train_idx, _val_idx, test_idx = weekly_matrix(root, support_threshold=20)
    residual = internal_calibration(demand, train_idx)["scale"]
    forecast = build_test_empirical_forecast(demand, test_idx)
    test_demand, test_weeks = demand[:, test_idx], weeks[test_idx]
    network = network_scores(root, products, min_pair_count=DEFAULT_MIN_PAIR_COUNT, top_k=DEFAULT_TOP_K)
    baskets = basket_map(root, products, test_weeks)
    graphs = {"default": default_edges(root, products), "stale": stale_edges(root, products)}
    graphs["shuffled"] = shuffled_basket_edges(root, products, seed=SEED)
    graphs["rewired"] = rewired_edges(graphs["default"], seed=SEED)
    buffers, metadata = buffers_from_graphs(root, products, residual, SAFETY_MULTIPLIER, graphs["default"], graphs["stale"], graphs["shuffled"], graphs["rewired"], tau=TAU)
    scenarios = pd.read_csv(root / "data" / "synthetic" / "inventory_scenarios.csv")
    rows = []
    weekly_store: list[dict[str, object]] = []
    matching_rows = []
    for scenario_dict in scenarios.to_dict("records"):
        scenario = pd.Series(scenario_dict)
        stochastic = scenario["lead_time_distribution"] != "deterministic_7d"
        rep_count = REPLICATIONS
        suffix = "stochastic" if stochastic else "deterministic"
        independent = "P2_independent_stochastic" if stochastic else "P1_independent_deterministic"
        for rep in range(rep_count):
            lead = lead_matrix(scenario, independent, len(test_idx), len(products), rep)
            nominal = float(scenario["shortage_penalty_per_unit"]) / (float(scenario["shortage_penalty_per_unit"]) + float(scenario["holding_cost_per_unit_week"]))
            policy_results = {}
            control_results = {}
            # The independent target grid is common to every basket-aware
            # variant in this scenario/replication.  Cache it once; otherwise
            # the matched-inventory design needlessly reruns the same twelve
            # independent simulations for every variant.
            control_candidates = [run(test_demand, test_weeks, forecast, residual, network, baskets, scenario, independent, 0.0, lead, None, target, False) for target in TARGET_GRID]
            for variant in VARIANTS:
                policy = f"{variant}_{suffix}"
                result = run(test_demand, test_weeks, forecast, residual, network, baskets, scenario, policy, ALPHA, lead, buffers[variant], nominal, True)
                policy_results[variant] = result
                if variant in {"PA1", "C4"}:
                    control = control_match(test_demand, test_weeks, forecast, residual, network, baskets, scenario, independent, lead, float(result["average_inventory_units"]), candidates=control_candidates)
                    control_weekly = run(test_demand, test_weeks, forecast, residual, network, baskets, scenario, independent, 0.0, lead, None, float(control["service_target"]), True)
                    control_results[variant] = control_weekly
                    gap = abs(float(result["average_inventory_units"])-float(control_weekly["average_inventory_units"])) / max(float(result["average_inventory_units"]),1.0)
                    control_fields = {"matched_service_target": float(control["service_target"]), "relative_inventory_gap": gap, "control_total_cost": float(control_weekly["total_cost"]), "control_average_inventory_units": float(control_weekly["average_inventory_units"]), "control_item_fill_rate": float(control_weekly["item_fill_rate"]), "control_complete_basket_fill_rate": float(control_weekly["complete_basket_fill_rate"])}
                    matching_rows.append({"scenario_id": scenario["scenario_id"], "replication": rep, "comparison": f"{variant}_minus_C1", "policy_inventory": float(result["average_inventory_units"]), "control_inventory": float(control_weekly["average_inventory_units"]), "inventory_difference": float(result["average_inventory_units"])-float(control_weekly["average_inventory_units"]), "inventory_difference_percent": 100.0 * gap, "within_1_percent": bool(gap <= MATCH_TOLERANCE)})
                else:
                    control_weekly = None
                    control_fields = {"matched_service_target": np.nan, "relative_inventory_gap": np.nan, "control_total_cost": np.nan, "control_average_inventory_units": np.nan, "control_item_fill_rate": np.nan, "control_complete_basket_fill_rate": np.nan}
                rows.append({"scenario_id": scenario["scenario_id"], "replication": rep, "variant": variant, "policy": policy, "independent_policy": independent, "alpha": ALPHA, "tau": TAU, **control_fields, **{m: float(result[m]) for m in ["total_cost","average_inventory_units","item_fill_rate","complete_basket_fill_rate","unmet_units","stockout_frequency"]}})
                weekly_store.append({"scenario_id": scenario["scenario_id"], "replication": rep, "variant": variant, **{k: result[k] for k in ["weekly_cost","weekly_inventory","weekly_fulfilled","weekly_demand","weekly_unmet","weekly_stockout_events","weekly_baskets","weekly_complete_baskets"]}})
                if control_weekly is not None:
                    weekly_store.append({"scenario_id": scenario["scenario_id"], "replication": rep, "variant": f"C1_{variant}", **{k: control_weekly[k] for k in ["weekly_cost","weekly_inventory","weekly_fulfilled","weekly_demand","weekly_unmet","weekly_stockout_events","weekly_baskets","weekly_complete_baskets"]}})
            pa, c1 = policy_results["PA1"], control_results["PA1"]
            rows.append({"scenario_id": scenario["scenario_id"], "replication": rep, "variant": "PA1_minus_C1", "policy": f"PA1_{suffix}", "independent_policy": independent, "alpha": ALPHA, "tau": TAU, "matched_service_target": float(c1["service_target"]), "relative_inventory_gap": abs(float(pa["average_inventory_units"])-float(c1["average_inventory_units"])) / max(float(pa["average_inventory_units"]),1.0), "total_cost_difference": diff_metric(pa, c1, "total_cost"), "average_inventory_difference": diff_metric(pa, c1, "average_inventory_units"), "item_fill_difference": diff_metric(pa, c1, "item_fill_rate"), "basket_fill_difference": diff_metric(pa, c1, "complete_basket_fill_rate"), "unmet_units_difference": diff_metric(pa, c1, "unmet_units"), "stockout_difference": diff_metric(pa, c1, "stockout_frequency")})
            for other in ["C4"]:
                pa, comp = policy_results["PA1"], policy_results[other]
                rows.append({"scenario_id": scenario["scenario_id"], "replication": rep, "variant": f"PA1_minus_{other}", "policy": f"PA1_{suffix}", "independent_policy": f"{other}_{suffix}", "alpha": ALPHA, "tau": TAU, "matched_service_target": np.nan, "relative_inventory_gap": np.nan, "total_cost_difference": diff_metric(pa, comp, "total_cost"), "average_inventory_difference": diff_metric(pa, comp, "average_inventory_units"), "item_fill_difference": diff_metric(pa, comp, "item_fill_rate"), "basket_fill_difference": diff_metric(pa, comp, "complete_basket_fill_rate"), "unmet_units_difference": diff_metric(pa, comp, "unmet_units"), "stockout_difference": diff_metric(pa, comp, "stockout_frequency")})
    frame = pd.DataFrame(rows)
    frame.to_csv(out / "phase3_test_results.csv", index=False)
    contrast = frame.loc[frame["variant"].str.startswith("PA1_minus_")].copy()
    contrast.to_csv(out / "phase3_paired_contrasts.csv", index=False)
    matching = pd.DataFrame(matching_rows)
    matching.to_csv(out / "phase3_matching_quality.csv", index=False)
    if not matching.empty and not bool(matching["within_1_percent"].all()):
        raise RuntimeError("At least one matched comparison exceeded the 1% inventory band.")
    summaries = []
    scenario_summaries = []
    for name, group in contrast.groupby("variant"):
        row = {"scenario_id": "POOLED", "contrast": name, "rows": len(group)}
        for col in ["total_cost_difference","average_inventory_difference","item_fill_difference","basket_fill_difference","unmet_units_difference","stockout_difference"]:
            row[f"{col}_mean"], row[f"{col}_ci95_low"], row[f"{col}_ci95_high"] = mean_ci(group[col].to_numpy())
            row[f"{col}_p025"] = group[col].quantile(.025); row[f"{col}_p975"] = group[col].quantile(.975)
        summaries.append(row)
    for (scenario_id, name), group in contrast.groupby(["scenario_id", "variant"]):
        row = {"scenario_id": scenario_id, "contrast": name, "rows": len(group)}
        for col in ["total_cost_difference","average_inventory_difference","item_fill_difference","basket_fill_difference","unmet_units_difference","stockout_difference"]:
            row[f"{col}_mean"], row[f"{col}_ci95_low"], row[f"{col}_ci95_high"] = mean_ci(group[col].to_numpy())
            row[f"{col}_p025"] = group[col].quantile(.025); row[f"{col}_p975"] = group[col].quantile(.975)
        scenario_summaries.append(row)
    pd.DataFrame(summaries + scenario_summaries).to_csv(out / "phase3_paired_contrasts_summary.csv", index=False)
    pd.DataFrame(scenario_summaries).to_csv(out / "phase3_scenario_contrast_summary.csv", index=False)
    cluster_rows = []
    scenario_frame = pd.DataFrame(scenario_summaries)
    for name, group in scenario_frame.groupby("contrast"):
        row = {"contrast": name, "scenario_count": len(group)}
        for col in ["total_cost_difference", "average_inventory_difference", "item_fill_difference", "basket_fill_difference", "unmet_units_difference", "stockout_difference"]:
            values = group[f"{col}_mean"].to_numpy(dtype=float)
            mean, low, high = mean_ci(values)
            row[f"{col}_cluster_mean"] = mean
            row[f"{col}_cluster_ci95_low"] = low
            row[f"{col}_cluster_ci95_high"] = high
        cluster_rows.append(row)
    pd.DataFrame(cluster_rows).to_csv(out / "phase3_cluster_pooled_summary.csv", index=False)
    bootstrap_summary(weekly_store, out)
    config = {"phase":3,"primary_scenario":"S05","scenario_scope":"all_12_scenarios","parent_validation_config_hash":PARENT_CONFIG_HASH,"selected_alpha":ALPHA,"tau":TAU,"match_tolerance":MATCH_TOLERANCE,"replications_stochastic":REPLICATIONS,"replications_deterministic":REPLICATIONS,"bootstrap_resamples_per_scenario":BOOTSTRAP_REPS,"variants":VARIANTS,"contrasts":CONTRASTS,"test_window_used":True,"graph_metadata":metadata}
    config["config_hash"] = hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode()).hexdigest()
    (out / "phase3_test_config.json").write_text(json.dumps(config, indent=2, default=str), encoding="utf-8")
    report = "# Phase 3 full scenario test report\n\n" + f"Alpha={ALPHA} is interior to the validation grid, matching tolerance is {MATCH_TOLERANCE:.1%}, all twelve scenarios use {REPLICATIONS} paired replications, and each scenario-contrast uses {BOOTSTRAP_REPS} bootstrap resamples. The primary paired contrasts are PA1−C1 and PA1−C4; PA1−C2, PA1−C3, and PA1−C5 remain placebo contrasts. Configuration hash: `{config['config_hash']}`.\n\n" + "The summary files report paired-mean 95% confidence intervals and empirical replication percentile ranges. The matching-quality file verifies that every PA1/C4 comparison is within the frozen 1% inventory band.\n"
    (out / "phase_3_test_report.md").write_text(report, encoding="utf-8")
    print(json.dumps({"config_hash":config["config_hash"],"rows":len(frame),"contrast_rows":len(contrast),"weekly_store_rows":len(weekly_store)},indent=2))


if __name__ == "__main__":
    main()
