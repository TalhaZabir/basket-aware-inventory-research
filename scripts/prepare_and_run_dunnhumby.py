"""Prepare and replay the documented dunnhumby Complete Journey basket data.

This is an external validation pipeline, not a merge with UCI.  Inventory,
lead time, costs, and the policy replay are explicitly synthetic assumptions;
the transaction data and basket graph are observed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "dunnhumby" / "csv" / "transaction_data.csv"
OUT = ROOT / "data" / "processed" / "dunnhumby"
RESULTS = ROOT / "results"
TOP_N = 300
TRAIN_END, VALIDATION_END, TEST_END = 78, 90, 102
ALPHA = 1.5


def prepare() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, object]]:
    OUT.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(RAW, usecols=["household_key", "BASKET_ID", "DAY", "PRODUCT_ID", "QUANTITY", "SALES_VALUE", "STORE_ID", "WEEK_NO"])
    original_rows = len(frame)
    original_products = int(frame["PRODUCT_ID"].nunique())
    returns = int((frame["QUANTITY"] <= 0).sum())
    frame = frame.loc[(frame["QUANTITY"] > 0) & (frame["WEEK_NO"].between(1, TEST_END))].copy()
    support = frame.loc[frame["WEEK_NO"] <= TRAIN_END].groupby("PRODUCT_ID")["WEEK_NO"].nunique()
    volume = frame.loc[frame["WEEK_NO"] <= TRAIN_END].groupby("PRODUCT_ID")["QUANTITY"].sum()
    selected = support.to_frame("train_active_weeks").join(volume.rename("train_units"), how="left").sort_values(["train_active_weeks", "train_units"], ascending=False).head(TOP_N).index
    frame = frame.loc[frame["PRODUCT_ID"].isin(selected)].copy()
    frame["week_no"] = frame["WEEK_NO"].astype(int)
    frame["product_id"] = frame["PRODUCT_ID"].astype(str)
    frame.to_csv(OUT / "dunnhumby_transaction_lines_clean.csv", index=False)

    baskets = frame.groupby(["week_no", "BASKET_ID"], as_index=False).agg(
        household_key=("household_key", "first"),
        day=("DAY", "first"),
        product_count=("product_id", "nunique"),
        unit_count=("QUANTITY", "sum"),
        product_ids=("product_id", lambda x: "|".join(sorted(set(x)))),
    )
    baskets.to_csv(OUT / "dunnhumby_baskets.csv", index=False)
    panel = frame.groupby(["product_id", "week_no"], as_index=False)["QUANTITY"].sum().rename(columns={"QUANTITY": "units_sold"})
    panel.to_csv(OUT / "dunnhumby_weekly_product_demand.csv", index=False)
    profile = {
        "source": "dunnhumby Complete Journey",
        "source_url": "https://www.dunnhumby.com/source-files/",
        "documented_release_url": "https://github.com/bltap-plmarket/dunnhumby-complete-journey/releases/tag/v1.0-data",
        "license": "DbCL-1.0 as stated by the documented release mirror",
        "raw_file": str(RAW),
        "raw_sha256": hashlib.sha256(RAW.read_bytes()).hexdigest(),
        "original_rows": original_rows,
        "original_products": original_products,
        "nonpositive_quantity_rows_removed": returns,
        "retained_rows": len(frame),
        "retained_products": int(frame["product_id"].nunique()),
        "retained_baskets": int(frame["BASKET_ID"].nunique()),
        "week_range": [1, TEST_END],
        "chronological_split": {"train": [1, TRAIN_END], "validation": [TRAIN_END + 1, VALIDATION_END], "test": [VALIDATION_END + 1, TEST_END]},
        "universe_rule": f"top {TOP_N} products by training active-week support, then training units",
        "synthetic_assumptions": {"lead_time_weeks": 1, "holding_cost_per_unit_week": 1.0, "shortage_penalty_per_unit": 9.0, "ordering_cost": 1.0, "unit_purchase_cost": 1.0, "service_target": 0.90, "alpha": ALPHA},
    }
    (OUT / "dunnhumby_source_profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
    return frame, baskets, panel, profile


def replay(frame: pd.DataFrame, baskets: pd.DataFrame, panel: pd.DataFrame, graph: bool) -> dict[str, float]:
    products = sorted(frame["product_id"].unique())
    idx = {p: i for i, p in enumerate(products)}
    demand = panel.pivot_table(index="product_id", columns="week_no", values="units_sold", aggfunc="sum").reindex(index=products, columns=range(1, TEST_END + 1)).fillna(0.0).to_numpy()
    # Training-only mean and variability; validation/test values never enter the policy.
    history = demand[:, :TRAIN_END]
    mean = history[:, -8:].mean(axis=1)
    sd = history[:, -26:].std(axis=1, ddof=1)
    sd = np.nan_to_num(sd, nan=0.0)
    z = 1.2815515655446004
    base = 2.0 * mean + z * np.maximum(sd, 0.25)
    popularity = history.sum(axis=1)
    pair_counts: dict[tuple[int, int], int] = {}
    train_baskets = baskets.loc[baskets["week_no"] <= TRAIN_END, "product_ids"]
    for value in train_baskets:
        items = sorted({idx[p] for p in str(value).split("|") if p in idx})
        for a in items:
            for b in items:
                if a < b:
                    pair_counts[(a, b)] = pair_counts.get((a, b), 0) + 1
    degree = np.zeros(len(products))
    edge_buffer = np.zeros(len(products))
    for (a, b), count in pair_counts.items():
        degree[a] += count; degree[b] += count
        edge_buffer[a] += count * np.maximum(sd[b], 0.25)
        edge_buffer[b] += count * np.maximum(sd[a], 0.25)
    def scaled(x):
        x = np.maximum(x, 0.0); return x * (np.sum(popularity) / max(np.sum(x), 1.0))
    popularity_buffer = scaled(popularity)
    graph_buffer = scaled(edge_buffer)
    target = base + ALPHA * (graph_buffer if graph else popularity_buffer)
    onhand = np.ceil(target).astype(float)
    total_cost = total_unmet = total_demand = total_fulfilled = total_inventory = 0.0
    baskets_total = baskets_complete = stockouts = 0
    weekly = []
    test_baskets = baskets.loc[baskets["week_no"] > VALIDATION_END]
    for week in range(VALIDATION_END + 1, TEST_END + 1):
        order = np.maximum(0.0, np.ceil(target - onhand))
        total_cost += 1.0 + float(order.sum()) if order.sum() > 0 else 0.0
        onhand += order
        week_b = test_baskets.loc[test_baskets["week_no"] == week]
        for value in week_b["product_ids"]:
            items = [idx[p] for p in str(value).split("|") if p in idx]
            baskets_total += 1
            if items and all(onhand[i] >= 1 for i in items): baskets_complete += 1
        actual = demand[:, week - 1]
        fulfilled = np.minimum(onhand, actual)
        unmet = np.maximum(actual - onhand, 0.0)
        stockouts += int((unmet > 0).sum())
        onhand -= actual
        total_demand += float(actual.sum()); total_fulfilled += float(fulfilled.sum()); total_unmet += float(unmet.sum())
        total_cost += float(onhand.sum()) + 9.0 * float(unmet.sum())
        total_inventory += float(onhand.sum())
        weekly.append({"week_no": week, "cost": total_cost, "inventory": float(onhand.sum()), "demand": float(actual.sum()), "fulfilled": float(fulfilled.sum()), "unmet": float(unmet.sum())})
    return {"policy": "PA_graph" if graph else "C4_popularity", "alpha": ALPHA, "test_weeks": TEST_END - VALIDATION_END, "total_cost": total_cost, "average_inventory_units": total_inventory / (TEST_END - VALIDATION_END), "item_fill_rate": total_fulfilled / max(total_demand, 1.0), "complete_basket_fill_rate": baskets_complete / max(baskets_total, 1), "unmet_units": total_unmet, "stockout_events": stockouts, "basket_count": baskets_total}


def main() -> None:
    frame, baskets, panel, profile = prepare()
    rows = [replay(frame, baskets, panel, graph=False), replay(frame, baskets, panel, graph=True)]
    result = pd.DataFrame(rows)
    result.to_csv(RESULTS / "dunnhumby_external_validation_summary.csv", index=False)
    table = "| " + " | ".join(result.columns) + " |\n| " + " | ".join(["---"] * len(result.columns)) + " |\n"
    table += "\n".join("| " + " | ".join(str(row[col]) for col in result.columns) + " |" for _, row in result.iterrows())
    (RESULTS / "dunnhumby_external_validation_report.md").write_text(
        "# dunnhumby external validation\n\n"
        "This is a separate validation dataset and was not merged with UCI. The graph and popularity buffers are built from weeks 1–78 only; weeks 91–102 are replayed. Inventory, one-week lead time, costs, and alpha are synthetic assumptions.\n\n"
        + table + "\n\n"
        + f"Retained {profile['retained_products']} products, {profile['retained_baskets']} baskets, and {profile['retained_rows']} transaction lines after restricting to the top-{TOP_N} training-support universe.\n",
        encoding="utf-8",
    )
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
