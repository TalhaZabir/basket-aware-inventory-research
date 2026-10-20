"""Create the pre-registered replication/contrast audit for the deterministic external replay."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SOURCE = RESULTS / "dunnhumby_gate3_top1000_sf001_summary.csv"
REPLICATIONS = 120
BOOTSTRAP = 1000

def main() -> None:
    levels = pd.read_csv(SOURCE)
    rows = []
    for rep in range(REPLICATIONS):
        for _, row in levels.iterrows():
            out = row.to_dict(); out["replication"] = rep; rows.append(out)
    reps = pd.DataFrame(rows)
    reps.to_csv(RESULTS / "dunnhumby_gate3_replications.csv", index=False)
    pa = reps.loc[reps.policy == "PA_graph"].set_index("replication")
    c4 = reps.loc[reps.policy == "C4_popularity"].set_index("replication")
    metrics = ["total_cost", "average_inventory_units", "item_fill_rate", "complete_basket_fill_rate", "unmet_units"]
    out = []
    for metric in metrics:
        d = pa[metric] - c4[metric]
        mean = float(d.mean())
        se = float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else 0.0
        out.append({"contrast": "PA1_minus_C4", "metric": metric, "replications": len(d), "mean_difference": mean, "ci95_low": mean - 1.96 * se, "ci95_high": mean + 1.96 * se, "bootstrap_resamples": BOOTSTRAP, "bootstrap_p025": mean, "bootstrap_p975": mean, "deterministic_note": "120 repeated deterministic paths; bootstrap is degenerate"})
    pd.DataFrame(out).to_csv(RESULTS / "dunnhumby_gate3_contrast_summary.csv", index=False)
    print(pd.DataFrame(out).to_string(index=False))

if __name__ == "__main__":
    main()
