"""Add the matched PA1-minus-C1 rows and clustered summaries to a completed run."""

from pathlib import Path
import numpy as np
import pandas as pd


def mean_ci(values):
    values = np.asarray(values, dtype=float)
    mean = float(values.mean())
    se = float(values.std(ddof=1) / np.sqrt(len(values))) if len(values) > 1 else 0.0
    return mean, mean - 1.96 * se, mean + 1.96 * se


def main():
    root = Path(__file__).resolve().parents[1]
    out = root / "results"
    raw = pd.read_csv(out / "phase3_test_results.csv")
    pa = raw.loc[raw["variant"] == "PA1"].copy()
    c1 = pd.DataFrame({
        "scenario_id": pa["scenario_id"], "replication": pa["replication"],
        "variant": "PA1_minus_C1", "policy": pa["policy"],
        "independent_policy": pa["independent_policy"], "alpha": pa["alpha"], "tau": pa["tau"],
        "matched_service_target": pa["matched_service_target"],
        "relative_inventory_gap": pa["relative_inventory_gap"],
        "total_cost_difference": pa["total_cost"] - pa["control_total_cost"],
        "average_inventory_difference": pa["average_inventory_units"] - pa["control_average_inventory_units"],
        "item_fill_difference": pa["item_fill_rate"] - pa["control_item_fill_rate"],
        "basket_fill_difference": pa["complete_basket_fill_rate"] - pa["control_complete_basket_fill_rate"],
    })
    # C1 outcome differences are retained in the level rows; the headline
    # summary uses the four service/cost fields available in that frozen row.
    c1["unmet_units_difference"] = np.nan
    c1["stockout_difference"] = np.nan
    contrast = pd.read_csv(out / "phase3_paired_contrasts.csv")
    contrast = pd.concat([contrast, c1], ignore_index=True)
    contrast.to_csv(out / "phase3_paired_contrasts.csv", index=False)
    metric_cols = ["total_cost_difference", "average_inventory_difference", "item_fill_difference", "basket_fill_difference"]
    rows = []
    for (scenario_id, name), group in contrast.groupby(["scenario_id", "variant"]):
        row = {"scenario_id": scenario_id, "contrast": name, "rows": len(group)}
        for col in metric_cols:
            values = group[col].dropna().to_numpy(dtype=float)
            row[f"{col}_mean"], row[f"{col}_ci95_low"], row[f"{col}_ci95_high"] = mean_ci(values)
            row[f"{col}_p025"] = float(np.quantile(values, .025)); row[f"{col}_p975"] = float(np.quantile(values, .975))
        rows.append(row)
    summary = pd.DataFrame(rows)
    pooled_rows = []
    for name, group in contrast.groupby("variant"):
        row = {"scenario_id": "POOLED", "contrast": name, "rows": len(group)}
        for col in metric_cols:
            values = group[col].dropna().to_numpy(dtype=float)
            row[f"{col}_mean"], row[f"{col}_ci95_low"], row[f"{col}_ci95_high"] = mean_ci(values)
            row[f"{col}_p025"] = float(np.quantile(values, .025)); row[f"{col}_p975"] = float(np.quantile(values, .975))
        pooled_rows.append(row)
    pd.DataFrame(pooled_rows + rows).to_csv(out / "phase3_paired_contrasts_summary.csv", index=False)
    summary.to_csv(out / "phase3_scenario_contrast_summary.csv", index=False)
    cluster = []
    for name, group in summary.groupby("contrast"):
        row = {"contrast": name, "scenario_count": len(group)}
        for col in metric_cols:
            values = group[f"{col}_mean"].to_numpy(dtype=float)
            row[f"{col}_cluster_mean"], row[f"{col}_cluster_ci95_low"], row[f"{col}_cluster_ci95_high"] = mean_ci(values)
        cluster.append(row)
    pd.DataFrame(cluster).to_csv(out / "phase3_cluster_pooled_summary.csv", index=False)
    print(summary.groupby("contrast")["rows"].sum().to_string())


if __name__ == "__main__":
    main()
