"""Create level and paired-contrast tables from the frozen Phase 3 replay."""

from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"


def interval(x):
    x = pd.Series(x).dropna()
    return {"mean": float(x.mean()), "p025": float(x.quantile(.025)), "p975": float(x.quantile(.975)), "n": int(x.size)}


def main():
    d = pd.read_csv(OUT / "phase3_test_results.csv")
    d = d.loc[d["scenario_id"] == "S05"].copy()
    levels = []
    for variant in ["PA1", "C1_matched_to_PA1", "C4", "C2", "C3", "C5"]:
        if variant == "C1_matched_to_PA1":
            x = d.loc[d["variant"] == "PA1"].copy()
            metrics = {"total_cost": x["control_total_cost"], "average_inventory_units": x["control_average_inventory_units"], "item_fill_rate": x["control_item_fill_rate"], "complete_basket_fill_rate": x["control_complete_basket_fill_rate"], "unmet_units": x["control_unmet_units"], "stockout_frequency": x["control_stockout_frequency"]}
        else:
            x = d.loc[d["variant"] == variant].copy()
            metrics = {m: x[m] for m in ["total_cost", "average_inventory_units", "item_fill_rate", "complete_basket_fill_rate", "unmet_units", "stockout_frequency"]}
        row = {"scenario_id": "S05", "variant": variant, "rows": len(x)}
        for name, values in metrics.items():
            stats = interval(values)
            for k, v in stats.items():
                row[f"{name}_{k}"] = v
        levels.append(row)
    pd.DataFrame(levels).to_csv(OUT / "phase3_primary_level_table.csv", index=False)

    contrasts = []
    pa = d.loc[d["variant"] == "PA1"].sort_values("replication")
    c1 = {m: pa["control_" + m] for m in ["total_cost", "average_inventory_units", "item_fill_rate", "complete_basket_fill_rate"]}
    c1.update({"unmet_units": None, "stockout_frequency": None})
    metrics = ["total_cost", "average_inventory_units", "item_fill_rate", "complete_basket_fill_rate", "unmet_units", "stockout_frequency"]
    row = {"contrast": "PA1_minus_C1", "estimand": "inventory-matched independent control"}
    for m in metrics:
        if m in {"unmet_units", "stockout_frequency"}:
            continue
        values = pa[m] - c1[m]
        stats = interval(values)
        for k, v in stats.items(): row[f"{m}_difference_{k}"] = v
    contrasts.append(row)
    for name in ["PA1_minus_C4", "PA1_minus_C2", "PA1_minus_C3", "PA1_minus_C5"]:
        x = pd.read_csv(OUT / "phase3_paired_contrasts.csv").loc[lambda z: z["variant"] == name]
        row = {"contrast": name, "estimand": "paired common-target placebo/control"}
        for m in ["total_cost_difference", "average_inventory_difference", "item_fill_difference", "basket_fill_difference", "unmet_units_difference", "stockout_difference"]:
            stats = interval(x[m])
            for k, v in stats.items(): row[f"{m}_{k}"] = v
        contrasts.append(row)
    pd.DataFrame(contrasts).to_csv(OUT / "phase3_primary_paired_summary.csv", index=False)
    diag = {"primary_scenario": "S05", "alpha": 1.5, "matching_tolerance": .01, "max_relative_inventory_gap_PA1": float(pa["relative_inventory_gap"].max()), "max_relative_inventory_gap_C4": float(d.loc[d["variant"] == "C4", "relative_inventory_gap"].max()), "replications": int(len(pa)), "bootstrap_resamples": 1000, "rolling_windows": 3}
    (OUT / "phase3_primary_diagnostics.json").write_text(json.dumps(diag, indent=2), encoding="utf-8")
    print(json.dumps(diag, indent=2))


if __name__ == "__main__":
    main()
