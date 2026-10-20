"""Create labeled synthetic inventory/lead-time assumptions for later simulation."""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import pandas as pd


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None)
    args = parser.parse_args()
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    destination = root / "data" / "synthetic" / "inventory_scenarios.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    scenario_number = 1
    for lead_name, mean_days, sd_days, min_days, max_days in [
        ("deterministic_7d", 7, 0, 7, 7),
        ("low_variance_normal", 7, 1, 5, 9),
        ("high_variance_normal", 7, 3, 1, 14),
        ("right_skewed_discrete", 7, 4, 2, 21),
    ]:
        for holding_cost, shortage_penalty in [(0.05, 2.0), (0.15, 5.0), (0.30, 10.0)]:
            rows.append({
                "scenario_id": f"S{scenario_number:02d}",
                "scenario_status": "SYNTHETIC_ASSUMPTION_ONLY",
                "review_interval_days": 7,
                "lead_time_distribution": lead_name,
                "lead_time_mean_days": mean_days,
                "lead_time_sd_days": sd_days,
                "lead_time_min_days": min_days,
                "lead_time_max_days": max_days,
                "holding_cost_per_unit_week": holding_cost,
                "shortage_penalty_per_unit": shortage_penalty,
                "ordering_cost_per_order": 1.0,
                "unit_purchase_cost": 1.0,
                "service_target": 0.95,
                "random_seed": 20261019 + scenario_number,
                "notes": "Synthetic scenario; not observed from UCI or M5 and must be frozen before final simulation.",
            })
            scenario_number += 1
    pd.DataFrame(rows).to_csv(destination, index=False)
    print(f"Wrote {len(rows)} synthetic scenarios to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
